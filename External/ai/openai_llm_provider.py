# External/ai/openai_llm_provider.py

from openai import OpenAI
from External.ai.llm_provider_base import LLMProviderBase


class OpenAILLMProvider(LLMProviderBase):
    """
    Provedor baseado em API compatível com OpenAI (OpenAI, Azure, Groq, LocalAI, Ollama, etc.).
    """

    def __init__(self, api_key: str, base_url: str | None = None):
        self._client = OpenAI(api_key=api_key, base_url=base_url)

    async def chat_completion(
        self,
        system_prompt: str,
        user_prompt: str,
        model: str,
        temperature: float = 0.0,
    ) -> str:
        response = self._client.chat.completions.create(
            model=model,
            temperature=temperature,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )

        content = response.choices[0].message.content or ""
        return content.strip()
