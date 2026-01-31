from typing import List, Optional

from Application.interfaces.i_iracema_llm_client import IIracemaLLMClient
from Application.interfaces.i_iracema_rag_retrieve_service import IIracemaRagRetrieveService
from Application.helpers.iracema_prompt_helper import (
    build_sql_generation_prompt,
    build_explanation_prompt,
)
from External.ai.langchain_ollama_provider import LangChainOllamaProvider


def _build_examples_block(examples: List[str]) -> str:
    if not examples:
        return ""

    joined = "\n\n---\n\n".join(examples[:6])
    return (
        "\n\n"
        "EXEMPLOS BEM-SUCEDIDOS (use como referência; adapte apenas filtros/colunas quando necessário):\n"
        f"{joined}\n"
    )


class IracemaLLMClient(IIracemaLLMClient):
    def __init__(
        self,
        settings,
        rag_retriever: Optional[IIracemaRagRetrieveService] = None,
    ):
        self._rag_retriever = rag_retriever

        self.sql_llm = LangChainOllamaProvider(
            model=settings.LLM_MODEL_SQL,
            base_url=settings.LLM_BASE_URL,
            temperature=0.0,
            num_predict=256,
        )

        self.explainer_llm = LangChainOllamaProvider(
            model=settings.LLM_MODEL_EXPLAINER,
            base_url=settings.LLM_BASE_URL,
            temperature=0.0,
            num_predict=256,
        )

    def generate_sql(
        self,
        schema_description: str,
        question: str,
        top_k: int,
        table_identifier: Optional[str] = None,
    ) -> str:
        # 1) prompt base (como você já tinha)
        prompt = build_sql_generation_prompt(schema_description, question, top_k)

        # 2) injeta exemplos recuperados (RAG) se disponível
        if self._rag_retriever and table_identifier:
            examples = self._rag_retriever.get_similar_sql_examples(
                table_identifier=table_identifier,
                question=question,
                k=4,
            )
            prompt = prompt + _build_examples_block(examples)

        return self.sql_llm.invoke(prompt)

    def explain_result(
        self,
        schema_description: str,
        question: str,
        sql_executed: str,
        rows: list,
        rowcount: int,
    ) -> str:
        prompt = build_explanation_prompt(
            schema_description, question, sql_executed, rows, rowcount
        )
        return self.explainer_llm.invoke(prompt)
