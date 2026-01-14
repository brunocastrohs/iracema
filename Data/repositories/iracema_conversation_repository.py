# Data/repositories/iracema_conversation_repository.py

from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from Data.db_context import DbContext
from Domain.iracema_conversation_model import IracemaConversation
from Domain.interfaces.i_iracema_conversation_repository import IIracemaConversationRepository


class IracemaConversationRepository(IIracemaConversationRepository):
    def __init__(self, db_context: DbContext):
        self._db_context = db_context

    def create(self, session: Session, title: Optional[str] = None) -> IracemaConversation:
        conversation = IracemaConversation(title=title)
        session.add(conversation)
        session.commit()
        session.refresh(conversation)
        return conversation

    def get_by_id(self, session: Session, conversation_id: UUID) -> Optional[IracemaConversation]:
        return session.get(IracemaConversation, conversation_id)

    def get_or_create(
        self,
        session: Session,
        conversation_id: Optional[UUID],
        title: Optional[str] = None,
    ) -> IracemaConversation:
        if conversation_id is None:
            return self.create(session=session, title=title)

        existing = self.get_by_id(session=session, conversation_id=conversation_id)
        if existing is not None:
            return existing

        # decisão: criar nova conversa se não existir (mais amigável para /start)
        # se você preferir erro, troque por raise
        return self.create(session=session, title=title)