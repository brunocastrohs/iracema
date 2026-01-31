# External/vector/chromadb_vector_store.py

from typing import Optional, Dict, Any, List

from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from chromadb.config import Settings

client_settings = Settings(anonymized_telemetry=False)

class ChromaDBVectorStore:
    def __init__(
        self,
        persist_directory: str,
        collection_name: str = "iracema_memory",
    ):
        self.persist_directory = persist_directory
        self.collection_name = collection_name
        self._vs = None

    def _ensure_vs(self):
        if self._vs is not None:
            return

        embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2"
        )

        self._vs = Chroma(
            persist_directory=self.persist_directory,
            embedding_function=embeddings,
            collection_name=self.collection_name,
            client_settings=client_settings,

        )

    def add_texts(
        self,
        texts: List[str],
        metadatas: Optional[List[Dict[str, Any]]] = None,
        ids: Optional[List[str]] = None,
    ) -> None:
        self._ensure_vs()
        self._vs.add_texts(texts=texts, metadatas=metadatas, ids=ids)
        #self._vs.persist()

    def similarity_search(self, query: str, k: int = 5, where: Optional[Dict[str, Any]] = None):
        self._ensure_vs()
        return self._vs.similarity_search(query, k=int(k), filter=where or {})


    def as_retriever(self, search_kwargs: Optional[Dict[str, Any]] = None):
        self._ensure_vs()
        return self._vs.as_retriever(search_kwargs=search_kwargs or {})
