# Application/services/iracema_rag_retrieve_service.py

from typing import List

from Application.interfaces.i_iracema_rag_retrieve_service import IIracemaRagRetrieveService
from External.vector.chromadb_vector_store import ChromaDBVectorStore
from Application.helpers.iracema_text_normalize_helper import normalize_question
from typing import List, Optional


class IracemaRagRetrieveService(IIracemaRagRetrieveService):
    def __init__(self, vector_store: ChromaDBVectorStore):
        self._vs = vector_store

    def get_similar_sql_examples(
        self,
        table_identifier: str,
        question: str,
        k: int = 4,
    ) -> List[str]:
        where = {
            "$and": [
                {"type": "qa_sql"},
                {"table_identifier": table_identifier},
            ]
        }

        docs = self._vs.similarity_search(
            query=f"[TABLE={table_identifier}] {question}",
            k=int(k),
            where=where,
        )

        return [d.page_content for d in (docs or [])]

    def try_get_exact_sql(self, table_identifier: str, question: str) -> Optional[str]:
        qn = normalize_question(question)

        where = {
            "type": "qa_sql",
            "table_identifier": table_identifier,
            "question_norm": qn,
        }

        docs = self._vs.similarity_search(
            query=f"[TABLE={table_identifier}] {question}",
                k=1,
                where={
                    "$and": [
                        {"type": "qa_sql"},
                        {"table_identifier": table_identifier},
                        {"question_norm": qn},
                    ]
                },
        )

        if not docs:
            return None

        content = docs[0].page_content or ""
        return self._extract_sql_from_doc(content)

    def _extract_sql_from_doc(self, content: str) -> Optional[str]:
        # extrai trecho depois de "SQL:"
        marker = "\nSQL:\n"
        if marker not in content:
            return None
        sql = content.split(marker, 1)[1].strip()
        return sql or None