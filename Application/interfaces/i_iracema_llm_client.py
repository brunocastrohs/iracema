from abc import ABC, abstractmethod
from typing import Optional

class IIracemaLLMClient(ABC):
    @abstractmethod
    def generate_sql(
        self,
        schema_description: str,
        question: str,
        top_k: int,
        table_identifier: Optional[str] = None,
    ) -> str:
        raise NotImplementedError()

    @abstractmethod
    def explain_result(
        self,
        schema_description: str,
        question: str,
        sql_executed: str,
        rows: list,
        rowcount: int,
    ) -> str:
        raise NotImplementedError()
