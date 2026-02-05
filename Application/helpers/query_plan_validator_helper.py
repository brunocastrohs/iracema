# Application/helpers/query_plan_validator_helper.py
from typing import Any
from Application.dto.iracema_query_plan_dto import QueryPlanArgsDto


def _allowed_columns(columns_meta: list[dict]) -> set[str]:
    allowed: set[str] = set()
    for c in columns_meta or []:
        name = c.get("name")
        if not name:
            continue
        if c.get("is_geometry"):
            continue
        allowed.add(name)
    return allowed


def _normalize_str_list(v: Any) -> list[str]:
    """
    Normaliza:
      - None -> []
      - "col" -> ["col"]
      - ["a","b"] -> ["a","b"]
      - outros -> [str(outro)]
    """
    if v is None:
        return []
    if isinstance(v, str):
        s = v.strip()
        return [s] if s else []
    if isinstance(v, list):
        out: list[str] = []
        for x in v:
            if x is None:
                continue
            s = str(x).strip()
            if s:
                out.append(s)
        return out
    s = str(v).strip()
    return [s] if s else []


def _normalize_group_by(group_by: Any) -> list[str]:
    # mantido (compat), mas agora reusa a lógica genérica
    return _normalize_str_list(group_by)


def validate_and_normalize_plan(plan: QueryPlanArgsDto, columns_meta: list[dict]) -> QueryPlanArgsDto:
    """
    - Normaliza listas (group_by/select_columns)
    - Faz repairs comuns vindos de LLM/FC
    - Valida colunas contra whitelist (columns_meta)
    """
    allowed = _allowed_columns(columns_meta)

    def ensure_col(name: str | None, field: str):
        if name is None:
            return
        if name not in allowed:
            raise ValueError(
                f"QueryPlan inválido: coluna '{name}' não existe/é proibida ({field})."
            )

    # ------------------------------------------------------------------
    # 1) NORMALIZAÇÃO (antes de validar)
    # ------------------------------------------------------------------

    # group_by sempre lista
    group_list = _normalize_group_by(plan.group_by)
    plan.group_by = group_list or None

    # ✅ select_columns sempre lista
    select_list = _normalize_str_list(plan.select_columns)
    plan.select_columns = select_list or None

    # repair para intents agregadas:
    # muitos modelos preenchem target_column como "coluna a somar"
    if plan.intent in ("sum", "grouped_sum"):
        if plan.value_column is None and plan.target_column:
            plan.value_column = plan.target_column
            plan.target_column = None

    # repair: distinct/detail com target_column -> select_columns
    if plan.intent in ("distinct", "detail"):
        if not plan.select_columns and plan.target_column:
            plan.select_columns = [plan.target_column]
            # manter target_column não é necessário; limpa para evitar ambiguidade
            plan.target_column = None

    # ------------------------------------------------------------------
    # 2) VALIDAÇÃO DE COLUNAS
    # ------------------------------------------------------------------
    ensure_col(plan.target_column, "target_column")
    ensure_col(plan.value_column, "value_column")

    for g in (plan.group_by or []):
        ensure_col(g, "group_by")

    for c in (plan.select_columns or []):
        ensure_col(c, "select_columns")

    for f in plan.filters or []:
        if f.column not in allowed:
            raise ValueError(f"QueryPlan inválido: filtro usa coluna proibida '{f.column}'.")

    # ------------------------------------------------------------------
    # 3) Defaults seguros
    # ------------------------------------------------------------------
    if plan.limit is not None:
        plan.limit = int(plan.limit)

    if plan.order_by is None:
        plan.order_dir = "asc"
    else:
        ensure_col(plan.order_by, "order_by")

    return plan
