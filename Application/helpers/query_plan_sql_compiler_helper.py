from Application.dto.iracema_query_plan_dto import QueryPlanArgsDto
from Application.helpers.sql_types_helper import SqlPlan
from Application.helpers.query_plan_validator_helper import _normalize_group_by

def _quote_ident(name: str) -> str:
    # simples: assume nome seguro vindo do whitelist
    return name

def compile_query_plan_to_sql(table_fqn: str, plan: QueryPlanArgsDto, top_k: int) -> SqlPlan:
    intent = plan.intent

    # decide limite final
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
        sql = f'SELECT COUNT(*)::bigint AS "Total"\nFROM {table_fqn};'
        return SqlPlan(sql=sql, used_template=True, reason="fc:count")

    if intent == "distinct":
        if not plan.target_column:
            raise ValueError("QueryPlan distinct exige target_column.")
        col = _quote_ident(plan.target_column)
        sql = (
            f'SELECT DISTINCT {col} AS "Valor"\n'
            f"FROM {table_fqn}\n"
            f"WHERE {col} IS NOT NULL\n"
            f"ORDER BY {col}\n"
            f"LIMIT {limit};"
        )
        return SqlPlan(sql=sql, used_template=True, reason=f"fc:distinct:{col}")

    if intent == "sum":
        if not plan.value_column:
            raise ValueError("QueryPlan sum exige value_column.")
        col = _quote_ident(plan.value_column)
        sql = (
            f'SELECT SUM({col})::double precision AS "Total"\n'
            f"FROM {table_fqn};"
        )
        return SqlPlan(sql=sql, used_template=True, reason=f"fc:sum:{col}")

    if intent == "grouped_sum":
        print(plan)
        group_cols_raw = _normalize_group_by(plan.group_by)
        if not group_cols_raw or not plan.value_column:
            raise ValueError("QueryPlan grouped_sum exige group_by e value_column.")

        group_cols = [_quote_ident(c) for c in group_cols_raw]
        g_select = ", ".join(group_cols)
        g_groupby = ", ".join(group_cols)

        v = _quote_ident(plan.value_column)

        # opcional: remove linhas com grupo nulo (qualquer um nulo)
        not_null_groups = " AND ".join(f"{c} IS NOT NULL" for c in group_cols)

        sql = (
            f'SELECT {g_select}, SUM({v})::double precision AS "Total"\n'
            f"FROM {table_fqn}\n"
            f"WHERE {v} IS NOT NULL AND {not_null_groups}\n"
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
        sql = f"SELECT *\nFROM {table_fqn}\nLIMIT {limit};"
        return SqlPlan(sql=sql, used_template=True, reason="fc:detail")

    raise ValueError(f"intent desconhecido: {intent}")
