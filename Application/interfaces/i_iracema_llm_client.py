# Application/interfaces/i_iracema_llm_client.py

from abc import ABC, abstractmethod
from typing import List, Dict, Any


class IIracemaLLMClient(ABC):
    """
    Abstração do cliente de LLM.
    A implementação concreta (OpenAI, Phi-3, Llama-3 etc.) virá em services.
    """

    @abstractmethod
    async def generate_sql(self, question: str, top_k: int) -> str:
        """
        Gera um comando SQL SELECT válido para PostgreSQL a partir da pergunta do usuário.
        """

    @abstractmethod
    async def explain_result(
        self,
        question: str,
        sql_executed: str,
        rows: List[Dict[str, Any]],
        rowcount: int,
    ) -> str:
        """
        Gera uma resposta em linguagem natural explicando o resultado da consulta SQL.
        """
