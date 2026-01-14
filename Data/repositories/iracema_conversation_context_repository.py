from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from Data.db_context import DbContext
from Domain.iracema_conversation_context_model import IracemaConversationContext
from Domain.iracema_enums import ConversationPhaseEnum, ConversationContextStatusEnum
from Domain.interfaces.i_iracema_conversation_context_repository import (
    IIracemaConversationContextRepository,
)


class IracemaConversationContextRepository(IIracemaConversationContextRepository):
    def __init__(self, db_context: DbContext):
        self._db_context = db_context

    def get_by_conversation_id(
        self,
        session: Session,
        conversation_id: UUID,
    ) -> Optional[IracemaConversationContext]:
        return session.get(IracemaConversationContext, conversation_id)

    def ensure_exists(
        self,
        session: Session,
        conversation_id: UUID,
    ) -> IracemaConversationContext:
        existing = self.get_by_conversation_id(session=session, conversation_id=conversation_id)
        if existing is not None:
            return existing

        ctx = IracemaConversationContext(
            conversation_id=conversation_id,
            phase=ConversationPhaseEnum.START,
            status=ConversationContextStatusEnum.EMPTY,
            start_state={},
            start_attempts=0,
            is_locked=False,
        )
        session.add(ctx)
        session.commit()
        session.refresh(ctx)
        return ctx

    def update(
        self,
        session: Session,
        context: IracemaConversationContext,
    ) -> IracemaConversationContext:
        # Como context é entidade já vinculada à session (normalmente),
        # basta commitar. Se vier “detached”, o merge resolve.
        merged = session.merge(context)
        session.commit()
        session.refresh(merged)
        return merged

    def set_datasource_selected(
        self,
        session: Session,
        conversation_id: UUID,
        datasource_id: int,
        table_identifier: str,
        prompt_inicial_snapshot: Optional[str],
    ) -> IracemaConversationContext:
        ctx = self.ensure_exists(session=session, conversation_id=conversation_id)

        ctx.datasource_id = datasource_id
        ctx.table_identifier = table_identifier
        ctx.prompt_inicial_snapshot = prompt_inicial_snapshot

        ctx.status = ConversationContextStatusEnum.READY
        ctx.phase = ConversationPhaseEnum.ASK

        # reset de estado do START (opcional, mas recomendável)
        ctx.start_state = ctx.start_state or {}
        ctx.is_locked = False

        session.commit()
        session.refresh(ctx)
        return ctx

    def clear_selection(
        self,
        session: Session,
        conversation_id: UUID,
    ) -> IracemaConversationContext:
        ctx = self.ensure_exists(session=session, conversation_id=conversation_id)

        ctx.datasource_id = None
        ctx.table_identifier = None
        ctx.prompt_inicial_snapshot = None

        ctx.phase = ConversationPhaseEnum.START
        ctx.status = ConversationContextStatusEnum.EMPTY

        ctx.start_state = {}
        ctx.start_attempts = 0
        ctx.is_locked = False

        session.commit()
        session.refresh(ctx)
        return ctx
