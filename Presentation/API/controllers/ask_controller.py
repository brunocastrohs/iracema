from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException

from Application.dto.iracema_ask_dto import (
    IracemaAskRequestDto,
    IracemaAskResponseDto,
)
from Application.interfaces.i_iracema_ask_service import IIracemaAskService
from Application.interfaces.i_iracema_ask_by_fc_service import IIracemaAskByFCService


from Presentation.API.helpers.iracema_dependencies_helper import (
    get_current_user,
    get_iracema_ask_service,
    get_iracema_ask_fc_service
)

router = APIRouter()


@router.post(
    "/ask",
    response_model=IracemaAskResponseDto,
    tags=["Iracema"],
)
async def ask_iracema(
    body: IracemaAskRequestDto,
    user: Dict[str, Any] = Depends(get_current_user),
    service: IIracemaAskService = Depends(get_iracema_ask_service),
) -> IracemaAskResponseDto:
    """
    Endpoint principal do chatbot Iracema.

    - Requer autenticação Bearer (token emitido pelo /auth/login).
    - Orquestra pergunta → SQL → PostgreSQL → explicação em linguagem natural.
    """
    try:
        # service.ask é síncrono
        return service.ask(body)
    except Exception as ex:
        # fallback defensivo (idealmente logar aqui)
        raise HTTPException(status_code=500, detail=str(ex))

@router.post(
    "/ask/heuristic",
    response_model=IracemaAskResponseDto,
    tags=["Iracema"],
)
async def ask_iracema_heuristic(
    body: IracemaAskRequestDto,
    user: Dict[str, Any] = Depends(get_current_user),
    service: IIracemaAskService = Depends(get_iracema_ask_service),
) -> IracemaAskResponseDto:
    """
    Endpoint principal do chatbot Iracema.

    - Requer autenticação Bearer (token emitido pelo /auth/login).
    - Orquestra pergunta → SQL → PostgreSQL → explicação em linguagem natural.
    """
    try:
        # service.ask é síncrono
        return service.ask_heuristic(body)
    except Exception as ex:
        # fallback defensivo (idealmente logar aqui)
        raise HTTPException(status_code=500, detail=str(ex))

@router.post(
    "/ask/ai",
    response_model=IracemaAskResponseDto,
    tags=["Iracema"],
)
async def ask_iracema_ai(
    body: IracemaAskRequestDto,
    user: Dict[str, Any] = Depends(get_current_user),
    service: IIracemaAskService = Depends(get_iracema_ask_service),
) -> IracemaAskResponseDto:
    """
    Endpoint principal do chatbot Iracema.

    - Requer autenticação Bearer (token emitido pelo /auth/login).
    - Orquestra pergunta → SQL → PostgreSQL → explicação em linguagem natural.
    """
    try:
        # service.ask é síncrono
        return service.ask_ai(body)
    except Exception as ex:
        # fallback defensivo (idealmente logar aqui)
        raise HTTPException(status_code=500, detail=str(ex))
    
@router.post("/ask/fc")
def ask_fc(
    request: IracemaAskRequestDto,
    svc: IIracemaAskByFCService = Depends(get_iracema_ask_fc_service),
):
    return svc.ask_fc(request)