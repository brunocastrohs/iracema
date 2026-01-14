from abc import ABC, abstractmethod
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from Domain.iracema_conversation_context_model import IracemaConversationContext


class IIracemaConversationContextRepository(ABC):
    @abstractmethod
    def get_by_conversation_id(
        self,
        session: Session,
        conversation_id: UUID,
    ) -> Optional[IracemaConversationContext]:
        """Obtém o contexto atual da conversa (1:1)."""

    @abstractmethod
    def ensure_exists(
        self,
        session: Session,
        conversation_id: UUID,
    ) -> IracemaConversationContext:
        """
        Garante que existe um contexto para a conversa.
        Se não existir, cria com defaults (phase START, status EMPTY).
        """

    @abstractmethod
    def update(
        self,
        session: Session,
        context: IracemaConversationContext,
    ) -> IracemaConversationContext:
        """Atualiza o contexto (status, phase, resumo, start_state etc.)."""

    @abstractmethod
    def set_datasource_selected(
        self,
        session: Session,
        conversation_id: UUID,
        datasource_id: int,
        table_identifier: str,
        prompt_inicial_snapshot: Optional[str],
    ) -> IracemaConversationContext:
        """
        Fixa a datasource/tabela ao final do START.

        Recomendação:
        - status = READY
        - phase = ASK
        - salvar table_identifier e snapshot do prompt
        """

    @abstractmethod
    def clear_selection(
        self,
        session: Session,
        conversation_id: UUID,
    ) -> IracemaConversationContext:
        """
        Limpa datasource e volta o contexto para START.
        Útil se o usuário pedir para trocar a camada/tabela.
        """
