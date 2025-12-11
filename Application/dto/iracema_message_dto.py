# Application/dto/iracema_message_dto.py

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from Models.iracema_enums import MessageRoleEnum


class IracemaMessageDto(BaseModel):
    id: UUID
    conversation_id: UUID
    role: MessageRoleEnum
    content: str
    created_at: datetime
