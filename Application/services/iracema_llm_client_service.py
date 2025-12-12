# Application/services/iracema_llm_client_service.py

from typing import List, Dict, Any

from Application.interfaces.i_iracema_llm_client import IIracemaLLMClient
from Application.helpers.iracema_prompt_helper import (
    build_sql_generation_prompt,
    build_explanation_prompt,
)
from External.ai.langchain_phi3_provider import LangChainPhi3Provider


class IracemaLLMClient(IIracemaLLMClient):
    """
    Orquestrador semântico da Iracema.

    Responsabilidades:
    - Montar prompts (SQL e explicação)
    - Acionar o provider de LLM
    - Retornar respostas puras (sem formatação de API)
    """

    def __init__(self, vector_store, settings):
        self.settings = settings

        retriever = vector_store.as_retriever(
            search_kwargs={"k": 5}  # default; pode ser sobrescrito no prompt
        )

        # Provider único (mesmo modelo pode servir aos dois fluxos)
        self.llm = LangChainPhi3Provider(
            model=settings.LLM_MODEL_SQL,
            base_url=settings.LLM_BASE_URL,
            retriever=retriever,
            temperature=settings.LLM_TEMPERATURE,
        )

    def generate_sql(self, question: str, top_k: int) -> str:
        """
        Gera um comando SQL SELECT válido para PostgreSQL.
        """
        prompt = build_sql_generation_prompt(question, top_k)

        sql = self.llm.invoke(prompt)

        return sql.strip()

    def explain_result(
        self,
        question: str,
        sql_executed: str,
        rows: List[Dict[str, Any]],
        rowcount: int,
    ) -> str:
        """
        Gera uma explicação em linguagem natural do resultado SQL.
        """
        prompt = build_explanation_prompt(
            question=question,
            sql_executed=sql_executed,
            rows=rows,
            rowcount=rowcount,
        )

        answer = self.llm.invoke(prompt)

        return answer.strip()
