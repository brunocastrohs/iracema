# Application/services/iracema_llm_client_service.py

from typing import List, Dict, Any

from External.ai.llm_provider_base import LLMProviderBase

from Application.helpers.iracema_prompt_helper import (
    build_sql_generation_prompt,
    build_explanation_prompt,
)
from Application.interfaces.i_iracema_llm_client import IIracemaLLMClient


class IracemaLLMClient(IIracemaLLMClient):
    """
    Orquestrador semântico da Iracema.

    - Monta o prompt de geração de SQL.
    - Monta o prompt de explicação do resultado.
    - Chama um provider de LLM da camada External (OpenAI, Phi-3, LangChain, etc.).
    """

    def __init__(
        self,
        provider: LLMProviderBase,
        model_sql: str,
        model_explainer: str | None = None,
    ) -> None:
        self._provider = provider
        self._model_sql = model_sql
        self._model_explainer = model_explainer or model_sql

    async def generate_sql(self, question: str, top_k: int) -> str:
        """
        Gera um comando SQL SELECT válido para PostgreSQL a partir da pergunta.
        """
        prompt = build_sql_generation_prompt(question, top_k)

        sql = await self._provider.chat_completion(
            system_prompt="Você é um gerador de SQL para PostgreSQL.",
            user_prompt=prompt,
            model=self._model_sql,
            temperature=0.1,
        )

        return sql.strip()

    async def explain_result(
        self,
        question: str,
        sql_executed: str,
        rows: List[Dict[str, Any]],
        rowcount: int,
    ) -> str:
        """
        Gera uma resposta em linguagem natural explicando o resultado da consulta.
        """
        prompt = build_explanation_prompt(question, sql_executed, rows, rowcount)

        answer = await self._provider.chat_completion(
            system_prompt="Você é um assistente que explica resultados de consultas SQL.",
            user_prompt=prompt,
            model=self._model_explainer,
            temperature=0.2,
        )

        return answer.strip()
