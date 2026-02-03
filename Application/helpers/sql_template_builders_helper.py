# Application/helpers/sql/sql_template_builders.py

def build_grouped_sum_query(table_fqn: str, group_col: str, value_col: str, top_k: int) -> str:
    return (
        f'SELECT {group_col} AS "Grupo", SUM({value_col})::double precision AS "Total"\n'
        f"FROM {table_fqn}\n"
        f"WHERE {group_col} IS NOT NULL AND {value_col} IS NOT NULL\n"
        f"GROUP BY {group_col}\n"
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
        f"ORDER BY {column}\n"
        f"LIMIT {int(top_k)};"
    )

def build_count_query(table_fqn: str) -> str:
    return (
        'SELECT COUNT(*)::bigint AS "Total"\n'
        f"FROM {table_fqn};"
    )

def build_columns_query(table_fqn: str) -> str:
    """
    Lista colunas via information_schema.
    table_fqn no formato: schema."table"
    """
    if "." not in table_fqn:
        raise ValueError("table_fqn inválido para build_columns_query")

    schema, table = table_fqn.split(".", 1)
    table_name = table.strip().strip('"')

    return (
        'SELECT column_name AS "coluna", data_type AS "tipo", is_nullable AS "nula"\n'
        "FROM information_schema.columns\n"
        f"WHERE table_schema = '{schema}'\n"
        f"  AND table_name = '{table_name}'\n"
        "ORDER BY ordinal_position;"
    )
