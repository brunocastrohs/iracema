import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from Data.db_context import Base
from Domain.iracema_enums import (
    ConversationPhaseEnum,
    ConversationContextStatusEnum,
)


class IracemaConversationContext(Base):
    """
    Estado e governança da conversa.

    - Fase 1 (START): resolve datasource/tabela + permissões + memória curta.
    - Fase 2 (ASK): perguntas assumindo datasource fixada e histórico resumido.
    - Fase 3 (Governança): limites, expiração, rotação, custos (campos já previstos).
    """

    __tablename__ = "iracema_conversation_context"

    # 1:1 com a conversa (uma conversa tem um contexto)
    conversation_id = Column(
        UUID(as_uuid=True),
        ForeignKey("iracema_conversation.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    )

    # --- Fase e status ---
    phase = Column(
        Enum(ConversationPhaseEnum, name="iracema_conversation_phase"),
        nullable=False,
        default=ConversationPhaseEnum.START,
        doc="Fase atual: START ou ASK.",
    )

    status = Column(
        Enum(ConversationContextStatusEnum, name="iracema_conversation_context_status"),
        nullable=False,
        default=ConversationContextStatusEnum.EMPTY,
        doc="Estado do contexto: EMPTY/SELECTING/READY/BLOCKED.",
    )

    # --- Resolução de datasource (START) ---
    datasource_id = Column(
        Integer,
        ForeignKey("datasources.id", ondelete="SET NULL"),
        nullable=True,
        doc="Datasource escolhida (catálogo).",
    )

    table_identifier = Column(
        Text,
        nullable=True,
        doc="Identificador final da tabela (datasources.identificador_tabela).",
    )

    prompt_inicial_snapshot = Column(
        Text,
        nullable=True,
        doc="Snapshot do prompt inicial escolhido (para auditoria e estabilidade).",
    )
    
    prompt_inicial_fc_snapshot = Column(
        Text,
        nullable=True,
        doc="Snapshot do prompt inicial escolhido (para auditoria e estabilidade).",
    )

    # --- Memória curta ---
    short_memory_summary = Column(
        Text,
        nullable=True,
        doc="Resumo curto do histórico para ser usado em prompts (START/ASK).",
    )

    # --- Estado auxiliar do START ---
    start_state = Column(
        JSONB,
        nullable=False,
        default=dict,
        doc=(
            "Estado interno do START (ex.: candidatos sugeridos, "
            "última intenção, contadores, evidências)."
        ),
    )

    start_attempts = Column(
        Integer,
        nullable=False,
        default=0,
        doc="Quantidade de interações/tentativas no fluxo START.",
    )

    # --- Governança (Fase 3 - já preparando) ---
    is_locked = Column(
        Boolean,
        nullable=False,
        default=False,
        doc="Se true, bloqueia ASK até resolver permissões/limites.",
    )

    expires_at = Column(
        DateTime(timezone=True),
        nullable=True,
        doc="Expiração do contexto (ex.: rotação após X dias).",
    )

    # --- Auditoria ---
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
    )

    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    # --- Relationships ---
    conversation = relationship("IracemaConversation", lazy="joined")
    datasource = relationship("DataSource", lazy="joined")
