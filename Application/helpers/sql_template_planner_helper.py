# Application/helpers/sql/sql_template_planner.py

from typing import Optional

from Application.helpers.sql_types_helper import SqlPlan
from Application.helpers.sql_intent_detector_helper import (
    is_schema_question,
    is_distinct_list_question,
    is_count_question,
    is_sum_question,
    wants_groupby,
)
from Application.helpers.sql_column_detector_helper import (
    detect_target_column,
    detect_sum_column,
    detect_groupby_column,
)
from Application.helpers.sql_template_builders_helper import (
    build_columns_query,
    build_distinct_query,
    build_count_query,
    build_sum_query,
    build_grouped_sum_query,
)
from Application.helpers.sql_security_helper import is_safe_select


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

    if is_schema_question(question):
        sql = build_columns_query(table_fqn)
        return SqlPlan(sql=sql, used_template=True, reason="schema_columns_template")

    if is_distinct_list_question(question):
        col = detect_target_column(question, columns_meta)
        if col:
            sql = build_distinct_query(table_fqn, col, top_k)
            return SqlPlan(sql=sql, used_template=True, reason=f"distinct_template:{col}")

    if is_sum_question(question):
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
