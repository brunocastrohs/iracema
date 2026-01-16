from abc import ABC, abstractmethod

from Application.dto.iracema_datasource_catalog_dto import DataSourceCatalogResponseDto


class IIracemaStartCatalogService(ABC):
    @abstractmethod
    def list_datasources_catalog(self) -> DataSourceCatalogResponseDto:
        """
        Retorna catálogo de datasources (para suportar a jornada start).
        """
        raise NotImplementedError
