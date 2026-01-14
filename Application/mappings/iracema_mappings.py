# Application/mappings/iracema_mappings.py

from typing import Dict, Any, List

from Domain.iracema_conversation_model import IracemaConversation
from Domain.iracema_message_model import IracemaMessage
from Domain.iracema_sql_log_model import IracemaSQLLog

from Application.dto.iracema_conversation_dto import IracemaConversationDto
from Application.dto.iracema_message_dto import IracemaMessageDto
from Application.dto.iracema_sql_log_dto import IracemaSQLLogDto
from Application.dto.iracema_ask_dto import IracemaAskResponseDto


def to_conversation_dto(model: IracemaConversation) -> IracemaConversationDto:
    return IracemaConversationDto(
        id=model.id,
        title=model.title,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def to_message_dto(model: IracemaMessage) -> IracemaMessageDto:
    return IracemaMessageDto(
        id=model.id,
        conversation_id=model.conversation_id,
        role=model.role,
        content=model.content,
        created_at=model.created_at,
    )


def to_sql_log_dto(model: IracemaSQLLog) -> IracemaSQLLogDto:
    return IracemaSQLLogDto(
        id=model.id,
        conversation_id=model.conversation_id,
        message_id=model.message_id,
        llm_provider=model.llm_provider,
        llm_model=model.llm_model,
        sql_text=model.sql_text,
        rowcount=model.rowcount,
        duration_ms=model.duration_ms or 0.0,
        status=model.status,
        error_message=model.error_message,
        created_at=model.created_at,
    )


def build_ask_response_dto(
    conversation: IracemaConversation,
    user_message: IracemaMessage,
    assistant_message: IracemaMessage,
    question: str,
    answer_text: str,
    sql_executed: str,
    rowcount: int,
    result_preview: List[Dict[str, Any]],
    error: str | None = None,
) -> IracemaAskResponseDto:
    """
    Helper para montar o DTO final de resposta do /ask
    a partir dos Models e dos dados do pipeline.
    """
    return IracemaAskResponseDto(
        conversation_id=conversation.id,
        user_message_id=user_message.id,
        assistant_message_id=assistant_message.id,
        question=question,
        answer_text=answer_text,
        sql_executed=sql_executed,
        rowcount=rowcount,
        result_preview=result_preview,
        error=error,
    )
