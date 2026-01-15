# Application/mappings/iracema_mappings.py

from typing import Dict, Any, List, Optional

from Domain.iracema_conversation_model import IracemaConversation
from Domain.iracema_message_model import IracemaMessage
from Domain.iracema_sql_log_model import IracemaSQLLog

from Application.dto.iracema_conversation_dto import IracemaConversationDto
from Application.dto.iracema_message_dto import IracemaMessageDto
from Application.dto.iracema_sql_log_dto import IracemaSQLLogDto
from Application.dto.iracema_ask_dto import IracemaAskResponseDto

from Domain.datasource_model import DataSource
from Application.dto.iracema_start_dto import (
    IracemaStartResponseDto,
    IracemaStartResolutionDto,
    IracemaDataSourceCandidateDto,
)

def build_start_response_dto(
    conversation: IracemaConversation,
    user_message: IracemaMessage,
    assistant_message: IracemaMessage,
    assistant_text: str,
    resolved: bool,
    table_identifier: Optional[str] = None,
    datasource_id: Optional[int] = None,
    prompt_inicial: Optional[str] = None,
    reason: Optional[str] = None,
    candidates: Optional[List[DataSource]] = None,
    start_state: Optional[Dict[str, Any]] = None,
    error: Optional[str] = None,
) -> IracemaStartResponseDto:
    return IracemaStartResponseDto(
        conversation_id=conversation.id,
        user_message_id=user_message.id,
        assistant_message_id=assistant_message.id,
        assistant_text=assistant_text,
        resolution=IracemaStartResolutionDto(
            resolved=resolved,
            table_identifier=table_identifier,
            datasource_id=datasource_id,
            prompt_inicial=prompt_inicial,
            reason=reason,
        ),
        candidates=[to_datasource_candidate_dto(x) for x in (candidates or [])],
        start_state=start_state or {},
        error=error,
    )


def to_datasource_candidate_dto(model: DataSource) -> IracemaDataSourceCandidateDto:
    return IracemaDataSourceCandidateDto(
        id=model.id,
        identificador_tabela=model.identificador_tabela,
        titulo_tabela=model.titulo_tabela,
        categoria_informacao=model.categoria_informacao,
        classe_maior=model.classe_maior,
        sub_classe_maior=model.sub_classe_maior,
        classe_menor=model.classe_menor,
        descricao_tabela=model.descricao_tabela,
        palavras_chave=model.palavras_chave,
        ano_elaboracao=model.ano_elaboracao,
        fonte_dados=model.fonte_dados,
    )


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
