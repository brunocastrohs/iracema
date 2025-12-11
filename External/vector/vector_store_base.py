# External/vector/vector_store_base.py

from abc import ABC, abstractmethod


class VectorStoreBase(ABC):
    """
    Interface genérica para banco vetorial.
    """

    @abstractmethod
    def as_retriever(self):
        """
        Retorna um retriever compatível com LangChain.
        """
        raise NotImplementedError()
