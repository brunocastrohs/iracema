# External/vector/chromadb_vector_store.py

from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from typing import Optional, Dict, Any


from External.vector.vector_store_base import VectorStoreBase


from typing import Optional, Dict, Any

class ChromaDBVectorStore:
    def __init__(self, persist_directory: str):
        self.persist_directory = persist_directory
        self._vs = None  # aqui fica o Chroma do LangChain

    def _ensure_vs(self):
        if self._vs is not None:
            return

        embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

        self._vs = Chroma(
            persist_directory=self.persist_directory,
            embedding_function=embeddings,
        )

    def as_retriever(self, search_kwargs: Optional[Dict[str, Any]] = None):
        self._ensure_vs()
        return self._vs.as_retriever(search_kwargs=search_kwargs or {})
