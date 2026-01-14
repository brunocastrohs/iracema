# Domain/interfaces/i_iracema_conversation_repository.py

from abc import ABC, abstractmethod
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from Domain.iracema_conversation_model import IracemaConversation


class IIracemaConversationRepository(ABC):
    @abstractmethod
    def create(self, session: Session, title: Optional[str] = None) -> IracemaConversation:
        """Cria uma nova conversa."""

    @abstractmethod
    def get_by_id(self, session: Session, conversation_id: UUID) -> Optional[IracemaConversation]:
        """Busca uma conversa pelo ID."""

    @abstractmethod
    def get_or_create(
        self,
        session: Session,
        conversation_id: Optional[UUID],
        title: Optional[str] = None,
    ) -> IracemaConversation:
        """
        Se conversation_id for None, cria uma conversa.
        Se conversation_id existir e for encontrado, retorna.
        Se não for encontrado, cria uma nova conversa (ou opcionalmente erro — decisão da implementação).
        """