# Data/interfaces/i_iracema_sql_log_repository.py

from abc import ABC, abstractmethod
from typing import List, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from Domain.iracema_sql_log_model import IracemaSQLLog
from Domain.iracema_enums import (
    LLMProviderEnum,
    LLMModelEnum,
    QueryStatusEnum,
)


class IIracemaSQLLogRepository(ABC):
    @abstractmethod
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
        """Registra uma interação SQL/LLM no log."""

    @abstractmethod
    def list_by_conversation(
        self,
        session: Session,
        conversation_id: UUID,
    ) -> List[IracemaSQLLog]:
        """Lista todos os logs de SQL associados a uma conversa."""
