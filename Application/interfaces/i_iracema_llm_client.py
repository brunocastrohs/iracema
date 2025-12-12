from abc import ABC, abstractmethod
from typing import List, Dict, Any


class IIracemaLLMClient(ABC):
    """
    Abstração do cliente de LLM da Iracema.

    Responsabilidades:
    - Gerar SQL a partir de linguagem natural
    - Explicar resultados de consultas SQL

    Implementações concretas vivem em Application/services.
    """

    @abstractmethod
    def generate_sql(self, question: str, top_k: int) -> str:
        """
        Gera um comando SQL SELECT válido para PostgreSQL
        a partir da pergunta do usuário.
        """
        raise NotImplementedError

    @abstractmethod
    def explain_result(
        self,
        question: str,
        sql_executed: str,
        rows: List[Dict[str, Any]],
        rowcount: int,
    ) -> str:
        """
        Gera uma resposta em linguagem natural explicando
        o resultado da consulta SQL.
        """
        raise NotImplementedError
