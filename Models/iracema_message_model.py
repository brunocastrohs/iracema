# Data/Entities/iracema_message_entity.py

import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, String, Text, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from Data.db_context import Base
from Models.iracema_enums import MessageRoleEnum


class IracemaMessage(Base):
    __tablename__ = "iracema_message"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )

    conversation_id = Column(
        UUID(as_uuid=True),
        ForeignKey("iracema_conversation.id", ondelete="CASCADE"),
        nullable=False,
    )

    role = Column(
        Enum(MessageRoleEnum, name="iracema_message_role"),
        nullable=False,
        doc="Papel na conversa: system, user, assistant.",
    )

    content = Column(
        Text,
        nullable=False,
        doc="Conteúdo textual bruto da mensagem.",
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    conversation = relationship(
        "IracemaConversation",
        backref="messages",
        lazy="joined",
    )
