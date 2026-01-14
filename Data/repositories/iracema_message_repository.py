# Data/repositories/iracema_message_repository.py

from typing import List, Optional
from uuid import UUID

from sqlalchemy import asc, desc
from sqlalchemy.orm import Session

from Data.db_context import DbContext
from Domain.iracema_message_model import IracemaMessage
from Domain.iracema_enums import MessageRoleEnum
from Domain.interfaces.i_iracema_message_repository import IIracemaMessageRepository


class IracemaMessageRepository(IIracemaMessageRepository):
    def __init__(self, db_context: DbContext):
        self._db_context = db_context

    def add_message(
        self,
        session: Session,
        conversation_id: UUID,
        role: MessageRoleEnum,
        content: str,
    ) -> IracemaMessage:
        message = IracemaMessage(
            conversation_id=conversation_id,
            role=role,
            content=content,
        )
        session.add(message)
        session.commit()
        session.refresh(message)
        return message

    def list_by_conversation(
        self,
        session: Session,
        conversation_id: UUID,
    ) -> List[IracemaMessage]:
        query = (
            session.query(IracemaMessage)
            .filter(IracemaMessage.conversation_id == conversation_id)
            .order_by(asc(IracemaMessage.created_at))
        )
        return query.all()

    def list_last_by_conversation(
        self,
        session: Session,
        conversation_id: UUID,
        limit: int = 10,
    ) -> List[IracemaMessage]:
        # busca as últimas N DESC e devolve em ordem cronológica (ASC)
        rows = (
            session.query(IracemaMessage)
            .filter(IracemaMessage.conversation_id == conversation_id)
            .order_by(desc(IracemaMessage.created_at))
            .limit(limit)
            .all()
        )
        return list(reversed(rows))

    def get_last_user_message(
        self,
        session: Session,
        conversation_id: UUID,
    ) -> Optional[IracemaMessage]:
        return (
            session.query(IracemaMessage)
            .filter(IracemaMessage.conversation_id == conversation_id)
            .filter(IracemaMessage.role == MessageRoleEnum.USER)
            .order_by(desc(IracemaMessage.created_at))
            .first()
        )