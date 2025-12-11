# External/vector/chromadb_vector_store.py

import chromadb
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings

from External.vector.vector_store_base import VectorStoreBase


class ChromaDBVectorStore(VectorStoreBase):
    """
    Encapsula ChromaDB e provê um retriever LangChain.
    """

    def __init__(self, persist_directory: str, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        self.persist_directory = persist_directory

        self.client = chromadb.PersistentClient(path=persist_directory)
        self.embedding = HuggingFaceEmbeddings(model_name=model_name)

        self.db = Chroma(
            client=self.client,
            collection_name="iracema_collection",
            embedding_function=self.embedding,
        )

    def as_retriever(self):
        return self.db.as_retriever(search_kwargs={"k": 5})
