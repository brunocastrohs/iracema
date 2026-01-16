from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class DataSourceColumnDto(BaseModel):
    name: str
    label: str
    type: str


class DataSourceCatalogItemDto(BaseModel):
    categoria_informacao: str
    classe_maior: Optional[str] = None
    sub_classe_maior: Optional[str] = None
    classe_menor: Optional[str] = None

    identificador_tabela: str
    titulo_tabela: str
    descricao_tabela: Optional[str] = None

    colunas_tabela: List[DataSourceColumnDto] = Field(default_factory=list)

    fonte_dados: Optional[str] = None
    ano_elaboracao: Optional[int] = None
    is_ativo: bool
    palavras_chave: Optional[str] = None

    created_at: datetime
    updated_at: datetime


class DataSourceCatalogResponseDto(BaseModel):
    version: str
    generated_at: str
    count: int
    items: List[DataSourceCatalogItemDto] = Field(default_factory=list)
