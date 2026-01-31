# Application/interfaces/i_iracema_rag_retrieve_service.py

from abc import ABC, abstractmethod
from typing import List, Optional

class IIracemaRagRetrieveService(ABC):
    @abstractmethod
    def get_similar_sql_examples(
        self,
        table_identifier: str,
        question: str,
        k: int = 4,
    ) -> List[str]:
        raise NotImplementedError()
    
    @abstractmethod
    def try_get_exact_sql(
        self,
        table_identifier: str,
        question: str,
    ) -> Optional[str]:
        raise NotImplementedError()