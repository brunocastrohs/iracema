import json
from typing import Any, Dict

from Application.interfaces.i_iracema_fc_client import IIracemaFCClient
from Application.dto.iracema_query_plan_dto import QueryPlanArgsDto

from External.ai.langchain_ollama_provider import LangChainOllamaProvider

def _extract_json(raw: str) -> Dict[str, Any]:
    s = (raw or "").strip()

    # tenta achar o primeiro { ... } válido
    start = s.find("{")
    end = s.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("LLM não retornou JSON válido.")
    payload = s[start : end + 1]
    return json.loads(payload)

class IracemaFCOllamaClient(IIracemaFCClient):
    def __init__(self, settings):
        self.llm = LangChainOllamaProvider(
            model=getattr(settings, "LLM_MODEL_FC", settings.LLM_MODEL_FC),
            base_url=settings.LLM_BASE_URL,
            temperature=0.0,
            num_predict=256,
        )

    def generate_query_plan(
        self,
        prompt_inicial_fc: str,
        question: str,
        columns_meta: list[dict],
        top_k: int,
    ) -> QueryPlanArgsDto:
        # prompt_inicial_fc já inclui {PERGUNTA_DO_USUARIO}
        prompt = (prompt_inicial_fc or "").replace("{PERGUNTA_DO_USUARIO}", question.strip())

        prompt += (
            "\n\nRETORNE APENAS JSON. Sem markdown. Sem texto extra.\n"
            "Campos esperados: intent, target_column, value_column, group_by, filters, limit.\n"
        )
        
        print(prompt)

        raw = self.llm.invoke(prompt)
        data = _extract_json(raw)
        return QueryPlanArgsDto.model_validate(data)
