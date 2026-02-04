# Application/services/iracema_ask_service.py

import time
from typing import Any, Dict, List, Optional

from sqlalchemy import text

from Data.db_context import DbContext
from Domain.interfaces.i_iracema_conversation_repository import IIracemaConversationRepository
from Domain.interfaces.i_iracema_message_repository import IIracemaMessageRepository
from Domain.interfaces.i_iracema_sql_log_repository import IIracemaSQLLogRepository

from Domain.iracema_enums import (
    MessageRoleEnum,
    LLMProviderEnum,
    LLMModelEnum,
    QueryStatusEnum,
)

from Application.dto.iracema_ask_dto import (
    IracemaAskRequestDto,
    IracemaAskResponseDto,
)
from Application.interfaces.i_iracema_ask_service import IIracemaAskService
from Application.interfaces.i_iracema_llm_client import IIracemaLLMClient
from Application.mappings.iracema_mappings import build_ask_response_dto
from Domain.interfaces.i_iracema_datasource_repository import IIracemaDataSourceRepository
from Application.helpers.iracema_table_name_helper import build_table_fqn

from Application.interfaces.i_iracema_rag_index_service import IIracemaRagIndexService
from Application.interfaces.i_iracema_rag_retrieve_service import IIracemaRagRetrieveService

from Application.helpers.sql_types_helper import SqlPlan
from Application.helpers.sql_template_planner_helper import plan_sql_template
from Application.helpers.sql_llm_sanitizer_helper import sanitize_llm_sql

from Application.helpers.iracema_apply_topk_limit_helper import apply_topk_limit


def _build_rows_summary(rows: List[Dict[str, Any]], top_k: int) -> Dict[str, Any]:
    preview = rows[: min(len(rows), top_k)]
    columns = list(preview[0].keys()) if preview else []

    unique_values: Optional[List[Any]] = None
    if preview and len(columns) == 1:
        c = columns[0]
        unique_values = []
        seen = set()
        for r in preview:
            v = r.get(c)
            if v not in seen:
                seen.add(v)
                unique_values.append(v)

    return {
        "columns": columns,
        "preview": preview,
        "preview_count": len(preview),
        "unique_values_preview": unique_values,
    }


