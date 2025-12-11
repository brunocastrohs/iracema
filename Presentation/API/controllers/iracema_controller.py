# Presentation/API/controllers/iracema_controller.py

from typing import Any, Dict

from fastapi import APIRouter, Depends

from Application.dto.iracema_ask_dto import (
    IracemaAskRequestDto,
    IracemaAskResponseDto,
)
from Application.interfaces.i_iracema_ask_service import IIracemaAskService

from Presentation.API.helpers.iracema_dependencies_helper import (
    get_current_user,
    get_iracema_ask_service,
)

router = APIRouter()

@router.get("/health", tags=["Iracema"])
def health_check() -> Dict[str, str]:
    """
    Endpoint simples de healthcheck da API do Iracema.
    """
    return {"status": "ok"}


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
    # `user` contém o payload do JWT; dá pra usar user["sub"] no futuro.
    return await service.ask(body)
