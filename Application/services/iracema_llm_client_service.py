from typing import List, Optional

from Application.interfaces.i_iracema_llm_client import IIracemaLLMClient
from Application.interfaces.i_iracema_rag_retrieve_service import IIracemaRagRetrieveService
from Application.helpers.iracema_prompt_helper import (
    build_sql_generation_prompt,
    build_explanation_prompt,
)
from External.ai.langchain_ollama_provider import LangChainOllamaProvider
from Application.dto.iracema_sql_example_dto import IracemaSqlExampleDto

def build_examples_block(examples: List[IracemaSqlExampleDto]) -> str:
    if not examples:
        return ""

    lines = ["### Exemplos"]
    for i, ex in enumerate(examples, 1):
        lines.append(f"-- Exemplo {i}")
        lines.append("Pergunta:")
        lines.append(ex.question.strip())
        lines.append("")
        lines.append("SQL:")
        lines.append(ex.sql.strip())
        lines.append("")
    return "\n".join(lines)


def inject_examples_before_sql(
    prompt_base: str,
    examples_block: str | None,
) -> str:
    """
    Injeta o bloco de exemplos imediatamente antes do '### SQL' final.
    Assume que o prompt_base já contém '### SQL'.
    """
    if not examples_block:
        return prompt_base

    marker = "### SQL"
    if marker not in prompt_base:
        raise ValueError("Prompt base não contém marcador '### SQL'")

    before, after = prompt_base.rsplit(marker, 1)

    return (
        before.rstrip()
        + "\n\n"
        + examples_block.strip()
        + "\n\n"
        + marker
        + after
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
        print("Vai executar build_sql_generation_prompt")
        prompt = build_sql_generation_prompt(schema_description, question, top_k)

        # 2) injeta exemplos recuperados (RAG) se disponível
        print("Vai executar get_similar_sql_examples")
        if self._rag_retriever and table_identifier:
            examples = self._rag_retriever.get_similar_sql_examples(
                table_identifier=table_identifier,
                question=question,
                k=4,
            )
            
            print("Vai executar build_examples_block")
            examples_block = build_examples_block(examples)

            print("Vai executar inject_examples_before_sql")
            prompt = inject_examples_before_sql(
                prompt_base=prompt,
                examples_block=examples_block,
            )

        print("Vai executar mandar prompt para llm")
        
        print(prompt)

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