class IracemaAskService(IIracemaAskService):
    def __init__(
        self,
        db_context: DbContext,
        conversation_repo: IIracemaConversationRepository,
        message_repo: IIracemaMessageRepository,
        sql_log_repo: IIracemaSQLLogRepository,
        datasource_repo: IIracemaDataSourceRepository,
        rag_index_service: IIracemaRagIndexService,
        rag_retrieve_service: IIracemaRagRetrieveService,
        llm_client: IIracemaLLMClient,
        llm_provider: LLMProviderEnum = LLMProviderEnum.OLLAMA,
        llm_model: LLMModelEnum = LLMModelEnum.PHI_3,
    ) -> None:
        self._db_context = db_context
        self._conversation_repo = conversation_repo
        self._message_repo = message_repo
        self._sql_log_repo = sql_log_repo
        self._datasource_repo = datasource_repo
        self._rag_index_service = rag_index_service
        self._rag_retrieve_service = rag_retrieve_service
        self._llm_client = llm_client
        self._llm_provider = llm_provider
        self._llm_model = llm_model

    # -------------------------------------------------------------------------
    # API pública
    # -------------------------------------------------------------------------

    def ask(self, request: IracemaAskRequestDto) -> IracemaAskResponseDto:
        """
        Modo padrão: cache-hit -> template planner -> LLM.
        """
        return self._run_pipeline(request, sql_mode="default")

    def ask_ai(self, request: IracemaAskRequestDto) -> IracemaAskResponseDto:
        """
        Modo AI: cache-hit -> LLM (sem planner templates).
        """
        return self._run_pipeline(request, sql_mode="ai")

    def ask_heuristic(self, request: IracemaAskRequestDto) -> IracemaAskResponseDto:
        """
        Modo heurístico: cache-hit -> template planner (sem LLM).
        Se planner não conseguir, gera erro controlado.
        """
        return self._run_pipeline(request, sql_mode="heuristic")

    # -------------------------------------------------------------------------
    # Pipeline central
    # -------------------------------------------------------------------------

    def _run_pipeline(self, request: IracemaAskRequestDto, sql_mode: str) -> IracemaAskResponseDto:
        session = self._db_context.create_session()

        question = request.question
        error_message: Optional[str] = None

        sql_executed = ""
        rows: List[Dict[str, Any]] = []
        rowcount = 0
        answer_text = ""

        conversation = None
        user_message = None
        assistant_message = None

        try:
            # 0) Datasource + schema
            ds = self._datasource_repo.get_by_table_identifier(
                session=session,
                table_identifier=request.table_identifier,
            )
            if ds is None or not ds.is_ativo:
                raise ValueError(
                    "table_identifier inválido ou datasource inativa. Execute /start para obter um identificador válido."
                )

            schema_description = ds.prompt_inicial or ""
            if not schema_description.strip():
                raise ValueError("Datasource não possui prompt_inicial configurado.")

            table_fqn = build_table_fqn(request.table_identifier)

            # 1) Obter/criar conversa
            conversation = self._get_or_create_conversation(session, request, question)
            print("1 executado")

            # 2) Registrar msg do usuário
            user_message = self._message_repo.add_message(
                session=session,
                conversation_id=conversation.id,
                role=MessageRoleEnum.USER,
                content=question,
            )
            session.flush()
            print("2 executado")

            # 3) Resolver SQL (cache/template/LLM conforme modo)
            sql_plan = self._resolve_sql_plan(
                request=request,
                schema_description=schema_description,
                table_fqn=table_fqn,
                columns_meta=ds.colunas_tabela,
                sql_mode=sql_mode,
            )
            sql_executed = sql_plan.sql
            print("3 executado")
            
            # 4) Executar SQL
            start = time.perf_counter()
            with self._db_context.engine.connect() as connection:
                result = connection.execute(text(sql_executed))
                columns = result.keys()
                rows = [dict(zip(columns, row)) for row in result.fetchall()]
            rowcount = len(rows)
            duration_ms = (time.perf_counter() - start) * 1000.0
            print("4 executado")
            
            # 5) Log SQL SUCCESS
            self._sql_log_repo.log_sql(
                session=session,
                conversation_id=conversation.id,
                message_id=user_message.id,
                provider=self._llm_provider,
                model=self._llm_model,
                sql_text=sql_executed,
                rowcount=rowcount,
                duration_ms=duration_ms,
                status=QueryStatusEnum.SUCCESS,
                error_message=f"planner:{sql_plan.reason}",
            )
            print("5 executado")
            
            # 6) Indexar (memória Pergunta->SQL) se aplicável
            self._index_if_needed(
                request=request,
                question=question,
                sql_executed=sql_executed,
                rowcount=rowcount,
                reason=sql_plan.reason,
                duration_ms=duration_ms,
                conversation_id=conversation.id,
                message_id=user_message.id,
            )
            print("6 executado")
            
            # 7) Explicar (opcional)
            if getattr(request, "explain", True):
                rows_summary = _build_rows_summary(rows, request.top_k)
                answer_text = self._llm_client.explain_result(
                    schema_description=schema_description,
                    question=question,
                    sql_executed=sql_executed,
                    rows=rows_summary["preview"],
                    rowcount=rowcount,
                )
            else:
                answer_text = ""
            print("7 executado")
            
            # 8) Registrar msg do assistente
            assistant_message = self._message_repo.add_message(
                session=session,
                conversation_id=conversation.id,
                role=MessageRoleEnum.ASSISTANT,
                content=answer_text,
            )
            session.flush()
            #print("7 executado")
            
        except Exception as ex:
            error_message = str(ex)
            answer_text = (
                "Ocorreu um erro ao processar sua pergunta. "
                "A equipe técnica será notificada."
            )

            # garante conversa/mensagens para auditoria
            if conversation is None:
                conversation = self._conversation_repo.create(session, title=question[:120])
                session.flush()

            if user_message is None:
                user_message = self._message_repo.add_message(
                    session=session,
                    conversation_id=conversation.id,
                    role=MessageRoleEnum.USER,
                    content=question,
                )
                session.flush()

            assistant_message = self._message_repo.add_message(
                session=session,
                conversation_id=conversation.id,
                role=MessageRoleEnum.ASSISTANT,
                content=answer_text,
            )
            session.flush()

            self._sql_log_repo.log_sql(
                session=session,
                conversation_id=conversation.id,
                message_id=user_message.id,
                provider=self._llm_provider,
                model=self._llm_model,
                sql_text=sql_executed or "",
                rowcount=rowcount,
                duration_ms=0.0,
                status=QueryStatusEnum.ERROR,
                error_message=error_message,
            )

        # Preview limitado
        result_preview: List[Dict[str, Any]] = rows[: min(len(rows), request.top_k)]

        response = build_ask_response_dto(
            conversation=conversation,
            user_message=user_message,
            assistant_message=assistant_message,
            question=question,
            answer_text=answer_text,
            sql_executed=sql_executed,
            rowcount=rowcount,
            result_preview=result_preview,
            error=error_message,
        )

        session.close()
        return response

    # -------------------------------------------------------------------------
    # Helpers internos
    # -------------------------------------------------------------------------

    def _get_or_create_conversation(self, session, request: IracemaAskRequestDto, question: str):
        if request.conversation_id:
            conv = self._conversation_repo.get_by_id(session, request.conversation_id)
            if conv is not None:
                return conv
        conv = self._conversation_repo.create(session, title=question[:120])
        session.flush()
        return conv

    def _resolve_sql_plan(
        self,
        request: IracemaAskRequestDto,
        schema_description: str,
        table_fqn: str,
        columns_meta: list[dict],
        sql_mode: str,
    ) -> SqlPlan:
        # 1) cache hit (sempre)
        #cached_sql = self._rag_retrieve_service.try_get_exact_sql(
       #     table_identifier=request.table_identifier,
       #     question=request.question,
       # )
        #print(cached_sql)
       # if cached_sql:
       #     sql = apply_topk_limit(cached_sql, request.top_k)
       #     return SqlPlan(sql=sql, used_template=False, reason="rag_exact_hit")

        # 2) modo heuristic: apenas template
        if sql_mode == "heuristic":
            template_plan = plan_sql_template(
                table_fqn=table_fqn,
                columns_meta=columns_meta,
                question=request.question,
                top_k=request.top_k,
            )
            if template_plan is None:
                raise ValueError("Planner heurístico não conseguiu gerar SQL para esta pergunta.")
            return template_plan

        # 3) modo default: template -> LLM
        if sql_mode == "default":
            template_plan = plan_sql_template(
                table_fqn=table_fqn,
                columns_meta=columns_meta,
                question=request.question,
                top_k=request.top_k,
            )
            #print(template_plan)
            if template_plan is not None:
                return template_plan

            raw_sql = self._llm_client.generate_sql(
                schema_description=schema_description,
                question=request.question,
                top_k=request.top_k,
                table_identifier=request.table_identifier,
            )
            #print(raw_sql)
            return sanitize_llm_sql(
                table_fqn=table_fqn,
                raw_sql_from_llm=raw_sql,
                top_k=request.top_k,
            )

        # 4) modo ai: LLM direto
        if sql_mode == "ai":
            print("Vai executar llm")
            raw_sql = self._llm_client.generate_sql(
                schema_description=schema_description,
                question=request.question,
                top_k=request.top_k,
                table_identifier=request.table_identifier,
            )
            print("Vai sanitizar sql")
            print(raw_sql)
            return sanitize_llm_sql(
                table_fqn=table_fqn,
                raw_sql_from_llm=raw_sql,
                top_k=request.top_k,
            )

        raise ValueError(f"sql_mode inválido: {sql_mode}")

    def _index_if_needed(
        self,
        request: IracemaAskRequestDto,
        question: str,
        sql_executed: str,
        rowcount: int,
        reason: str,
        duration_ms: float,
        conversation_id: int,
        message_id: int,
    ) -> None:
        should_index = (
            (rowcount > 0)
            or ("count(" in (sql_executed or "").lower())
            or ("sum(" in (sql_executed or "").lower())
        )
        #print("ShouldIndex")
        #print(should_index)

        if not should_index:
            return

        self._rag_index_service.index_success(
            table_identifier=request.table_identifier,
            question=question,
            sql_executed=sql_executed,
            rowcount=rowcount,
            reason=reason,
            duration_ms=duration_ms,
            conversation_id=conversation_id,
            message_id=message_id,
        )
