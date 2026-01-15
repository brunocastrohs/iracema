import re
from dataclasses import dataclass
from typing import Optional


_SELECT_BY_ID = re.compile(r"\b(id|op[cç][aã]o)\s*[:#]?\s*(\d+)\b", re.IGNORECASE)
_SELECT_BY_TABLE = re.compile(r"\b(tabela|camada)\s*[:#]?\s*([a-zA-Z0-9_]+)\b", re.IGNORECASE)

_LIST_INTENT = re.compile(r"\b(listar|lista|op[cç][oõ]es|opcoes|quais\s+s[aã]o|mostre|ver|cat[aá]logo)\b", re.IGNORECASE)
_CHANGE_INTENT = re.compile(r"\b(trocar|mudar|alterar|outra\s+camada|outra\s+tabela|resetar|recome[cç]ar)\b", re.IGNORECASE)


@dataclass
class StartIntent:
    kind: str  # "select_id" | "select_table" | "list" | "change" | "search"
    value: Optional[str] = None


def detect_start_intent(message: str) -> StartIntent:
    text = (message or "").strip()

    m = _SELECT_BY_ID.search(text)
    if m:
        return StartIntent(kind="select_id", value=m.group(2))

    m = _SELECT_BY_TABLE.search(text)
    if m:
        return StartIntent(kind="select_table", value=m.group(2))

    if _CHANGE_INTENT.search(text):
        return StartIntent(kind="change", value=None)

    if _LIST_INTENT.search(text):
        return StartIntent(kind="list", value=None)

    return StartIntent(kind="search", value=text)
