# Application/helpers/iracema_sql_policy_helper.py

import re
from dataclasses import dataclass
from typing import Optional


# -----------------------------
# INTENTS (PT-BR)
# -----------------------------

_DISTINCT_INTENT = re.compile(
    r"\b(quais|quais\s+s[aã]o|listar|lista|existem|existentes|valores|op[cç][oõ]es|categorias|tipos|nomes|diferentes|distint[oa]s|distinct)\b",
    re.IGNORECASE,
)

_COUNT_INTENT = re.compile(
    r"\b(quantos|quantas|conta|contagem|total)\b",
    re.IGNORECASE,
)

# Perguntas que geralmente pedem "tabela inteira" NÃO devem cair em distinct:
_DETAIL_INTENT = re.compile(
    r"\b(detalhe|detalhes|mostrar|exibir|trazer|todas?\s+as?\s+linhas|tudo)\b",
    re.IGNORECASE,
)


# -----------------------------
# COLUMN HINTS (MVP ZEEC)
# -----------------------------

_COL_HINTS = [
    ("sub_zonas", re.compile(r"\b(sub\s*zonas?|sub[-_\s]?zonas?)\b", re.IGNORECASE)),
    ("letra_subz", re.compile(r"\b(letra|sigla)\b", re.IGNORECASE)),
    ("zonas", re.compile(r"\b(zonas?|zona)\b", re.IGNORECASE)),
]


# -----------------------------
# NORMALIZATION / SAFETY
# -----------------------------

_CODE_FENCE_SQL = re.compile(r"```(?:sql)?\s*(.*?)\s*```", re.IGNORECASE | re.DOTALL)
SQL_SELECT_PATTERN = re.compile(r"^\s*select\s", re.IGNORECASE)
SQL_WITH_PATTERN = re.compile(r"^\s*with\s", re.IGNORECASE)

_LIMIT_PATTERN = re.compile(r"\blimit\s+\d+\b", re.IGNORECASE)

# Tabela alvo (MVP)
TABLE_FQN = 'public."1201_ce_zeec_zoneamento_p_litora_2021_pol"'


@dataclass
class SqlPlan:
    """
    Resultado do Planner/Policy.
    - sql: SQL final pronto para executar
    - used_template: True quando o Planner gerou SQL sem LLM
    - reason: motivo (debug/log)
    """
    sql: str
    used_template: bool
    reason: str


def extract_sql(raw: str) -> str:
    """Extrai SQL de ```sql ...``` e limpa crases/whitespace."""
    if not raw:
        return ""
    s = raw.strip()
    m = _CODE_FENCE_SQL.search(s)
    if m:
        s = m.group(1).strip()
    return s.strip("`").strip()


def is_safe_select(sql: str) -> bool:
    """Verifica se é SELECT/CTE e não contém DDL/DML óbvios."""
    stripped = sql.strip()
    if not stripped:
        return False

    # multi-statement?
    if ";" in stripped[:-1]:
        return False

    if not (SQL_SELECT_PATTERN.match(stripped) or SQL_WITH_PATTERN.match(stripped)):
        return False

    forbidden = [
        " insert ", " update ", " delete ", " drop ", " alter ", " truncate ",
        " create ", " grant ", " revoke ", " merge ", " call ", " execute ",
    ]
    lower_sql = f" {stripped.lower()} "
    return not any(tok in lower_sql for tok in forbidden)


def has_limit(sql: str) -> bool:
    return bool(_LIMIT_PATTERN.search(sql))


def ensure_limit(sql: str, top_k: int) -> str:
    """
    Garante LIMIT no final se não existir.
    """
    s = sql.strip().rstrip(";")
    if has_limit(s):
        return s + ";"
    return f"{s}\nLIMIT {int(top_k)};"


def detect_target_column(question: str) -> Optional[str]:
    """
    Detecta a coluna alvo provável: zonas / sub_zonas / letra_subz.
    """
    q = question or ""
    for col, rx in _COL_HINTS:
        if rx.search(q):
            return col

    # fallback: se é pergunta de distinct mas não citou coluna -> zonas
    if _DISTINCT_INTENT.search(q):
        return "zonas"
    return None


def is_distinct_list_question(question: str) -> bool:
    """
    Perguntas do tipo: "quais são as zonas existentes...".
    Evita false-positive quando usuário pede detalhes.
    """
    q = question or ""
    if _DETAIL_INTENT.search(q):
        return False
    return bool(_DISTINCT_INTENT.search(q)) and not bool(_COUNT_INTENT.search(q))


def is_count_question(question: str) -> bool:
    q = question or ""
    return bool(_COUNT_INTENT.search(q))


def build_distinct_query(column: str, top_k: int) -> str:
    return (
        f'SELECT DISTINCT {column} AS "Valor"\n'
        f"FROM {TABLE_FQN}\n"
        f"WHERE {column} IS NOT NULL\n"
        f'ORDER BY {column}\n'
        f"LIMIT {int(top_k)};"
    )


def build_count_query() -> str:
    return (
        'SELECT COUNT(*)::bigint AS "Total"\n'
        f"FROM {TABLE_FQN};"
    )


def plan_sql(question: str, raw_sql_from_llm: Optional[str], top_k: int) -> SqlPlan:
    """
    Planner + Policy.

    1) Se for DISTINCT-list: gera SQL template (sem LLM).
    2) Se for COUNT: gera SQL template (sem LLM).
    3) Caso geral: usa SQL do LLM, aplica normalização + LIMIT + segurança.
    """
    # 1) DISTINCT templates (sem LLM)
    if is_distinct_list_question(question):
        col = detect_target_column(question) or "zonas"
        sql = build_distinct_query(col, top_k)
        if not is_safe_select(sql):
            raise ValueError("Planner gerou SQL inseguro (não deveria acontecer).")
        return SqlPlan(sql=sql, used_template=True, reason=f"distinct_template:{col}")

    # 2) COUNT templates (sem LLM)
    if is_count_question(question):
        sql = build_count_query()
        if not is_safe_select(sql):
            raise ValueError("Planner gerou SQL inseguro (não deveria acontecer).")
        return SqlPlan(sql=sql, used_template=True, reason="count_template")

    # 3) Caso geral: usa SQL do LLM
    sql = extract_sql(raw_sql_from_llm or "")
    sql = ensure_limit(sql, top_k)

    if not is_safe_select(sql):
        raise ValueError("O modelo gerou um SQL potencialmente inseguro.")

    return SqlPlan(sql=sql, used_template=False, reason="llm_sql_with_policy")
