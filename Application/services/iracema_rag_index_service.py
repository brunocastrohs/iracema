# Application/services/iracema_rag_index_service.py

import hashlib
from datetime import datetime
from typing import Optional

from Application.interfaces.i_iracema_rag_index_service import IIracemaRagIndexService
from External.vector.chromadb_vector_store import ChromaDBVectorStore
from Application.helpers.iracema_text_normalize_helper import normalize_question



def _stable_id(table_identifier: str, question: str, sql: str) -> str:
    raw = f"{table_identifier}||{question.strip()}||{sql.strip()}".encode("utf-8")
    return hashlib.sha1(raw).hexdigest()


class IracemaRagIndexService(IIracemaRagIndexService):
    def __init__(self, vector_store: ChromaDBVectorStore):
        self._vs = vector_store

    def index_success(
        self,
        table_identifier: str,
        question: str,
        sql_executed: str,
        rowcount: int,
        reason: str,
        duration_ms: float,
        conversation_id: Optional[int] = None,
        message_id: Optional[int] = None,
    ) -> None:
        doc = (
            f"[TABLE={table_identifier}]\n"
            f"Pergunta: {question.strip()}\n"
            f"SQL:\n{sql_executed.strip()}\n"
        )

        meta = {
            "type": "qa_sql",
            "question_norm": normalize_question(question),
            "question_raw": question.strip(),
            "table_identifier": table_identifier,
            "rowcount": int(rowcount),
            "reason": str(reason),
            "duration_ms": float(duration_ms),
            #"conversation_id": int(conversation_id) if conversation_id is not None else None,
            #"message_id": int(message_id) if message_id is not None else None,
            "created_at": datetime.utcnow().isoformat() + "Z",
        }

        doc_id = _stable_id(table_identifier, question, sql_executed)
        self._vs.add_texts(texts=[doc], metadatas=[meta], ids=[doc_id])
