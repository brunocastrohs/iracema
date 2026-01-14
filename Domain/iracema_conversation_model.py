# Data/Entities/iracema_conversation_entity.py

import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, String
from sqlalchemy.dialects.postgresql import UUID

from Data.db_context import Base  # ajuste o caminho se no seu projeto for diferente


class IracemaConversation(Base):
    __tablename__ = "iracema_conversation"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )

    title = Column(
        String(255),
        nullable=True,
        doc="Título opcional da conversa (ex.: primeira pergunta resumida).",
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )
