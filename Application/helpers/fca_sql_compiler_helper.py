# Application/helpers/fca_sql_compiler_helper.py

from __future__ import annotations

from typing import Any, List, Optional

from Application.dto.iracema_fca_dto import FCAArgsDto, FCASelectItemDto, FCAWhereDto
from Application.helpers.sql_types_helper import SqlPlan


# -----------------------------------------------------------------------------
# Quoting (determinístico)
# -----------------------------------------------------------------------------

def _quote_ident(name: str) -> str:
    """
    Quote seguro para identificadores.
    Como a validação já faz whitelist, aqui só escapamos aspas duplas por garantia.
    """
    s = str(name).replace('"', '""')
    return f'"{s}"'


def _quote_alias(alias: str) -> str:
    # alias também vai quoted
    s = str(alias).replace('"', '""')
    return f'"{s}"'


def _sql_literal(v: Any) -> str:
    """
    Literal SQL básico (sem parâmetros). Como você já controla a whitelist de colunas
    e os operadores, isso fica bem mais seguro.
    Idealmente, você pode migrar depois para SQL parametrizado (text + params).
    """
    if v is None:
        return "NULL"
    if isinstance(v, bool):
        return "TRUE" if v else "FALSE"
    if isinstance(v, (int, float)):
        return str(v)
    # string / outros -> string
    s = str(v)
    s = s.replace("'", "''")
    return f"'{s}'"


# -----------------------------------------------------------------------------
# WHERE builder
# -----------------------------------------------------------------------------

def _compile_where_clause(where: List[FCAWhereDto]) -> str:
    if not where:
        return ""

    parts: list[str] = []
    for w in where:
        col = _quote_ident(w.column)
        op = str(w.op).upper()
        val = w.value

        # Null-safe para '=' / '!='
        if val is None and op in ("=", "!="):
            parts.append(f"{col} IS {'NOT ' if op == '!=' else ''}NULL")
            continue
        if val is None:
            raise ValueError(f"WHERE inválido: operador {op} não aceita NULL (use '='/'!=').")

        if op == "IN":
            if not isinstance(val, (list, tuple)) or len(val) == 0:
                raise ValueError("WHERE inválido: IN exige lista não-vazia.")
            lit_list = ", ".join(_sql_literal(x) for x in val)
            parts.append(f"{col} IN ({lit_list})")
        elif op in ("LIKE", "ILIKE"):
            if not isinstance(val, str):
                raise ValueError(f"WHERE inválido: {op} exige string.")
            parts.append(f"{col} {op} {_sql_literal(val)}")
        else:
            parts.append(f"{col} {op} {_sql_literal(val)}")

    return "WHERE " + " AND ".join(parts)


# -----------------------------------------------------------------------------
# SELECT builder
# -----------------------------------------------------------------------------

def _compile_select_item(it: FCASelectItemDto) -> str:
    t = (it.type or "column").lower()

    if t == "column":
        col = _quote_ident(it.name)
        alias = _quote_alias(it.alias or it.name)
        # se alias == name, ainda é ok manter "AS"
        return f"{col} AS {alias}"

    if t == "agg":
        op = (it.agg or "").lower()
        alias = _quote_alias(it.alias or f"{op}_{it.column or 'all'}")

        if op == "count":
            if it.column:
                col = _quote_ident(it.column)
                return f"COUNT({col})::bigint AS {alias}"
            return f"COUNT(*)::bigint AS {alias}"

        col = _quote_ident(it.column)
        if op == "sum":
            return f"SUM({col})::double precision AS {alias}"
        if op == "avg":
            return f"AVG({col})::double precision AS {alias}"
        if op == "min":
            return f"MIN({col}) AS {alias}"
        if op == "max":
            return f"MAX({col}) AS {alias}"

        raise ValueError(f"Select agg op desconhecido: {op}")

    raise ValueError(f"Select item type desconhecido: {it.type}")


def _compile_group_by(group_by: list[str]) -> str:
    if not group_by:
        return ""
    cols = ", ".join(_quote_ident(c) for c in group_by)
    return "GROUP BY " + cols


def _compile_order_by(fca: FCAArgsDto) -> str:
    if not (fca.order_by or []):
        return ""

    # order_by.expr pode ser:
    # - coluna real -> quote_ident
    # - alias -> quote_alias
    # Como o validator garante que expr ou é coluna permitida ou alias conhecido,
    # aqui escolhemos: se expr bate em alguma coluna selecionada “name”, quote_ident,
    # senão quote_alias.
    selected_cols = {it.name for it in (fca.select or []) if (it.type or "column").lower() == "column" and it.name}
    parts: list[str] = []
    for ob in fca.order_by:
        expr = ob.expr
        dir_ = (ob.dir or "asc").lower()
        if expr in selected_cols or expr in (fca.group_by or []):
            parts.append(f"{_quote_ident(expr)} {dir_.upper()}")
        else:
            parts.append(f"{_quote_alias(expr)} {dir_.upper()}")
    return "ORDER BY " + ", ".join(parts)


def _compile_limit_offset(limit: Optional[int], offset: Optional[int]) -> str:
    s = f"LIMIT {int(limit)}"
    if offset is not None:
        s += f" OFFSET {int(offset)}"
    return s


# -----------------------------------------------------------------------------
# Compiler principal
# -----------------------------------------------------------------------------

def compile_fca_to_sql(fca: FCAArgsDto) -> SqlPlan:
    """
    Compila FCAArgsDto (já validado/normalizado) para SQL determinístico.
    """
    table_fqn = str(fca.table_fqn)

    # SELECT:
    if not (fca.select or []):
        select_sql = "SELECT *"
    else:
        select_parts = [_compile_select_item(it) for it in fca.select]
        select_sql = "SELECT " + ", ".join(select_parts)

    from_sql = f"FROM {table_fqn}"

    where_sql = _compile_where_clause(fca.where or [])
    group_by_sql = _compile_group_by(fca.group_by or [])
    order_by_sql = _compile_order_by(fca)
    limit_sql = _compile_limit_offset(fca.limit, fca.offset)

    sql_lines = [select_sql, from_sql]
    if where_sql:
        sql_lines.append(where_sql)
    if group_by_sql:
        sql_lines.append(group_by_sql)
    if order_by_sql:
        sql_lines.append(order_by_sql)
    sql_lines.append(limit_sql + ";")

    sql = "\n".join(sql_lines)

    return SqlPlan(
        sql=sql,
        used_template=True,
        reason="fc_args:v2",
    )
