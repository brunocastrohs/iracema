# Application/dto/iracema_fca_dto.py
from typing import Any, List, Literal, Optional
from pydantic import BaseModel, Field

WhereOp = Literal["=", "!=", ">", ">=", "<", "<=", "IN", "LIKE", "ILIKE"]

class FCASelectItemDto(BaseModel):
    type: Literal["column", "agg"] = "column"
    name: Optional[str] = None          # usado quando type=column
    agg: Optional[Literal["sum", "count", "avg", "min", "max"]] = None  # quando type=agg
    column: Optional[str] = None        # quando type=agg
    alias: Optional[str] = None

class FCAWhereDto(BaseModel):
    column: str
    op: WhereOp
    value: Any

class FCAAggDto(BaseModel):
    op: Literal["sum", "count", "avg", "min", "max"]
    column: str
    alias: Optional[str] = None

class FCAOrderByDto(BaseModel):
    expr: str  # coluna OU alias de agregação
    dir: Literal["asc", "desc"] = "asc"

class FCAArgsDto(BaseModel):
    # table_fqn pode vir, mas você deve sobrescrever/validar usando o request.table_identifier
    table_fqn: Optional[str] = None

    select: List[FCASelectItemDto] = Field(default_factory=list)
    where: List[FCAWhereDto] = Field(default_factory=list)

    aggregations: List[FCAAggDto] = Field(default_factory=list)
    group_by: List[str] = Field(default_factory=list)

    order_by: List[FCAOrderByDto] = Field(default_factory=list)

    limit: Optional[int] = None
    offset: Optional[int] = None
