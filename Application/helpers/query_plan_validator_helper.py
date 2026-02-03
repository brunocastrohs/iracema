from typing import Set,Iterable,Optional
from Application.dto.iracema_query_plan_dto import QueryPlanArgsDto

from typing import Any

from Application.dto.iracema_query_plan_dto import QueryPlanArgsDto


def _allowed_columns(columns_meta: list[dict]) -> set[str]:
    allowed = set()
    for c in columns_meta or []:
        name = c.get("name")
        if not name:
            continue
        if c.get("is_geometry"):
            continue
        allowed.add(name)
    return allowed


def _normalize_group_by(group_by: Any) -> list[str]:
    if group_by is None:
        return []
    if isinstance(group_by, str):
        s = group_by.strip()
        return [s] if s else []
    if isinstance(group_by, list):
        out: list[str] = []
        for x in group_by:
            if x is None:
                continue
            s = str(x).strip()
            if s:
                out.append(s)
        return out
    s = str(group_by).strip()
    return [s] if s else []


def validate_and_normalize_plan(plan: QueryPlanArgsDto, columns_meta: list[dict]) -> QueryPlanArgsDto:
    allowed = _allowed_columns(columns_meta)

    def ensure_col(name: str | None, field: str):
        if name is None:
            return
        if name not in allowed:
            raise ValueError(f"QueryPlan inválido: coluna '{name}' não existe/é proibida ({field}).")

    # ------------------------------------------------------------------
    # 1) NORMALIZAÇÃO (antes de validar)
    # ------------------------------------------------------------------

    # normaliza group_by para lista sempre
    group_list = _normalize_group_by(plan.group_by)
    plan.group_by = group_list or None

    # repair para intents agregadas
    # (muitos modelos usam target_column como “coluna principal” e esquecem value_column)
    if plan.intent in ("sum", "grouped_sum"):
        if plan.value_column is None and plan.target_column:
            plan.value_column = plan.target_column
            # opcional: limpar target_column pra evitar ambiguidade
            plan.target_column = None

    # ------------------------------------------------------------------
    # 2) VALIDAÇÃO DE COLUNAS
    # ------------------------------------------------------------------
    ensure_col(plan.target_column, "target_column")
    ensure_col(plan.value_column, "value_column")

    for g in (plan.group_by or []):
        ensure_col(g, "group_by")

    for f in plan.filters or []:
        if f.column not in allowed:
            raise ValueError(f"QueryPlan inválido: filtro usa coluna proibida '{f.column}'.")

    # ------------------------------------------------------------------
    # 3) Defaults seguros
    # ------------------------------------------------------------------
    # se limit vier None, executor decide
    if plan.limit is not None:
        plan.limit = int(plan.limit)

    # order_dir só faz sentido se tiver order_by
    if plan.order_by is None:
        plan.order_dir = "asc"

    return plan
