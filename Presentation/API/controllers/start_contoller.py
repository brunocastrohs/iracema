# Presentation/API/controllers/start_controller.py

from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException

from Application.dto.iracema_start_dto import (
    IracemaStartRequestDto,
    IracemaStartResponseDto,
)
from Application.interfaces.i_iracema_start_service import IIracemaStartService

from Presentation.API.helpers.iracema_dependencies_helper import (
    get_current_user,
    get_iracema_start_service,
)

router = APIRouter()


@router.post(
    "/start",
    response_model=IracemaStartResponseDto,
    tags=["Iracema"],
)
async def start_iracema(
    body: IracemaStartRequestDto,
    user: Dict[str, Any] = Depends(get_current_user),
    service: IIracemaStartService = Depends(get_iracema_start_service),
) -> IracemaStartResponseDto:
    """
    Endpoint Fase 1 do chatbot Iracema.

    - Requer autenticação Bearer (token emitido pelo /auth/login).
    - Orquestra a resolução do contexto (datasource/tabela) de forma iterativa.
    - Deve ser chamado repetidamente até que `resolution.resolved == true`,
      retornando `table_identifier` para ser usado no /ask.
    """
    try:
        # service.start é síncrono
        return service.start(body)
    except Exception as ex:
        # fallback defensivo (idealmente logar aqui)
        raise HTTPException(status_code=500, detail=str(ex))
