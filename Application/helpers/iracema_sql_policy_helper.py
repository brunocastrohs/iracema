import re
from dataclasses import dataclass
from typing import Optional

_SCHEMA_INTENT = re.compile(
    r"\b(colunas?|campos?|atributos?|esquema|schema|estrutura)\b",
    re.IGNORECASE,
)

_GROUPBY_INTENT = re.compile(
    r"\b(de\s+cada|por\s+cada|por\b|agrupad[oa]\s+por|separad[oa]\s+por)\b",
    re.IGNORECASE,
)


_DISTINCT_INTENT = re.compile(
    r"\b(quais|quais\s+s[aã]o|listar|lista|existem|existentes|valores|op[cç][oõ]es|categorias|tipos|nomes|diferentes|distint[oa]s|distinct)\b",
    re.IGNORECASE,
)

_COUNT_INTENT = re.compile(
    r"\b(quantos|quantas|conta|contagem|n[uú]mero\s+de\s+registros|n[uú]mero\s+de\s+linhas|registros)\b",
    re.IGNORECASE,
)

_SUM_INTENT = re.compile(
    r"\b(soma|somat[oó]rio|somar|total)\b",
    re.IGNORECASE,
)

_AREA_HINT = re.compile(r"\b([aá]rea)\b", re.IGNORECASE)
_PERIM_HINT = re.compile(r"\b(per[ií]metro)\b", re.IGNORECASE)


_DETAIL_INTENT = re.compile(
    r"\b(detalhe|detalhes|mostrar|exibir|trazer|todas?\s+as?\s+linhas|tudo)\b",
    re.IGNORECASE,
)

#_COL_HINTS = [
#    ("sub_zonas", re.compile(r"\b(sub\s*zonas?|sub[-_\s]?zonas?)\b", re.IGNORECASE)),
#    ("letra_subz", re.compile(r"\b(letra|sigla)\b", re.IGNORECASE)),
#    ("zonas", re.compile(r"\b(zonas?|zona)\b", re.IGNORECASE)),
#]

_CODE_FENCE_SQL = re.compile(r"```(?:sql)?\s*(.*?)\s*```", re.IGNORECASE | re.DOTALL)
SQL_SELECT_PATTERN = re.compile(r"^\s*select\s", re.IGNORECASE)
SQL_WITH_PATTERN = re.compile(r"^\s*with\s", re.IGNORECASE)
_LIMIT_PATTERN = re.compile(r"\blimit\s+\d+\b", re.IGNORECASE)


@dataclass
class SqlPlan:
    sql: str
    used_template: bool
    reason: str

def wants_groupby(question: str) -> bool:
    return bool(_GROUPBY_INTENT.search(question or ""))

def extract_queryable_columns(columns_meta: list[dict]) -> list[str]:
    """
    Retorna apenas colunas não-geométricas, seguras para SELECT/DISTINCT.
    """
    cols = []
    for c in columns_meta or []:
        if not c.get("is_geometry"):
            name = c.get("name")
            if name:
                cols.append(name)
    return cols


def extract_sql(raw: str) -> str:
    if not raw:
        return ""
    s = raw.strip()
    m = _CODE_FENCE_SQL.search(s)
    if m:
        s = m.group(1).strip()
    return s.strip("`").strip()


def is_safe_select(sql: str) -> bool:
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
    s = sql.strip().rstrip(";")
    if has_limit(s):
        return s + ";"
    return f"{s}\nLIMIT {int(top_k)};"


def _normalize_text(s: str) -> str:
    # Mantém letras/números/_ e troca o resto por espaço
    return re.sub(r"[^a-z0-9_]+", " ", (s or "").lower()).strip()

def _token_boundary_pattern(col_name: str) -> re.Pattern:
    # Garante que "pan" não case dentro de "nomepan"
    # Ex: (?<![a-z0-9_])pan(?![a-z0-9_])
    escaped = re.escape(col_name.lower())
    return re.compile(rf"(?<![a-z0-9_]){escaped}(?![a-z0-9_])", re.IGNORECASE)

def detect_groupby_column(question: str, columns_meta: list[dict]) -> Optional[str]:
    q_norm = _normalize_text(question)

    cols = [
        c.get("name")
        for c in (columns_meta or [])
        if c.get("name") and not c.get("is_geometry")
    ]

    # 🔑 Prioriza colunas maiores primeiro (nomepan antes de pan)
    cols_sorted = sorted(cols, key=lambda x: len(x), reverse=True)

    for col in cols_sorted:
        pat = _token_boundary_pattern(col)
        if pat.search(q_norm):
            return col

    return None


def detect_target_column(question: str, columns_meta: list[dict]) -> Optional[str]:
    q = (question or "").lower()

    for col in columns_meta or []:
        name = col.get("name")
        if not name:
            continue
        if col.get("is_geometry"):
            continue

        if name.lower() in q:
            return name

    return None

def detect_sum_column(question: str, columns_meta: list[dict]) -> Optional[str]:
    q = (question or "").lower()
    cols = {c.get("name"): c for c in (columns_meta or []) if c.get("name")}

    # regra: se menciona "área", prefira colunas com "area"
    if _AREA_HINT.search(q):
        for name in cols:
            if name and "area" in name.lower():
                return name

    # regra: se menciona "perímetro", prefira colunas com "perimet"
    if _PERIM_HINT.search(q):
        for name in cols:
            if name and ("perimet" in name.lower() or "perimetro" in name.lower()):
                return name

    return None


def is_schema_question(question: str) -> bool:
    q = question or ""
    return bool(_SCHEMA_INTENT.search(q))

