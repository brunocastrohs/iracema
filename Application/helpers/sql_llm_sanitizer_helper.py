# Application/helpers/sql/sql_llm_sanitizer.py

from dataclasses import dataclass
from typing import Optional

from Application.helpers.sql_types_helper import SqlPlan
from Application.helpers.sql_extractor_helper import extract_sql
from Application.helpers.sql_llm_normalizer_helper import normalize_sql_whitespace
from Application.helpers.sql_security_helper import is_safe_select


def sanitize_llm_sql(table_fqn: str, raw_sql_from_llm: Optional[str], top_k: int) -> SqlPlan:
    """
    1) extrai SQL
    2) normaliza whitespace (corrige FROMzcm...)
    3) valida segurança
    4) força table_fqn no FROM
    """
    sql = extract_sql(raw_sql_from_llm or "")
    sql = normalize_sql_whitespace(sql)

    if not is_safe_select(sql):
        raise ValueError("O modelo gerou um SQL potencialmente inseguro.")

    tokens = sql.split()

    try:
        from_idx = next(i for i, t in enumerate(tokens) if t.lower() == "from")
    except StopIteration:
        raise ValueError("SQL do modelo não contém cláusula FROM.")

    if from_idx + 1 >= len(tokens):
        raise ValueError("SQL do modelo contém FROM inválido.")

    table_token = tokens[from_idx + 1]
    suffix = ""
    while table_token and table_token[-1] in ";,":
        suffix = table_token[-1] + suffix
        table_token = table_token[:-1]

    tokens[from_idx + 1] = table_fqn + suffix
    sql = " ".join(tokens)

    return SqlPlan(sql=sql, used_template=False, reason="llm_sql_normalized_and_forced")
