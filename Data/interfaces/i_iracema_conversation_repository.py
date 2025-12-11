# Data/interfaces/i_iracema_conversation_repository.py

from abc import ABC, abstractmethod
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from Models.iracema_conversation_model import IracemaConversation


class IIracemaConversationRepository(ABC):
    @abstractmethod
    def create(self, session: Session, title: Optional[str] = None) -> IracemaConversation:
        """Cria uma nova conversa."""

    @abstractmethod
    def get_by_id(self, session: Session, conversation_id: UUID) -> Optional[IracemaConversation]:
        """Busca uma conversa pelo ID."""
