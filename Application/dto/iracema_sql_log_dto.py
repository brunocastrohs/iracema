# Application/dto/iracema_sql_log_dto.py

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel

from Domain.iracema_enums import (
    LLMProviderEnum,
    LLMModelEnum,
    QueryStatusEnum,
)


class IracemaSQLLogDto(BaseModel):
    id: UUID
    conversation_id: Optional[UUID]
    message_id: Optional[UUID]

    llm_provider: LLMProviderEnum
    llm_model: LLMModelEnum

    sql_text: str
    rowcount: int
    duration_ms: float
    status: QueryStatusEnum
    error_message: Optional[str]

    created_at: datetime
