# Application/services/iracema_rag_retrieve_service.py

from typing import List
import re
from typing import List, Optional
from Application.dto.iracema_sql_example_dto import IracemaSqlExampleDto
from Application.interfaces.i_iracema_rag_retrieve_service import IIracemaRagRetrieveService
from External.vector.chromadb_vector_store import ChromaDBVectorStore
from Application.helpers.iracema_text_normalize_helper import normalize_question
from typing import List, Optional

_QUESTION_RE = re.compile(r"Pergunta:\s*(.*)", re.IGNORECASE)
_SQL_MARKER = "\nSQL:\n"

def _parse_example(doc: str) -> Optional[IracemaSqlExampleDto]:
    if not doc:
        return None

    m = _QUESTION_RE.search(doc)
    if not m:
        return None

    question = m.group(1).strip()

    if _SQL_MARKER not in doc:
        return None
    sql = doc.split(_SQL_MARKER, 1)[1].strip()

    if not sql:
        return None

    return IracemaSqlExampleDto(question=question, sql=sql)
class IracemaRagRetrieveService(IIracemaRagRetrieveService):
    def __init__(self, vector_store: ChromaDBVectorStore):
        self._vs = vector_store

    def get_similar_sql_examples(self, table_identifier: str, question: str, k: int = 4) -> List[IracemaSqlExampleDto]:
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

        examples: List[IracemaSqlExampleDto] = []
        for d in (docs or []):
            ex = _parse_example(d.page_content or "")
            if ex:
                examples.append(ex)

        return examples

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