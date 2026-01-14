# Data/repositories/iracema_sql_log_repository.py

from typing import List, Optional
from uuid import UUID

from sqlalchemy import asc
from sqlalchemy.orm import Session

from Data.db_context import DbContext
from Domain.iracema_sql_log_model import IracemaSQLLog
from Domain.iracema_enums import (
    LLMProviderEnum,
    LLMModelEnum,
    QueryStatusEnum,
)
from Domain.interfaces.i_iracema_sql_log_repository import IIracemaSQLLogRepository


class IracemaSQLLogRepository(IIracemaSQLLogRepository):
    def __init__(self, db_context: DbContext):
        self._db_context = db_context

    def log_sql(
        self,
        session: Session,
        conversation_id: Optional[UUID],
        message_id: Optional[UUID],
        provider: LLMProviderEnum,
        model: LLMModelEnum,
        sql_text: str,
        rowcount: int,
        duration_ms: float,
        status: QueryStatusEnum,
        error_message: Optional[str] = None,
    ) -> IracemaSQLLog:
        log = IracemaSQLLog(
            conversation_id=conversation_id,
            message_id=message_id,
            llm_provider=provider,
            llm_model=model,
            sql_text=sql_text,
            rowcount=rowcount,
            duration_ms=duration_ms,
            status=status,
            error_message=error_message,
        )
        session.add(log)
        session.commit()
        session.refresh(log)
        return log

    def list_by_conversation(
        self,
        session: Session,
        conversation_id: UUID,
    ) -> List[IracemaSQLLog]:
        query = (
            session.query(IracemaSQLLog)
            .filter(IracemaSQLLog.conversation_id == conversation_id)
            .order_by(asc(IracemaSQLLog.created_at))
        )
        return query.all()
