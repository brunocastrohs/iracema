# Data/interfaces/i_iracema_message_repository.py

from abc import ABC, abstractmethod
from typing import List, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from Domain.iracema_message_model import IracemaMessage
from Domain.iracema_enums import MessageRoleEnum


class IIracemaMessageRepository(ABC):
    @abstractmethod
    def add_message(
        self,
        session: Session,
        conversation_id: UUID,
        role: MessageRoleEnum,
        content: str,
    ) -> IracemaMessage:
        """Registra uma nova mensagem na conversa."""

    @abstractmethod
    def list_last_by_conversation(
        self,
        session: Session,
        conversation_id: UUID,
        limit: int = 10,
    ) -> List[IracemaMessage]:
        """
        Lista as últimas N mensagens da conversa.

        Recomendação na implementação:
        - buscar DESC por created_at/id
        - depois inverter para retornar em ordem cronológica (antigo → novo)
        """
   
    # 🆕 útil para guiar start e prompts (ex.: "última pergunta do user")
    @abstractmethod
    def get_last_user_message(
        self,
        session: Session,
        conversation_id: UUID,
    ) -> Optional[IracemaMessage]:
        """Retorna a última mensagem com role=user, se existir."""