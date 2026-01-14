# Data/Entities/iracema_sql_log_entity.py

import uuid
from datetime import datetime

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    Text,
    Enum,
    Float,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from Data.db_context import Base
from Models.iracema_enums import LLMProviderEnum, LLMModelEnum, QueryStatusEnum


class IracemaSQLLog(Base):
    __tablename__ = "iracema_sql_log"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )

    conversation_id = Column(
        UUID(as_uuid=True),
        ForeignKey("iracema_conversation.id", ondelete="SET NULL"),
        nullable=True,
    )

    message_id = Column(
        UUID(as_uuid=True),
        ForeignKey("iracema_message.id", ondelete="SET NULL"),
        nullable=True,
        doc="Mensagem do usuário que originou esta consulta.",
    )

    llm_provider = Column(
        Enum(LLMProviderEnum, name="iracema_llm_provider"),
        nullable=False,
        default=LLMProviderEnum.OPENAI,
    )

    llm_model = Column(
        Enum(LLMModelEnum, name="iracema_llm_model"),
        nullable=False,
        default=LLMModelEnum.PHI_3,
    )

    sql_text = Column(
        Text,
        nullable=False,
        doc="Comando SQL executado no PostgreSQL.",
    )

    rowcount = Column(
        Integer,
        nullable=False,
        default=0,
        doc="Quantidade de linhas retornadas pela consulta.",
    )

    duration_ms = Column(
        Float,
        nullable=True,
        doc="Tempo de execução da query no banco (em milissegundos).",
    )

    status = Column(
        Enum(QueryStatusEnum, name="iracema_query_status"),
        nullable=False,
        default=QueryStatusEnum.SUCCESS,
    )

    error_message = Column(
        Text,
        nullable=True,
        doc="Mensagem de erro, se a consulta ou interação com o LLM falhar.",
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    conversation = relationship("IracemaConversation", lazy="joined")
    message = relationship("IracemaMessage", lazy="joined")
