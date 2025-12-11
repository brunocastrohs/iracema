# External/ai/phi3_local_llm_provider.py

import requests
from External.ai.llm_provider_base import LLMProviderBase


class Phi3LocalLLMProvider(LLMProviderBase):
    """
    Provedor para Phi-3 rodando localmente (Ollama, llama.cpp HTTP server, LM Studio).
    Espera um endpoint HTTP compatível com completions.
    """

    def __init__(self, base_url: str = "http://localhost:11434"):
        self.base_url = base_url.rstrip("/")

    async def chat_completion(
        self,
        system_prompt: str,
        user_prompt: str,
        model: str,
        temperature: float = 0.0,
    ) -> str:

        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature,
            "stream": False,
        }

        resp = requests.post(f"{self.base_url}/v1/chat/completions", json=payload)
        resp.raise_for_status()
        data = resp.json()

        return data["choices"][0]["message"]["content"].strip()