def is_distinct_list_question(question: str) -> bool:
    q = question or ""
    if _DETAIL_INTENT.search(q):
        return False
    if _SCHEMA_INTENT.search(q):
        return False
    return bool(_DISTINCT_INTENT.search(q)) and not bool(_COUNT_INTENT.search(q))


def is_count_question(question: str) -> bool:
    q = question or ""
    return bool(_COUNT_INTENT.search(q))

def build_grouped_sum_query(table_fqn: str, group_col: str, value_col: str, top_k: int) -> str:
    return (
        f'SELECT {group_col} AS "Grupo", SUM({value_col})::double precision AS "Total"\n'
        f"FROM {table_fqn}\n"
        f"WHERE {group_col} IS NOT NULL AND {value_col} IS NOT NULL\n"
        f'GROUP BY {group_col}\n'
        f'ORDER BY "Total" DESC\n'
        f"LIMIT {int(top_k)};"
    )

def build_sum_query(table_fqn: str, column: str) -> str:
    return (
        f'SELECT SUM({column})::double precision AS "Total"\n'
        f"FROM {table_fqn};"
    )

def build_distinct_query(table_fqn: str, column: str, top_k: int) -> str:
    return (
        f'SELECT DISTINCT {column} AS "Valor"\n'
        f"FROM {table_fqn}\n"
        f"WHERE {column} IS NOT NULL\n"
        f'ORDER BY {column}\n'
        f"LIMIT {int(top_k)};"
    )


def build_count_query(table_fqn: str) -> str:
    return (
        'SELECT COUNT(*)::bigint AS "Total"\n'
        f"FROM {table_fqn};"
    )

def build_columns_query(table_fqn: str) -> str:
    """
    Lista colunas da tabela alvo via information_schema.
    table_fqn esperado no formato: schema."table"
    """
    # extrai schema e table a partir de algo como public."minha_tabela"
    if "." not in table_fqn:
        raise ValueError("table_fqn inválido para build_columns_query")

    schema, table = table_fqn.split(".", 1)
    # remove aspas da tabela se vier quoted
    table_name = table.strip().strip('"')

    return (
        'SELECT column_name AS "coluna", data_type AS "tipo", is_nullable AS "nula"\n'
        "FROM information_schema.columns\n"
        f"WHERE table_schema = '{schema}'\n"
        f"  AND table_name = '{table_name}'\n"
        'ORDER BY ordinal_position;'
    )

def plan_sql_template(
    table_fqn: str,
    columns_meta: list[dict],
    question: str,
    top_k: int,
) -> Optional[SqlPlan]:
    """
    Retorna um SqlPlan template quando possível.
    Retorna None quando deve delegar ao LLM.
    """
    print(columns_meta)

    if is_schema_question(question):
        sql = build_columns_query(table_fqn)
        return SqlPlan(sql=sql, used_template=True, reason="schema_columns_template")

    # DISTINCT apenas se coluna explícita
    if is_distinct_list_question(question):
        col = detect_target_column(question, columns_meta)
        if col:
            sql = build_distinct_query(table_fqn, col, top_k)
            return SqlPlan(sql=sql, used_template=True, reason=f"distinct_template:{col}")

    # SUM / grouped sum
    if _SUM_INTENT.search(question or ""):
        sum_col = detect_sum_column(question, columns_meta)
        if sum_col:
            if wants_groupby(question):
                group_col = detect_groupby_column(question, columns_meta)
                if group_col:
                    sql = build_grouped_sum_query(table_fqn, group_col, sum_col, top_k)
                    if not is_safe_select(sql):
                        raise ValueError("Planner gerou SQL inseguro (grouped sum).")
                    return SqlPlan(sql=sql, used_template=True, reason=f"grouped_sum_template:{group_col}:{sum_col}")

            sql = build_sum_query(table_fqn, sum_col)
            if not is_safe_select(sql):
                raise ValueError("Planner gerou SQL inseguro (sum).")
            return SqlPlan(sql=sql, used_template=True, reason=f"sum_template:{sum_col}")

    if is_count_question(question):
        sql = build_count_query(table_fqn)
        return SqlPlan(sql=sql, used_template=True, reason="count_template")

    return None

def sanitize_llm_sql(table_fqn: str, raw_sql_from_llm: Optional[str], top_k: int) -> SqlPlan:
    """
    Normaliza e valida SQL vindo do LLM.
    Policy de segurança + garante schema quando table_fqn = schema.tabela.
    """
    sql = extract_sql(raw_sql_from_llm or "")
    #sql = ensure_limit(sql, top_k)

    if not is_safe_select(sql):
        raise ValueError("O modelo gerou um SQL potencialmente inseguro.")

    # Se table_fqn tem schema (algo como "zcm"."tabela" ou zcm."tabela" ou zcm.tabela)
    tokens = sql.split()

    # encontra FROM
    try:
        from_idx = next(i for i, t in enumerate(tokens) if t.lower() == "from")
    except StopIteration:
        raise ValueError("SQL do modelo não contém cláusula FROM.")

    if from_idx + 1 >= len(tokens):
        raise ValueError("SQL do modelo contém FROM inválido.")

    # preserva possível pontuação (; ,)
    table_token = tokens[from_idx + 1]
    suffix = ""
    while table_token and table_token[-1] in ";,":
        suffix = table_token[-1] + suffix
        table_token = table_token[:-1]

    # FORÇA a tabela correta (descarta a do LLM)
    tokens[from_idx + 1] = table_fqn + suffix
    sql = " ".join(tokens)

    return SqlPlan(sql=sql, used_template=False, reason="llm_sql_table_forced")
