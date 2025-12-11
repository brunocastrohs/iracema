# Application/interfaces/i_iracema_ask_service.py

from abc import ABC, abstractmethod

from Application.dto.iracema_ask_dto import (
    IracemaAskRequestDto,
    IracemaAskResponseDto,
)


class IIracemaAskService(ABC):
    """
    Orquestra o pipeline: pergunta → SQL → PostgreSQL → explicação.
    """

    @abstractmethod
    async def ask(self, request: IracemaAskRequestDto) -> IracemaAskResponseDto:
        """
        Executa o fluxo completo do Iracema para uma pergunta.
        """
