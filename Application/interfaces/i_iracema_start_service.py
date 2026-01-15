from abc import ABC, abstractmethod

from Application.dto.iracema_start_dto import (
    IracemaStartRequestDto,
    IracemaStartResponseDto,
)


class IIracemaStartService(ABC):
    @abstractmethod
    def start(self, request: IracemaStartRequestDto) -> IracemaStartResponseDto:
        """
        Fase 1 — START:
        - Resolve contexto de dados (datasource/tabela)
        - Registra mensagens
        - Atualiza ConversationContext
        - Retorna candidato(s) ou a tabela final (identificador_tabela)
        """
        raise NotImplementedError
