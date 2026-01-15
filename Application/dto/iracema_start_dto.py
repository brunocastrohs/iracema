from typing import List, Optional, Dict, Any
from uuid import UUID

from pydantic import BaseModel, Field


class IracemaStartRequestDto(BaseModel):
    """
    Payload de entrada do endpoint /start.

    A ideia é o cliente chamar /start repetidamente até que o sistema
    retorne um table_identifier (datasource.identificador_tabela).
    """
    message: str = Field(
        ...,
        description="Mensagem do usuário para resolver o contexto (qual tabela/camada)."
    )

    conversation_id: Optional[UUID] = Field(
        default=None,
        description="ID da conversa. Se vazio, o serviço cria uma nova conversa e contexto."
    )

    language: str = Field(
        "pt-BR",
        description="Idioma desejado para mensagens e prompts."
    )

    max_candidates: int = Field(
        5,
        ge=1,
        le=20,
        description="Número máximo de datasources candidatas a retornar quando houver ambiguidade."
    )


class IracemaDataSourceCandidateDto(BaseModel):
    """
    Candidato de datasource retornado durante o START.
    """
    id: int
    identificador_tabela: str
    titulo_tabela: str
    categoria_informacao: str

    classe_maior: Optional[str] = None
    sub_classe_maior: Optional[str] = None
    classe_menor: Optional[str] = None

    descricao_tabela: Optional[str] = None
    palavras_chave: Optional[str] = None
    ano_elaboracao: Optional[int] = None
    fonte_dados: Optional[str] = None


class IracemaStartResolutionDto(BaseModel):
    """
    Resultado da resolução do START.
    """
    resolved: bool = Field(
        ...,
        description="Se true, o contexto foi resolvido e a tabela está fixada."
    )

    table_identifier: Optional[str] = Field(
        default=None,
        description="Identificador da tabela fixada (datasources.identificador_tabela)."
    )

    datasource_id: Optional[int] = Field(
        default=None,
        description="ID da datasource selecionada."
    )

    prompt_inicial: Optional[str] = Field(
        default=None,
        description="Prompt inicial (system prompt) para a tabela selecionada."
    )

    # útil para debugging e UI
    reason: Optional[str] = Field(
        default=None,
        description="Motivo/resumo da decisão do start (ex.: 'seleção única', 'confirmado pelo usuário')."
    )


class IracemaStartResponseDto(BaseModel):
    """
    Resposta do endpoint /start.

    Pode retornar:
    - resolved=true com table_identifier (fim do start)
    OU
    - resolved=false com candidates + next_question (continua start)
    """
    conversation_id: UUID

    user_message_id: UUID
    assistant_message_id: UUID

    assistant_text: str = Field(
        ...,
        description="Resposta do assistente orientando o usuário durante o START."
    )

    resolution: IracemaStartResolutionDto

    candidates: List[IracemaDataSourceCandidateDto] = Field(
        default_factory=list,
        description="Lista de datasources candidatas (quando há ambiguidade)."
    )

    # estado leve para o cliente (sem expor internals demais)
    start_state: Dict[str, Any] = Field(
        default_factory=dict,
        description="Estado resumido do START (ex.: contagem de tentativas, último termo, etc.)."
    )

    error: Optional[str] = Field(
        default=None,
        description="Erro (se ocorrer) — idealmente vazio em operação normal."
    )
