# Application/dto/iracema_conversation_dto.py

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class IracemaConversationDto(BaseModel):
    id: UUID
    title: str | None
    created_at: datetime
    updated_at: datetime
