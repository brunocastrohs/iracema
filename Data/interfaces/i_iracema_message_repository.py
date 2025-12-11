# Data/interfaces/i_iracema_message_repository.py

from abc import ABC, abstractmethod
from typing import List
from uuid import UUID

from sqlalchemy.orm import Session

from Models.iracema_message_model import IracemaMessage
from Models.iracema_enums import MessageRoleEnum


class IIracemaMessageRepository(ABC):
    @abstractmethod
    def add_message(
        self,
        session: Session,
        conversation_id: UUID,
        role: MessageRoleEnum,
        content: str,
    ) -> IracemaMessage:
        """Registra uma nova mensagem na conversa."""

    @abstractmethod
    def list_by_conversation(
        self,
        session: Session,
        conversation_id: UUID,
    ) -> List[IracemaMessage]:
        """Lista todas as mensagens de uma conversa, em ordem cronológica."""
