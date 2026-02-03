# Application/helpers/sql/sql_security.py

import re

SQL_SELECT_PATTERN = re.compile(r"^\s*select\s", re.IGNORECASE)
SQL_WITH_PATTERN   = re.compile(r"^\s*with\s", re.IGNORECASE)

# detecta múltiplos statements (sem contar ; final)
_MULTI_STMT = re.compile(r";\s*\S", re.DOTALL)

# Palavras perigosas (DDL/DML)
_FORBIDDEN = [
    "insert", "update", "delete", "drop", "alter", "truncate",
    "create", "grant", "revoke", "merge", "call", "execute",
]

def is_safe_select(sql: str) -> bool:
    """
    Policy de segurança para SQL vindo do LLM.
    Aceita apenas SELECT ou WITH ... SELECT
    Reprova:
      - multi-statement
      - qualquer token DDL/DML
    """
    if not sql:
        return False

    stripped = sql.strip()
    if not stripped:
        return False

    # multi-statement?
    # ex: "select ...; drop table x;"
    if _MULTI_STMT.search(stripped):
        return False

    # precisa começar com SELECT ou WITH
    if not (SQL_SELECT_PATTERN.match(stripped) or SQL_WITH_PATTERN.match(stripped)):
        return False

    # checa tokens proibidos (com fronteira de palavra)
    lower = stripped.lower()

    # evita falso positivo em nomes (ex.: coluna "updated_at")
    # por isso usamos regex de palavra
    for kw in _FORBIDDEN:
        if re.search(rf"\b{re.escape(kw)}\b", lower):
            return False

    return True
