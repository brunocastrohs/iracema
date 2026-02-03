# Application/helpers/sql/sql_intent_detector.py

import re

_SCHEMA_INTENT = re.compile(r"\b(colunas?|campos?|atributos?|esquema|schema|estrutura)\b", re.IGNORECASE)
_GROUPBY_INTENT = re.compile(r"\b(de\s+cada|por\s+cada|por\b|agrupad[oa]\s+por|separad[oa]\s+por)\b", re.IGNORECASE)

_DISTINCT_INTENT = re.compile(
    r"\b(quais|quais\s+s[aã]o|listar|lista|existem|existentes|valores|op[cç][oõ]es|categorias|tipos|nomes|diferentes|distint[oa]s|distinct)\b",
    re.IGNORECASE,
)

_COUNT_INTENT = re.compile(
    r"\b(quantos|quantas|conta|contagem|n[uú]mero\s+de\s+registros|n[uú]mero\s+de\s+linhas|registros)\b",
    re.IGNORECASE,
)

_SUM_INTENT = re.compile(r"\b(soma|somat[oó]rio|somar|total)\b", re.IGNORECASE)

_DETAIL_INTENT = re.compile(
    r"\b(detalhe|detalhes|mostrar|exibir|trazer|todas?\s+as?\s+linhas|tudo)\b",
    re.IGNORECASE,
)

_AREA_HINT = re.compile(r"\b([aá]rea)\b", re.IGNORECASE)
_PERIM_HINT = re.compile(r"\b(per[ií]metro)\b", re.IGNORECASE)

def wants_groupby(question: str) -> bool:
    return bool(_GROUPBY_INTENT.search(question or ""))

def is_schema_question(question: str) -> bool:
    return bool(_SCHEMA_INTENT.search(question or ""))

def is_count_question(question: str) -> bool:
    return bool(_COUNT_INTENT.search(question or ""))

def is_sum_question(question: str) -> bool:
    return bool(_SUM_INTENT.search(question or ""))

def has_area_hint(question: str) -> bool:
    return bool(_AREA_HINT.search(question or ""))

def has_perim_hint(question: str) -> bool:
    return bool(_PERIM_HINT.search(question or ""))

def is_distinct_list_question(question: str) -> bool:
    q = question or ""
    # bloqueia perguntas que pedem detalhe ou schema
    if _DETAIL_INTENT.search(q):
        return False
    if _SCHEMA_INTENT.search(q):
        return False
    # DISTINCT: sim, mas NÃO quando for contagem
    return bool(_DISTINCT_INTENT.search(q)) and not bool(_COUNT_INTENT.search(q))
