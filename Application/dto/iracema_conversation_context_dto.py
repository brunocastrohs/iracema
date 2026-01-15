from datetime import datetime
from typing import Optional, Dict, Any
from uuid import UUID

from pydantic import BaseModel

from Domain.iracema_enums import ConversationPhaseEnum, ConversationContextStatusEnum


class IracemaConversationContextDto(BaseModel):
    conversation_id: UUID

    phase: ConversationPhaseEnum
    status: ConversationContextStatusEnum

    datasource_id: Optional[int]
    table_identifier: Optional[str]

    short_memory_summary: Optional[str]
    start_state: Dict[str, Any]

    is_locked: bool

    created_at: datetime
    updated_at: datetime
