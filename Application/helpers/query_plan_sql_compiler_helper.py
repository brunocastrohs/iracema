from Application.dto.iracema_query_plan_dto import QueryPlanArgsDto
from Application.helpers.sql_types_helper import SqlPlan
from Application.helpers.query_plan_validator_helper import _normalize_group_by, _normalize_str_list


def _quote_ident(name: str) -> str:
    return name


def _compile_filters(plan: QueryPlanArgsDto) -> str:
    """
    Compila filtros simples (já whitelisted no validator).
    OBS: IN recebe lista, LIKE/ILIKE recebe string.
    """
    if not plan.filters:
        return ""

    parts = []
    for f in plan.filters:
        col = _quote_ident(f.column)
        op = f.operator.upper()

        if op == "IN":
            if not isinstance(f.value, list):
                raise ValueError("Filtro IN exige value como lista.")
            vals = []
            for v in f.value:
                if v is None:
                    continue
                if isinstance(v, (int, float)):
                    vals.append(str(v))
                else:
                    vals.append("'" + str(v).replace("'", "''") + "'")
            parts.append(f"{col} IN ({', '.join(vals)})")
        else:
            if f.value is None:
                # se quiser suportar "IS NULL", crie operador no DTO; por ora, bloqueia
                raise ValueError("Filtro inválido: value None não suportado para este operador.")
            if isinstance(f.value, (int, float)):
                val = str(f.value)
            else:
                val = "'" + str(f.value).replace("'", "''") + "'"
            parts.append(f"{col} {op} {val}")

    return "WHERE " + " AND ".join(parts)


def compile_query_plan_to_sql(table_fqn: str, plan: QueryPlanArgsDto, top_k: int) -> SqlPlan:
    intent = plan.intent
    limit = int(plan.limit) if plan.limit is not None else int(top_k)

    if intent == "schema":
        if "." not in table_fqn:
            raise ValueError("table_fqn inválido para schema")
        schema, table = table_fqn.split(".", 1)
        table_name = table.strip().strip('"')
        sql = (
            'SELECT column_name AS "coluna", data_type AS "tipo", is_nullable AS "nula"\n'
            "FROM information_schema.columns\n"
            f"WHERE table_schema = '{schema}'\n"
            f"  AND table_name = '{table_name}'\n"
            "ORDER BY ordinal_position;"
        )
        return SqlPlan(sql=sql, used_template=True, reason="fc:schema")

    if intent == "count":
        where_sql = _compile_filters(plan)
        sql = f'SELECT COUNT(*)::bigint AS "Total"\nFROM {table_fqn}\n{where_sql};'
        return SqlPlan(sql=sql, used_template=True, reason="fc:count")

    if intent == "distinct":
        cols_raw = _normalize_str_list(plan.select_columns)  # ✅ multi-coluna
        if cols_raw:
            cols = ", ".join(_quote_ident(c) for c in cols_raw)
            where_sql = _compile_filters(plan)
            order_sql = ""
            if plan.order_by:
                order_sql = f"\nORDER BY {_quote_ident(plan.order_by)} {plan.order_dir.upper()}"
            sql = (
                f"SELECT DISTINCT {cols}\n"
                f"FROM {table_fqn}\n"
                f"{where_sql}"
                f"{order_sql}\n"
                f"LIMIT {limit};"
            )
            return SqlPlan(sql=sql, used_template=True, reason=f"fc:distinct:{cols}")

        # compat legado (1 coluna)
        if not plan.target_column:
            raise ValueError("QueryPlan distinct exige select_columns ou target_column.")
        col = _quote_ident(plan.target_column)
        where_sql = _compile_filters(plan)
        if not where_sql:
            where_sql = f"WHERE {col} IS NOT NULL"
        else:
            where_sql = where_sql + f" AND {col} IS NOT NULL"

        sql = (
            f'SELECT DISTINCT {col} AS "Valor"\n'
            f"FROM {table_fqn}\n"
            f"{where_sql}\n"
            f"ORDER BY {col}\n"
            f"LIMIT {limit};"
        )
        return SqlPlan(sql=sql, used_template=True, reason=f"fc:distinct:{col}")

    if intent == "sum":
        if not plan.value_column:
            raise ValueError("QueryPlan sum exige value_column.")
        col = _quote_ident(plan.value_column)
        where_sql = _compile_filters(plan)
        if not where_sql:
            where_sql = f"WHERE {col} IS NOT NULL"
        else:
            where_sql = where_sql + f" AND {col} IS NOT NULL"

        sql = (
            f'SELECT SUM({col})::double precision AS "Total"\n'
            f"FROM {table_fqn}\n"
            f"{where_sql};"
        )
        return SqlPlan(sql=sql, used_template=True, reason=f"fc:sum:{col}")

    if intent == "grouped_sum":
        group_cols_raw = _normalize_group_by(plan.group_by)
        if not group_cols_raw or not plan.value_column:
            raise ValueError("QueryPlan grouped_sum exige group_by e value_column.")

        group_cols = [_quote_ident(c) for c in group_cols_raw]
        g_select = ", ".join(group_cols)
        g_groupby = ", ".join(group_cols)
        v = _quote_ident(plan.value_column)

        not_null_groups = " AND ".join(f"{c} IS NOT NULL" for c in group_cols)

        where_sql = _compile_filters(plan)
        base_nn = f"{v} IS NOT NULL AND {not_null_groups}"
        if not where_sql:
            where_sql = "WHERE " + base_nn
        else:
            where_sql = where_sql + " AND " + base_nn

        sql = (
            f'SELECT {g_select}, SUM({v})::double precision AS "Total"\n'
            f"FROM {table_fqn}\n"
            f"{where_sql}\n"
            f"GROUP BY {g_groupby}\n"
            f'ORDER BY "Total" DESC\n'
            f"LIMIT {limit};"
        )
        return SqlPlan(
            sql=sql,
            used_template=True,
            reason=f"fc:grouped_sum:{'|'.join(group_cols)}:{v}",
        )

    if intent == "detail":
        cols_raw = _normalize_str_list(plan.select_columns)
        cols = ", ".join(_quote_ident(c) for c in cols_raw) if cols_raw else "*"

        where_sql = _compile_filters(plan)

        order_sql = ""
        if plan.order_by:
            order_sql = f"\nORDER BY {_quote_ident(plan.order_by)} {plan.order_dir.upper()}"

        sql = (
            f"SELECT {cols}\n"
            f"FROM {table_fqn}\n"
            f"{where_sql}"
            f"{order_sql}\n"
            f"LIMIT {limit};"
        )
        return SqlPlan(sql=sql, used_template=True, reason="fc:detail")

    raise ValueError(f"intent desconhecido: {intent}")
