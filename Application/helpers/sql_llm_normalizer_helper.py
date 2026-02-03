import re

# Palavras reservadas que exigem separação
_SQL_KEYWORDS = [
    "select", "from", "where", "group", "by", "order",
    "having", "limit", "join", "inner", "left", "right",
    "full", "on", "union", "with"
]

# cria regex tipo: (?i)(from)([a-z_"])
_KEYWORD_GLUE_PATTERNS = [
    re.compile(rf"(?i)\b({kw})([a-z_\"\.])") for kw in _SQL_KEYWORDS
]

def normalize_sql_whitespace(sql: str) -> str:
    """
    Insere espaços entre palavras-chave SQL e identificadores colados.
    Não tenta ser parser SQL, apenas corrige erros comuns de LLM.
    """
    if not sql:
        return sql

    s = sql.strip()

    for pat in _KEYWORD_GLUE_PATTERNS:
        s = pat.sub(r"\1 \2", s)

    # normaliza múltiplos espaços
    s = re.sub(r"\s+", " ", s)

    return s.strip()
