import time
from typing import Any, Dict, List, Optional

from sqlalchemy import text

from Data.db_context import DbContext
from Domain.interfaces.i_iracema_conversation_repository import IIracemaConversationRepository
from Domain.interfaces.i_iracema_message_repository import IIracemaMessageRepository
from Domain.interfaces.i_iracema_sql_log_repository import IIracemaSQLLogRepository
from Domain.interfaces.i_iracema_datasource_repository import IIracemaDataSourceRepository

from Domain.iracema_enums import MessageRoleEnum, LLMProviderEnum, LLMModelEnum, QueryStatusEnum

from Application.dto.iracema_ask_dto import IracemaAskRequestDto, IracemaAskResponseDto
from Application.interfaces.i_iracema_ask_service import IIracemaAskService
from Application.interfaces.i_iracema_llm_client import IIracemaLLMClient
from Application.interfaces.i_iracema_rag_index_service import IIracemaRagIndexService
from Application.interfaces.i_iracema_rag_retrieve_service import IIracemaRagRetrieveService
from Application.interfaces.i_iracema_fc_client import IIracemaFCClient

from Application.mappings.iracema_mappings import build_ask_response_dto
from Application.helpers.iracema_table_name_helper import build_table_fqn
from Application.helpers.sql_types_helper import SqlPlan

from Application.helpers.query_plan_validator_helper import validate_and_normalize_plan
from Application.helpers.query_plan_sql_compiler_helper import compile_query_plan_to_sql
from Application.helpers.iracema_apply_topk_limit_helper import apply_topk_limit
from Application.interfaces.i_iracema_ask_by_fc_service import IIracemaAskByFCService

from Application.dto.iracema_fca_dto import FCAArgsDto
from Application.helpers.fca_validator_helper import validate_and_normalize_fca
from Application.helpers.fca_sql_compiler_helper import compile_fca_to_sql


def _build_rows_summary(rows: List[Dict[str, Any]], top_k: int) -> Dict[str, Any]:
    preview = rows[: min(len(rows), top_k)]
    columns = list(preview[0].keys()) if preview else []
    return {"columns": columns, "preview": preview, "preview_count": len(preview)}


