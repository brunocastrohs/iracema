from langchain_ollama import ChatOllama
from typing import Optional
from langchain.schema import BaseRetriever

class LangChainOllamaProvider:
    def __init__(
        self,
        model: str,
        base_url: str,
        retriever: Optional[BaseRetriever] = None,
        temperature: float = 0.0,
        num_predict:int = 256,
    ):
        self.model = model
        self.retriever = retriever

        self.llm = ChatOllama(
            model=model,
            base_url=base_url,
            temperature=temperature,
            num_predict=num_predict

        )

    def invoke(self, prompt: str) -> str:
        if self.retriever:
            docs = self.retriever.get_relevant_documents(prompt)
            context = "\n".join(d.page_content for d in docs)
            prompt = f"""Contexto:
                        {context}

                        Pergunta:
                        {prompt}
                        """
        response = self.llm.invoke(prompt)
        return response.content
