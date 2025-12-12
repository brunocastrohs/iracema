# Application/services/iracema_ask_service.py

import re
import time
from typing import Any, Dict, List, Optional

from sqlalchemy import text

from Data.db_context import DbContext
from Data.interfaces.i_iracema_conversation_repository import IIracemaConversationRepository
from Data.interfaces.i_iracema_message_repository import IIracemaMessageRepository
from Data.interfaces.i_iracema_sql_log_repository import IIracemaSQLLogRepository
from Models.iracema_enums import (
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


SQL_SELECT_PATTERN = re.compile(r"^\s*select\s", re.IGNORECASE)


def _is_safe_select(sql: str) -> bool:
    stripped = sql.strip()

    # mais de um comando?
    if ";" in stripped[:-1]:
        return False

    if not SQL_SELECT_PATTERN.match(stripped):
        return False

    forbidden = [" insert ", " update ", " delete ", " drop ", " alter ", " truncate "]
    lower_sql = f" {stripped.lower()} "
    return not any(tok in lower_sql for tok in forbidden)


class IracemaAskService(IIracemaAskService):
    """
    Fluxo principal:
      pergunta → gera SQL → executa no PostgreSQL → explica resultado.
    """

    def __init__(
        self,
        db_context: DbContext,
        conversation_repo: IIracemaConversationRepository,
        message_repo: IIracemaMessageRepository,
        sql_log_repo: IIracemaSQLLogRepository,
        llm_client: IIracemaLLMClient,
        llm_provider: LLMProviderEnum = LLMProviderEnum.OLLAMA,
        llm_model: LLMModelEnum = LLMModelEnum.PHI_3,
    ) -> None:
        self._db_context = db_context
        self._conversation_repo = conversation_repo
        self._message_repo = message_repo
        self._sql_log_repo = sql_log_repo
        self._llm_client = llm_client
        self._llm_provider = llm_provider
        self._llm_model = llm_model

    def ask(self, request: IracemaAskRequestDto) -> IracemaAskResponseDto:
        session = self._db_context.create_session()

        question = request.question
        error_message: Optional[str] = None
        sql_executed = ""
        rows: List[Dict[str, Any]] = []
        rowcount = 0
        answer_text = ""

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

            # 3) Gerar SQL (SYNC)
            sql_executed = self._llm_client.generate_sql(
                question=question,
                top_k=request.top_k,
            )

            if not _is_safe_select(sql_executed):
                raise ValueError("O modelo gerou um SQL potencialmente inseguro.")

            # 4) Executar SQL no banco
            start = time.perf_counter()
            with self._db_context.engine.connect() as connection:
                result = connection.execute(text(sql_executed))
                columns = result.keys()
                rows = [dict(zip(columns, row)) for row in result.fetchall()]

            rowcount = len(rows)
            duration_ms = (time.perf_counter() - start) * 1000.0

            # 5) Log de sucesso
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
                error_message=None,
            )

            # 6) Explicar resultado (SYNC)
            answer_text = self._llm_client.explain_result(
                question=question,
                sql_executed=sql_executed,
                rows=rows,
                rowcount=rowcount,
            )

            # 7) Registrar mensagem do assistente
            assistant_message = self._message_repo.add_message(
                session=session,
                conversation_id=conversation.id,
                role=MessageRoleEnum.ASSISTANT,
                content=answer_text,
            )

        except Exception as ex:
            error_message = str(ex)
            answer_text = (
                "Ocorreu um erro ao processar sua pergunta. "
                "A equipe técnica será notificada."
            )

            # garante que temos conversa e msg do usuário
            if "conversation" not in locals():
                conversation = self._conversation_repo.create(
                    session, title=question[:120]
                )

            if "user_message" not in locals():
                user_message = self._message_repo.add_message(
                    session=session,
                    conversation_id=conversation.id,
                    role=MessageRoleEnum.USER,
                    content=question,
                )

            assistant_message = self._message_repo.add_message(
                session=session,
                conversation_id=conversation.id,
                role=MessageRoleEnum.ASSISTANT,
                content=answer_text,
            )

            # log de erro
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

        finally:
            session.close()

        # Preview das linhas (limitado a top_k)
        result_preview: List[Dict[str, Any]] = rows[: min(len(rows), request.top_k)]

        return build_ask_response_dto(
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
