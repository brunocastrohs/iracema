# Data/repositories/iracema_conversation_repository.py

from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from Data.db_context import DbContext
from Models.iracema_conversation_model import IracemaConversation
from Data.interfaces.i_iracema_conversation_repository import IIracemaConversationRepository


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
