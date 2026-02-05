# Application/dto/iracema_query_plan_dto.py
from typing import Any, List, Literal, Optional
from pydantic import BaseModel, Field

IntentType = Literal["schema", "count", "distinct", "sum", "grouped_sum", "detail"]


class QueryFilterDto(BaseModel):
    column: str
    operator: Literal["=", "!=", ">", ">=", "<", "<=", "IN", "LIKE", "ILIKE"]
    value: Any


class QueryAggregationDto(BaseModel):
    op: Literal["sum", "count"]
    column: str
    alias: Optional[str] = None


class QueryPlanArgsDto(BaseModel):
    intent: IntentType

    # compat legado (ainda aceito)
    # distinct/sum/grouped_sum/detail
    target_column: Optional[str] = None

    # sum/grouped_sum
    value_column: Optional[str] = None

    # grouped_sum: pode ter 1+ colunas
    group_by: Optional[List[str]] = None

    # ✅ NOVO: para suportar SELECT com múltiplas colunas (detail/distinct e casos gerais)
    select_columns: Optional[List[str]] = None

    # filtros opcionais
    filters: List[QueryFilterDto] = Field(default_factory=list)

    # ordenação
    order_by: Optional[str] = None
    order_dir: Literal["asc", "desc"] = "asc"

    # paginação/limite
    limit: Optional[int] = None
