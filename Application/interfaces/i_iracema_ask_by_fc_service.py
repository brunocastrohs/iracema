from abc import ABC, abstractmethod

from Application.dto.iracema_ask_dto import IracemaAskRequestDto, IracemaAskResponseDto
from Application.dto.iracema_fca_dto import FCAArgsDto
from Application.dto.iracema_fca_dto import FCAArgsDto

class IIracemaAskByFCService(ABC):
    """
    Serviço do endpoint /ask/fc.
    Este serviço usa Function Calling para gerar QueryPlan (JSON),
    compila SQL determinístico e executa no PostgreSQL.
    """

    @abstractmethod
    def ask_fc(self, request: IracemaAskRequestDto) -> IracemaAskResponseDto:
        raise NotImplementedError()

    @abstractmethod
    def ask_fc_with_args(self, request: IracemaAskRequestDto, fca: FCAArgsDto) -> IracemaAskResponseDto:
        raise NotImplementedError()