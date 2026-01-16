from typing import List, Optional

from sqlalchemy import or_
from sqlalchemy.orm import Session

from Data.db_context import DbContext
from Domain.datasource_model import DataSource
from Domain.interfaces.i_iracema_datasource_repository import IIracemaDataSourceRepository


class IracemaDataSourceRepository(IIracemaDataSourceRepository):
    def __init__(self, db_context: DbContext):
        self._db_context = db_context

    def get_by_id(self, session: Session, datasource_id: int) -> Optional[DataSource]:
        return session.get(DataSource, datasource_id)

    def get_by_table_identifier(
        self,
        session: Session,
        table_identifier: str,
    ) -> Optional[DataSource]:
        return (
            session.query(DataSource)
            .filter(DataSource.identificador_tabela == table_identifier)
            .first()
        )

    def search_active(
        self,
        session: Session,
        query: str,
        limit: int = 10,
        offset: int = 0,
    ) -> List[DataSource]:
        q = f"%{query.strip()}%" if query else "%"

        return (
            session.query(DataSource)
            .filter(DataSource.is_ativo.is_(True))
            .filter(
                or_(
                    DataSource.titulo_tabela.ilike(q),
                    DataSource.descricao_tabela.ilike(q),
                    DataSource.palavras_chave.ilike(q),
                    DataSource.categoria_informacao.ilike(q),
                    DataSource.classe_maior.ilike(q),
                    DataSource.sub_classe_maior.ilike(q),
                    DataSource.classe_menor.ilike(q),
                    DataSource.identificador_tabela.ilike(q),
                )
            )
            .order_by(DataSource.titulo_tabela.asc())
            .offset(offset)
            .limit(limit)
            .all()
        )

    def list_active(
        self,
        session: Session,
        limit: int = 50,
        offset: int = 0,
    ) -> List[DataSource]:
        return (
            session.query(DataSource)
            .filter(DataSource.is_ativo.is_(True))
            .order_by(DataSource.titulo_tabela.asc())
            .offset(offset)
            .limit(limit)
            .all()
        )

    def list_all(
        self,
        session: Session,
        limit: int = 5000,
        offset: int = 0,
    ) -> List[DataSource]:
        return (
            session.query(DataSource)
            .filter(DataSource.is_ativo.is_(True))
            .order_by(DataSource.categoria_informacao.asc(), DataSource.titulo_tabela.asc())
            .offset(offset)
            .limit(limit)
            .all()
        )