class IracemaAskByFCService(IIracemaAskByFCService):
    """
    Endpoint ask/fc:
    - cache-hit (Pergunta->SQL) via RAG (igual ao ask)
    - se MISS: chama FC client para gerar QueryPlanArgs (JSON)
    - valida plano vs columns_meta
    - compila SQL determinístico
    - executa, loga, indexa, explica
    """

    def __init__(
        self,
        db_context: DbContext,
        conversation_repo: IIracemaConversationRepository,
        message_repo: IIracemaMessageRepository,
        sql_log_repo: IIracemaSQLLogRepository,
        datasource_repo: IIracemaDataSourceRepository,
        rag_index_service: IIracemaRagIndexService,
        rag_retrieve_service: IIracemaRagRetrieveService,
        fc_client: IIracemaFCClient,
        llm_client: IIracemaLLMClient,  # para explainer
        llm_provider: LLMProviderEnum = LLMProviderEnum.OLLAMA,
        llm_model: LLMModelEnum = LLMModelEnum.PHI_3,
    ):
        self._db_context = db_context
        self._conversation_repo = conversation_repo
        self._message_repo = message_repo
        self._sql_log_repo = sql_log_repo
        self._datasource_repo = datasource_repo
        self._rag_index_service = rag_index_service
        self._rag_retrieve_service = rag_retrieve_service
        self._fc_client = fc_client
        self._llm_client = llm_client
        self._llm_provider = llm_provider
        self._llm_model = llm_model
        
    def ask_fc_with_args(self, request: IracemaAskRequestDto, fca: FCAArgsDto) -> IracemaAskResponseDto:
        """
        Novo modo:
        - NÃO chama LLM
        - NÃO faz retrieve no vector store (remove custo)
        - valida FCA vs columns_meta
        - compila SQL determinístico
        - executa, loga
        - indexa FCA no vector store (Pergunta -> FCA) para auditoria/memória
        """
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
            ds = self._datasource_repo.get_by_table_identifier(
                session=session,
                table_identifier=request.table_identifier,
            )
            if ds is None or not ds.is_ativo:
                raise ValueError("table_identifier inválido ou datasource inativa. Execute /start.")

            table_fqn = build_table_fqn(request.table_identifier)

            # conversa
            conversation = self._get_or_create_conversation(session, request, question)

            # msg user
            user_message = self._message_repo.add_message(
                session=session,
                conversation_id=conversation.id,
                role=MessageRoleEnum.USER,
                content=question,
            )
            session.flush()

            # 1) valida e normaliza FCA (whitelist + defaults)
            fca.table_fqn = table_fqn  # força a tabela do request
            fca = validate_and_normalize_fca(fca, columns_meta=ds.colunas_tabela, top_k=request.top_k)

            # 2) compila SQL determinístico
            sql_plan = compile_fca_to_sql(fca)
            sql_executed = sql_plan.sql

            # 3) executa
            start = time.perf_counter()
            with self._db_context.engine.connect() as connection:
                result = connection.execute(text(sql_executed))
                columns = result.keys()
                rows = [dict(zip(columns, row)) for row in result.fetchall()]
            rowcount = len(rows)
            duration_ms = (time.perf_counter() - start) * 1000.0

            # 4) log SUCCESS
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

            # 5) indexa FCA (sempre) - não precisa mais retrieve, mas mantém memória/auditoria
            # Sugestão: criar um método novo no rag_index_service
            # index_fca(question, fca_json, sql_executed, ...)
            self._rag_index_service.index_success(
                table_identifier=request.table_identifier,
                question=question,
                sql_executed=sql_executed,
                rowcount=rowcount,
                reason="fc_args",
                duration_ms=duration_ms,
                conversation_id=conversation.id,
                message_id=user_message.id,
                # opcional: incluir fca serializado se seu index aceitar metadados
                # extra={"fca": fca.model_dump()}
            )

            # 6) explain (opcional)
            if getattr(request, "explain", True):
                rows_summary = _build_rows_summary(rows, request.top_k)
                answer_text = self._llm_client.explain_result(
                    schema_description=ds.prompt_inicial or "",
                    question=question,
                    sql_executed=sql_executed,
                    rows=rows_summary["preview"],
                    rowcount=rowcount,
                )
            else:
                answer_text = ""

            assistant_message = self._message_repo.add_message(
                session=session,
                conversation_id=conversation.id,
                role=MessageRoleEnum.ASSISTANT,
                content=answer_text,
            )
            session.flush()

        except Exception as ex:
            error_message = str(ex)
            answer_text = "Ocorreu um erro ao processar sua pergunta. A equipe técnica será notificada."

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

        result_preview = rows[: min(len(rows), request.top_k)]

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

    def ask_fc(self, request: IracemaAskRequestDto) -> IracemaAskResponseDto:
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
            ds = self._datasource_repo.get_by_table_identifier(
                session=session,
                table_identifier=request.table_identifier,
            )
            if ds is None or not ds.is_ativo:
                raise ValueError("table_identifier inválido ou datasource inativa. Execute /start.")

            prompt_fc = ds.prompt_inicial_fc or ""
            if not prompt_fc.strip():
                raise ValueError("Datasource não possui prompt_inicial_fc configurado.")

            table_fqn = build_table_fqn(request.table_identifier)

            # conversa
            conversation = self._get_or_create_conversation(session, request, question)

            # msg user
            user_message = self._message_repo.add_message(
                session=session,
                conversation_id=conversation.id,
                role=MessageRoleEnum.USER,
                content=question,
            )
            session.flush()

            # 1) cache hit (Pergunta->SQL)
            cached_sql = self._rag_retrieve_service.try_get_exact_sql(
                table_identifier=request.table_identifier,
                question=question,
            )
            if cached_sql:
                sql_executed = apply_topk_limit(cached_sql, request.top_k)
                sql_plan = SqlPlan(sql=sql_executed, used_template=False, reason="rag_exact_hit")
            else:
                # 2) FC plan
                plan = self._fc_client.generate_query_plan(
                    prompt_inicial_fc=prompt_fc,
                    question=question,
                    columns_meta=ds.colunas_tabela,
                    top_k=request.top_k,
                )

                # 3) valida contra colunas reais
                plan = validate_and_normalize_plan(plan, ds.colunas_tabela)

                # 4) compila SQL determinístico
                sql_plan = compile_query_plan_to_sql(
                    table_fqn=table_fqn,
                    plan=plan,
                    top_k=request.top_k,
                )
                sql_executed = sql_plan.sql

            # executa
            start = time.perf_counter()
            with self._db_context.engine.connect() as connection:
                result = connection.execute(text(sql_executed))
                columns = result.keys()
                rows = [dict(zip(columns, row)) for row in result.fetchall()]
            rowcount = len(rows)
            duration_ms = (time.perf_counter() - start) * 1000.0

            # log
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

            # index (só se não for cache hit)
            if sql_plan.reason != "rag_exact_hit":
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

            # explain
            if getattr(request, "explain", True):
                rows_summary = _build_rows_summary(rows, request.top_k)
                answer_text = self._llm_client.explain_result(
                    schema_description=ds.prompt_inicial or "",  # ok usar prompt SQL como contexto do explainer
                    question=question,
                    sql_executed=sql_executed,
                    rows=rows_summary["preview"],
                    rowcount=rowcount,
                )
            else:
                answer_text = ""

            assistant_message = self._message_repo.add_message(
                session=session,
                conversation_id=conversation.id,
                role=MessageRoleEnum.ASSISTANT,
                content=answer_text,
            )
            session.flush()

        except Exception as ex:
            error_message = str(ex)
            answer_text = "Ocorreu um erro ao processar sua pergunta. A equipe técnica será notificada."

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

        result_preview = rows[: min(len(rows), request.top_k)]

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

    def _get_or_create_conversation(self, session, request: IracemaAskRequestDto, question: str):
        if request.conversation_id:
            conv = self._conversation_repo.get_by_id(session, request.conversation_id)
            if conv is not None:
                return conv
        conv = self._conversation_repo.create(session, title=question[:120])
        session.flush()
        return conv

    def _index_if_needed(
        self,
        request: IracemaAskRequestDto,
        question: str,
        sql_executed: str,
        rowcount: int,
        reason: str,
        duration_ms: float,
        conversation_id,
        message_id,
    ):
        should_index = (
            (rowcount > 0)
            or ("count(" in (sql_executed or "").lower())
            or ("sum(" in (sql_executed or "").lower())
        )
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
