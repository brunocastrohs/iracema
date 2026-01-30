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

from Application.helpers.iracema_sql_policy_helper import (plan_sql_template, sanitize_llm_sql)


def _build_rows_summary(rows: List[Dict[str, Any]], top_k: int) -> Dict[str, Any]:
    """
    Resumo compacto para o LLM explainer (reduz tokens e melhora latência).
    """
    preview = rows[: min(len(rows), top_k)]
    columns = list(preview[0].keys()) if preview else []

    # Heurística: valores únicos se for 1 coluna (ex: DISTINCT zonas)
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
        datasource_repo: IIracemaDataSourceRepository,  # 🆕
        llm_client: IIracemaLLMClient,
        llm_provider: LLMProviderEnum = LLMProviderEnum.OLLAMA,
        llm_model: LLMModelEnum = LLMModelEnum.PHI_3,
    ) -> None:
        self._db_context = db_context
        self._conversation_repo = conversation_repo
        self._message_repo = message_repo
        self._sql_log_repo = sql_log_repo
        self._datasource_repo = datasource_repo
        self._llm_client = llm_client
        self._llm_provider = llm_provider
        self._llm_model = llm_model

    def ask(self, request: IracemaAskRequestDto) -> IracemaAskResponseDto:
        session = self._db_context.create_session()

        question = request.question
        
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
        
        error_message: Optional[str] = None

        sql_executed = ""
        rows: List[Dict[str, Any]] = []
        rowcount = 0
        answer_text = ""

        conversation = None
        user_message = None
        assistant_message = None

        try:
            # 1) Obter ou criar conversa
            if request.conversation_id:
                conversation = self._conversation_repo.get_by_id(
                    session, request.conversation_id
                )
                if conversation is None:
                    conversation = self._conversation_repo.create(
                        session, title=question[:120]
                    )
            else:
                conversation = self._conversation_repo.create(
                    session, title=question[:120]
                )

            # 2) Registrar mensagem do usuário
            user_message = self._message_repo.add_message(
                session=session,
                conversation_id=conversation.id,
                role=MessageRoleEnum.USER,
                content=question,
            )
            session.flush()

            # 3) Planner → decide se precisa LLM SQL
            #    (para distinct/count, planner gera SQL template e pula LLM)
            raw_sql = None

            # Só chama LLM SQL se NÃO for template.
            # A estratégia: tenta planejar sem sql (templates), se cair em llm_sql_with_policy
            # aí sim pede sql ao LLM e replana com raw_sql.
            template_plan = plan_sql_template(
                table_fqn=table_fqn,
                columns_meta=ds.colunas_tabela,
                question=question,
                top_k=request.top_k,
            )

            if template_plan is not None:
                sql_plan = template_plan
            else:
                raw_sql = self._llm_client.generate_sql(
                        schema_description=schema_description,
                        question=question,
                        top_k=request.top_k,
                    )
                sql_plan = sanitize_llm_sql(
                        table_fqn=table_fqn,
                        raw_sql_from_llm=raw_sql,
                        top_k=request.top_k,
                    )

            

            sql_executed = sql_plan.sql
            
            

            # 4) Executar SQL no banco
            start = time.perf_counter()
            with self._db_context.engine.connect() as connection:
                result = connection.execute(text(sql_executed))
                columns = result.keys()
                rows = [dict(zip(columns, row)) for row in result.fetchall()]

            rowcount = len(rows)
            duration_ms = (time.perf_counter() - start) * 1000.0

            # 5) Log de sucesso (inclui reason do planner)
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

            # 6) Explicar resultado (envia resumo, não tudo)
            rows_summary = _build_rows_summary(rows, request.top_k)
            

            answer_text = self._llm_client.explain_result(
                schema_description=schema_description,
                question=question,
                sql_executed=sql_executed,
                rows=rows_summary["preview"],
                rowcount=rowcount,
            )

            # 7) Registrar mensagem do assistente
            assistant_message = self._message_repo.add_message(
                session=session,
                conversation_id=conversation.id,
                role=MessageRoleEnum.ASSISTANT,
                content=answer_text,
            )
            session.flush()

        except Exception as ex:
            error_message = str(ex)
            answer_text = (
                "Ocorreu um erro ao processar sua pergunta. "
                "A equipe técnica será notificada."
            )

            if conversation is None:
                conversation = self._conversation_repo.create(
                    session, title=question[:120]
                )
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

        # Preview limitado (para retornar ao client)
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

    def ask_ai(self, request: IracemaAskRequestDto) -> IracemaAskResponseDto:
        session = self._db_context.create_session()

        question = request.question
        
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
        
        error_message: Optional[str] = None

        sql_executed = ""
        rows: List[Dict[str, Any]] = []
        rowcount = 0
        answer_text = ""

        conversation = None
        user_message = None
        assistant_message = None

        try:
            # 1) Obter ou criar conversa
            if request.conversation_id:
                conversation = self._conversation_repo.get_by_id(
                    session, request.conversation_id
                )
                if conversation is None:
                    conversation = self._conversation_repo.create(
                        session, title=question[:120]
                    )
            else:
                conversation = self._conversation_repo.create(
                    session, title=question[:120]
                )

            # 2) Registrar mensagem do usuário
            user_message = self._message_repo.add_message(
                session=session,
                conversation_id=conversation.id,
                role=MessageRoleEnum.USER,
                content=question,
            )
            session.flush()

            # 3) Planner → decide se precisa LLM SQL
            #    (para distinct/count, planner gera SQL template e pula LLM)
            raw_sql = None

            # Só chama LLM SQL se NÃO for template.
            # A estratégia: tenta planejar sem sql (templates), se cair em llm_sql_with_policy
            # aí sim pede sql ao LLM e replana com raw_sql.
            """template_plan = plan_sql_template(
                table_fqn=table_fqn,
                columns_meta=ds.colunas_tabela,
                question=question,
                top_k=request.top_k,
            )

            if template_plan is not None:
                sql_plan = template_plan
            else:"""
            raw_sql = self._llm_client.generate_sql(
                        schema_description=schema_description,
                        question=question,
                        top_k=request.top_k,
                    )
            print(raw_sql)
            sql_plan = sanitize_llm_sql(
                        table_fqn=table_fqn,
                        raw_sql_from_llm=raw_sql,
                        top_k=request.top_k,
                    )

            sql_executed = sql_plan.sql
            
            

            # 4) Executar SQL no banco
            start = time.perf_counter()
            with self._db_context.engine.connect() as connection:
                result = connection.execute(text(sql_executed))
                columns = result.keys()
                rows = [dict(zip(columns, row)) for row in result.fetchall()]

            rowcount = len(rows)
            duration_ms = (time.perf_counter() - start) * 1000.0

            # 5) Log de sucesso (inclui reason do planner)
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

            # 6) Explicar resultado (envia resumo, não tudo)
            rows_summary = _build_rows_summary(rows, request.top_k)
            

            answer_text = self._llm_client.explain_result(
                schema_description=schema_description,
                question=question,
                sql_executed=sql_executed,
                rows=rows_summary["preview"],
                rowcount=rowcount,
            )

            # 7) Registrar mensagem do assistente
            assistant_message = self._message_repo.add_message(
                session=session,
                conversation_id=conversation.id,
                role=MessageRoleEnum.ASSISTANT,
                content=answer_text,
            )
            session.flush()

        except Exception as ex:
            error_message = str(ex)
            answer_text = (
                "Ocorreu um erro ao processar sua pergunta. "
                "A equipe técnica será notificada."
            )

            if conversation is None:
                conversation = self._conversation_repo.create(
                    session, title=question[:120]
                )
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

        # Preview limitado (para retornar ao client)
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

    def ask_heuristic(self, request: IracemaAskRequestDto) -> IracemaAskResponseDto:
        session = self._db_context.create_session()

        question = request.question
        
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
        
        error_message: Optional[str] = None

        sql_executed = ""
        rows: List[Dict[str, Any]] = []
        rowcount = 0
        answer_text = ""

        conversation = None
        user_message = None
        assistant_message = None

        try:
            # 1) Obter ou criar conversa
            if request.conversation_id:
                conversation = self._conversation_repo.get_by_id(
                    session, request.conversation_id
                )
                if conversation is None:
                    conversation = self._conversation_repo.create(
                        session, title=question[:120]
                    )
            else:
                conversation = self._conversation_repo.create(
                    session, title=question[:120]
                )

            # 2) Registrar mensagem do usuário
            user_message = self._message_repo.add_message(
                session=session,
                conversation_id=conversation.id,
                role=MessageRoleEnum.USER,
                content=question,
            )
            session.flush()

            # 3) Planner → decide se precisa LLM SQL
            #    (para distinct/count, planner gera SQL template e pula LLM)

            # Só chama LLM SQL se NÃO for template.
            # A estratégia: tenta planejar sem sql (templates), se cair em llm_sql_with_policy
            # aí sim pede sql ao LLM e replana com raw_sql.
            template_plan = plan_sql_template(
                table_fqn=table_fqn,
                columns_meta=ds.colunas_tabela,
                question=question,
                top_k=request.top_k,
            )

            if template_plan is not None:
                sql_plan = template_plan
            
            sql_executed = sql_plan.sql
            
            # 4) Executar SQL no banco
            start = time.perf_counter()
            with self._db_context.engine.connect() as connection:
                result = connection.execute(text(sql_executed))
                columns = result.keys()
                rows = [dict(zip(columns, row)) for row in result.fetchall()]

            rowcount = len(rows)
            duration_ms = (time.perf_counter() - start) * 1000.0

            # 5) Log de sucesso (inclui reason do planner)
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

            # 6) Explicar resultado (envia resumo, não tudo)
            rows_summary = _build_rows_summary(rows, request.top_k)
            

            answer_text = self._llm_client.explain_result(
                schema_description=schema_description,
                question=question,
                sql_executed=sql_executed,
                rows=rows_summary["preview"],
                rowcount=rowcount,
            )

            # 7) Registrar mensagem do assistente
            assistant_message = self._message_repo.add_message(
                session=session,
                conversation_id=conversation.id,
                role=MessageRoleEnum.ASSISTANT,
                content=answer_text,
            )
            session.flush()

        except Exception as ex:
            error_message = str(ex)
            answer_text = (
                "Ocorreu um erro ao processar sua pergunta. "
                "A equipe técnica será notificada."
            )

            if conversation is None:
                conversation = self._conversation_repo.create(
                    session, title=question[:120]
                )
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

        # Preview limitado (para retornar ao client)
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