from abc import ABC, abstractmethod
from typing import List, Dict, Any


class IIracemaLLMClient(ABC):
    @abstractmethod
    def generate_sql(self, schema_description: str, question: str, top_k: int) -> str:
        """Gera SQL (SELECT) a partir da pergunta do usuário."""

    @abstractmethod
    def explain_result(
        self,
        schema_description: str,
        question: str,
        sql_executed: str,
        rows: List[Dict[str, Any]],
        rowcount: int,
    ) -> str:
        """Explica resultado SQL em linguagem natural."""
