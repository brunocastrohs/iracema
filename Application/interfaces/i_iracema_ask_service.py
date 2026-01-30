from abc import ABC, abstractmethod
from Application.dto.iracema_ask_dto import IracemaAskRequestDto, IracemaAskResponseDto


class IIracemaAskService(ABC):
    @abstractmethod
    def ask(self, request: IracemaAskRequestDto) -> IracemaAskResponseDto:
        """
        Executa o fluxo:
        pergunta → gera SQL → executa → explica resultado.
        """
        raise NotImplementedError

    @abstractmethod
    def ask_heuristic(self, request: IracemaAskRequestDto) -> IracemaAskResponseDto:
        """
        Executa o fluxo:
        pergunta → gera SQL → executa → explica resultado.
        """
        raise NotImplementedError

    @abstractmethod
    def ask_ai(self, request: IracemaAskRequestDto) -> IracemaAskResponseDto:
        """
        Executa o fluxo:
        pergunta → gera SQL → executa → explica resultado.
        """
        raise NotImplementedError