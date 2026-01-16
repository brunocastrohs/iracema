from datetime import datetime, timezone
from typing import List

from Data.db_context import DbContext
from Domain.interfaces.i_iracema_datasource_repository import IIracemaDataSourceRepository

from Application.dto.iracema_datasource_catalog_dto import (
    DataSourceCatalogResponseDto,
    DataSourceCatalogItemDto,
    DataSourceColumnDto,
)
from Application.interfaces.i_iracema_start_catalog_service import IIracemaStartCatalogService


class IracemaStartCatalogService(IIracemaStartCatalogService):
    def __init__(
        self,
        db_context: DbContext,
        datasource_repo: IIracemaDataSourceRepository,
        version: str = "1.0",
    ) -> None:
        self._db_context = db_context
        self._datasource_repo = datasource_repo
        self._version = version

    def list_datasources_catalog(self) -> DataSourceCatalogResponseDto:
        session = self._db_context.create_session()
        try:
            # Use list_all se quiser retornar ativo + inativo.
            # Se quiser só ativos, troque para list_active.
            datasources = self._datasource_repo.list_all(session=session, limit=5000, offset=0)

            items: List[DataSourceCatalogItemDto] = []

            for ds in datasources:
                cols: List[DataSourceColumnDto] = []
                for c in (ds.colunas_tabela or []):
                    name = c.get("name")
                    if not name:
                        continue

                    cols.append(
                        DataSourceColumnDto(
                            name=name,
                            label=c.get("label") or c.get("description") or name,
                            type=c.get("type") or "text",
                        )
                    )

                items.append(
                    DataSourceCatalogItemDto(
                        categoria_informacao=ds.categoria_informacao,
                        classe_maior=ds.classe_maior,
                        sub_classe_maior=ds.sub_classe_maior,
                        classe_menor=ds.classe_menor,
                        identificador_tabela=ds.identificador_tabela,
                        titulo_tabela=ds.titulo_tabela,
                        descricao_tabela=ds.descricao_tabela,
                        colunas_tabela=cols,
                        fonte_dados=ds.fonte_dados,
                        ano_elaboracao=ds.ano_elaboracao,
                        is_ativo=ds.is_ativo,
                        palavras_chave=ds.palavras_chave,
                        created_at=ds.created_at,
                        updated_at=ds.updated_at,
                    )
                )

            generated_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

            return DataSourceCatalogResponseDto(
                version=self._version,
                generated_at=generated_at,
                count=len(items),
                items=items,
            )
        finally:
            session.close()
