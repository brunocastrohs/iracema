# Application/services/iracema_llm_client_service.py

from typing import List, Dict, Any

from Application.interfaces.i_iracema_llm_client import IIracemaLLMClient
from Application.helpers.iracema_prompt_helper import (
    build_sql_generation_prompt,
    build_explanation_prompt,
)
from External.ai.langchain_ollama_provider import LangChainOllamaProvider


class IracemaLLMClient(IIracemaLLMClient):
    def __init__(self, settings):
        self.sql_llm = LangChainOllamaProvider(
            model=settings.LLM_MODEL_SQL,          # qwen
            base_url=settings.LLM_BASE_URL,
            temperature=0.0,
            num_predict=256,
        )

        self.explainer_llm = LangChainOllamaProvider(
            model=settings.LLM_MODEL_EXPLAINER,    # tinyllama
            base_url=settings.LLM_BASE_URL,
            temperature=0.0,
            num_predict=256,
        )

    def generate_sql(self, question: str, top_k: int) -> str:
        prompt = build_sql_generation_prompt(question, top_k)
        return self.sql_llm.invoke(prompt)

    def explain_result(
        self,
        question: str,
        sql_executed: str,
        rows: list,
        rowcount: int,
    ) -> str:
        prompt = build_explanation_prompt(
            question, sql_executed, rows, rowcount
        )
        return self.explainer_llm.invoke(prompt)