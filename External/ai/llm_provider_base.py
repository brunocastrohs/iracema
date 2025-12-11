# External/ai/llm_provider_base.py

from abc import ABC, abstractmethod

class LLMProviderBase(ABC):
    """
    Interface base para provedores de LLM.
    A camada Application só deve depender desta interface.
    """

    @abstractmethod
    async def chat_completion(
        self,
        system_prompt: str,
        user_prompt: str,
        model: str,
        temperature: float = 0.0,
    ) -> str:
        """
        Executa uma chamada de completions/conversação.
        Deve retornar o texto final da resposta.
        """
        raise NotImplementedError()
