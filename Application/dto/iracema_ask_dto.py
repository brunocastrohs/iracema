# Application/dto/iracema_ask_dto.py

from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class IracemaAskRequestDto(BaseModel):
    """
    Payload de entrada do endpoint /ask.
    """
    question: str = Field(
        ...,
        description="Pergunta em linguagem natural sobre os dados das tabelas da PEDEA."
    )
    conversation_id: Optional[UUID] = Field(
        default=None,
        description="ID da conversa atual. Se vazio, o serviço pode criar uma nova."
    )
    table_identifier: str = Field(
        ...,
        description="Identificador da tabela selecionada no /start (datasources.identificador_tabela)."
    )
    top_k: int = Field(
        20,
        ge=1,
        le=1200,
        description="Número máximo de linhas que a consulta SQL pode retornar."
    )
    language: str = Field(
        "pt-BR",
        description="Idioma desejado para a resposta textual."
    )
    explain: bool = True


class IracemaAskResponseDto(BaseModel):
    """
    Resposta do endpoint /ask.
    Inclui: resposta textual, SQL executado e um preview do resultado.
    """
    conversation_id: UUID
    user_message_id: UUID
    assistant_message_id: UUID

    question: str
    answer_text: str

    sql_executed: str
    rowcount: int

    result_preview: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Amostra das linhas retornadas (ex.: primeiras N linhas)."
    )

    error: Optional[str] = Field(
        default=None,
        description="Mensagem de erro, se algo falhar no pipeline."
    )
