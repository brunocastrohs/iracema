from abc import ABC, abstractmethod
from typing import List, Optional

from sqlalchemy.orm import Session

from Domain.datasource_model import DataSource


class IIracemaDataSourceRepository(ABC):
    @abstractmethod
    def get_by_id(self, session: Session, datasource_id: int) -> Optional[DataSource]:
        """Busca uma datasource pelo ID."""

    @abstractmethod
    def get_by_table_identifier(
        self,
        session: Session,
        table_identifier: str,
    ) -> Optional[DataSource]:
        """Busca uma datasource pelo identificador_tabela."""

    @abstractmethod
    def search_active(
        self,
        session: Session,
        query: str,
        limit: int = 10,
        offset: int = 0,
    ) -> List[DataSource]:
        """
        Busca textual em datasources ativas.

        A implementação deve filtrar is_ativo = true e aplicar ILIKE em:
        - titulo_tabela
        - descricao_tabela
        - palavras_chave
        - categoria_informacao
        - classe_maior / sub_classe_maior / classe_menor
        - identificador_tabela
        """

    @abstractmethod
    def list_active(
        self,
        session: Session,
        limit: int = 50,
        offset: int = 0,
    ) -> List[DataSource]:
        """Lista datasources ativas (fallback quando não houver query)."""

    @abstractmethod
    def list_all(self, session: Session, limit: int = 5000, offset: int = 0) -> List[DataSource]:
        """Lista todas as datasources (ativas e inativas)."""