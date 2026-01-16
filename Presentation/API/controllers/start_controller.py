from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException

from Application.dto.iracema_start_dto import IracemaStartRequestDto, IracemaStartResponseDto
from Application.dto.iracema_datasource_catalog_dto import DataSourceCatalogResponseDto
from Application.interfaces.i_iracema_start_service import IIracemaStartService
from Application.interfaces.i_iracema_start_catalog_service import IIracemaStartCatalogService

from Presentation.API.helpers.iracema_dependencies_helper import (
    get_current_user,
    get_iracema_start_service,
    get_iracema_start_catalog_service,
)

router = APIRouter()


@router.get(
    "/catalog",
    response_model=DataSourceCatalogResponseDto,
    tags=["Iracema"],
)
async def list_datasources(
    user: Dict[str, Any] = Depends(get_current_user),
    service: IIracemaStartCatalogService = Depends(get_iracema_start_catalog_service),
) -> DataSourceCatalogResponseDto:
    """
    Retorna o catálogo de datasources no formato padronizado
    para apoiar a jornada START (seleção de contexto).
    """
    try:
        return service.list_datasources_catalog()
    except Exception as ex:
        raise HTTPException(status_code=500, detail=str(ex))


@router.post(
    "/ask",
    response_model=IracemaStartResponseDto,
    tags=["Iracema"],
)
async def start_iracema(
    body: IracemaStartRequestDto,
    user: Dict[str, Any] = Depends(get_current_user),
    service: IIracemaStartService = Depends(get_iracema_start_service),
) -> IracemaStartResponseDto:
    """
    START iterativo: resolve contexto (tabela/camada).
    """
    try:
        return service.start(body)
    except Exception as ex:
        raise HTTPException(status_code=500, detail=str(ex))
