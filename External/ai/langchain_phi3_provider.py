# External/ai/langchain_phi3_provider.py

from External.ai.llm_provider_base import LLMProviderBase

from langchain_community.chat_models import ChatOpenAI
from langchain.chains import RetrievalQA
from langchain_core.prompts import ChatPromptTemplate


class LangChainPhi3Provider(LLMProviderBase):
    """
    Provider baseado em LangChain:
    - Carrega Phi-3 via API compatível (OpenAI-like)
    - Utiliza ChromaDB como store vetorial para RAG
    """

    def __init__(
        self,
        api_key: str,
        base_url: str,
        model: str,
        retriever,
    ):
        self.llm = ChatOpenAI(
            api_key=api_key,
            base_url=base_url,
            model=model,
            temperature=0.0,
        )
        self.retriever = retriever

        system_template = """
        Você é um assistente avançado chamado IRACEMA. Utilize o contexto para responder.
        """
        self.prompt = ChatPromptTemplate.from_messages(
            [
                ("system", system_template),
                ("user", "{question}"),
            ]
        )

        self.chain = RetrievalQA.from_chain_type(
            llm=self.llm,
            retriever=self.retriever,
            chain_type="stuff",
            return_source_documents=False,
            chain_type_kwargs={"prompt": self.prompt},
        )

    async def chat_completion(
        self,
        system_prompt: str,
        user_prompt: str,
        model: str,
        temperature: float = 0.0,
    ) -> str:

        # Aqui ignoramos model/temperature porque LangChain já controla isso internamente
        result = self.chain.invoke({"question": user_prompt})
        return result["result"].strip()
