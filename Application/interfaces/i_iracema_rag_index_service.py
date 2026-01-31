# Application/interfaces/i_iracema_rag_index_service.py

from abc import ABC, abstractmethod
from typing import Optional

class IIracemaRagIndexService(ABC):
    @abstractmethod
    def index_success(
        self,
        table_identifier: str,
        question: str,
        sql_executed: str,
        rowcount: int,
        reason: str,
        duration_ms: float,
        conversation_id: Optional[int] = None,
        message_id: Optional[int] = None,
    ) -> None:
        raise NotImplementedError()
