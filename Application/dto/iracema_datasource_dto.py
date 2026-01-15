from typing import Optional
from pydantic import BaseModel


class IracemaDataSourceDto(BaseModel):
    id: int
    identificador_tabela: str
    titulo_tabela: str
    descricao_tabela: Optional[str] = None
    categoria_informacao: str

    classe_maior: Optional[str] = None
    sub_classe_maior: Optional[str] = None
    classe_menor: Optional[str] = None

    palavras_chave: Optional[str] = None
    fonte_dados: Optional[str] = None
    ano_elaboracao: Optional[int] = None

    is_ativo: bool
    prompt_inicial: Optional[str] = None
