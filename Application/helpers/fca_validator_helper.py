# Application/helpers/fca_validator_helper.py

from __future__ import annotations

from typing import Any, Iterable, Optional, Set

from Application.dto.iracema_fca_dto import (
    FCAArgsDto,
    FCASelectItemDto,
    FCAAggDto,
    FCAWhereDto,
    FCAOrderByDto,
)


# -----------------------------------------------------------------------------
# Whitelist de colunas (não-geom)
# -----------------------------------------------------------------------------

def _allowed_columns(columns_meta: list[dict]) -> set[str]:
    allowed: set[str] = set()
    for c in columns_meta or []:
        name = (c.get("name") or "").strip()
        if not name:
            continue
        if c.get("is_geometry"):
            continue
        allowed.add(name)
    return allowed


def _allowed_agg_ops() -> set[str]:
    return {"sum", "count", "avg", "min", "max"}


def _allowed_where_ops() -> set[str]:
    return {"=", "!=", ">", ">=", "<", "<=", "IN", "LIKE", "ILIKE"}


def _as_int_or_none(v: Any) -> Optional[int]:
    if v is None:
        return None
    try:
        return int(v)
    except Exception:
        raise ValueError(f"FCA inválido: limit/offset deve ser inteiro. Recebido: {v!r}")


def _norm_str(v: Any) -> str:
    return str(v).strip()


def _ensure_col(allowed: Set[str], name: Optional[str], field: str) -> None:
    if name is None:
        return
    if name not in allowed:
        raise ValueError(f"FCA inválido: coluna '{name}' não existe/é proibida ({field}).")


def _ensure_cols(allowed: Set[str], names: Iterable[str], field: str) -> None:
    for n in names:
        if n not in allowed:
            raise ValueError(f"FCA inválido: coluna '{n}' não existe/é proibida ({field}).")


def _ensure_alias_safe(alias: str) -> None:
    # Alias é usado como identificador quoted no SQL. Não precisa regex pesada,
    # mas não aceitamos vazio.
    if not alias.strip():
        raise ValueError("FCA inválido: alias vazio não é permitido.")


# -----------------------------------------------------------------------------
# Normalização de SELECT
# -----------------------------------------------------------------------------

def _normalize_select(
    fca: FCAArgsDto,
    allowed: Set[str],
) -> list[FCASelectItemDto]:
    """
    Normaliza e valida fca.select.
    Regras:
    - Se select vazio:
        - se (group_by ou aggregations) -> select = group_by(cols) + aggregations(as agg select items)
        - senão: select vazio (compiler decide por SELECT *)
    - Se select preenchido:
        - type=column exige name em allowed
        - type=agg exige agg+column e column em allowed (exceto count(*) caso column None)
    """
    select_items: list[FCASelectItemDto] = []

    # Se não veio select, inferir a partir de group_by + aggregations (se existirem)
    if not (fca.select or []):
        inferred: list[FCASelectItemDto] = []
        for gb in (fca.group_by or []):
            _ensure_col(allowed, gb, "group_by(select_infer)")
            inferred.append(FCASelectItemDto(type="column", name=gb, alias=gb))

        for agg in (fca.aggregations or []):
            op = _norm_str(agg.op).lower()
            if op not in _allowed_agg_ops():
                raise ValueError(f"FCA inválido: agregação op='{agg.op}' não suportada.")
            if op != "count":
                if not agg.column:
                    raise ValueError("FCA inválido: agregação exige column (exceto count).")
                _ensure_col(allowed, agg.column, f"aggregations[{op}].column(select_infer)")
            alias = agg.alias or f"{op}_{agg.column or 'all'}"
            _ensure_alias_safe(alias)
            inferred.append(
                FCASelectItemDto(type="agg", agg=op, column=agg.column, alias=alias)
            )

        return inferred

    # Normaliza o select fornecido
    for i, it in enumerate(fca.select or []):
        t = _norm_str(it.type or "column").lower()
        if t == "column":
            name = _norm_str(it.name) if it.name is not None else ""
            if not name:
                raise ValueError(f"FCA inválido: select[{i}] type=column exige 'name'.")
            _ensure_col(allowed, name, f"select[{i}].name")
            alias = it.alias or name
            _ensure_alias_safe(alias)
            select_items.append(FCASelectItemDto(type="column", name=name, alias=alias))

        elif t == "agg":
            op = _norm_str(it.agg).lower() if it.agg is not None else ""
            if op not in _allowed_agg_ops():
                raise ValueError(f"FCA inválido: select[{i}] agg '{it.agg}' não suportado.")
            col = _norm_str(it.column) if it.column is not None else None
            if op != "count":
                if not col:
                    raise ValueError(f"FCA inválido: select[{i}] agg '{op}' exige 'column'.")
                _ensure_col(allowed, col, f"select[{i}].column")
            else:
                # count pode ser count(*) se column não vier
                if col:
                    _ensure_col(allowed, col, f"select[{i}].column(count)")
            alias = it.alias or (f"{op}_{col or 'all'}")
            _ensure_alias_safe(alias)
            select_items.append(FCASelectItemDto(type="agg", agg=op, column=col, alias=alias))

        else:
            raise ValueError(f"FCA inválido: select[{i}].type '{it.type}' desconhecido.")

    return select_items


# -----------------------------------------------------------------------------
# Normalização e validação do FCA inteiro
# -----------------------------------------------------------------------------

def validate_and_normalize_fca(
    fca: FCAArgsDto,
    columns_meta: list[dict],
    top_k: int,
    enforced_table_fqn: Optional[str] = None,
) -> FCAArgsDto:
    """
    Valida e normaliza um FCAArgsDto:
    - Aplica whitelist de colunas (não-geom)
    - Normaliza select (suporta multi-coluna + agregações)
    - Valida where, group_by, aggregations, order_by
    - Aplica defaults para limit/offset
    - Força table_fqn (se fornecido em enforced_table_fqn)

    Retorna o próprio objeto (mutável), pronto pro compiler.
    """
    if enforced_table_fqn:
        fca.table_fqn = enforced_table_fqn

    if not fca.table_fqn or not str(fca.table_fqn).strip():
        raise ValueError("FCA inválido: table_fqn é obrigatório (e deve ser forçado pelo backend).")

    allowed = _allowed_columns(columns_meta)

    # --- group_by ---
    gb_norm: list[str] = []
    for x in (fca.group_by or []):
        s = _norm_str(x)
        if s:
            gb_norm.append(s)
    fca.group_by = gb_norm
    _ensure_cols(allowed, fca.group_by, "group_by")

    # --- aggregations ---
    aggs_norm: list[FCAAggDto] = []
    for i, a in enumerate(fca.aggregations or []):
        op = _norm_str(a.op).lower()
        if op not in _allowed_agg_ops():
            raise ValueError(f"FCA inválido: aggregations[{i}].op '{a.op}' não suportado.")
        col = _norm_str(a.column) if a.column is not None else None
        if op != "count":
            if not col:
                raise ValueError(f"FCA inválido: aggregations[{i}] '{op}' exige column.")
            _ensure_col(allowed, col, f"aggregations[{i}].column")
        else:
            # count pode ser count(*) (column None) ou count(col)
            if col:
                _ensure_col(allowed, col, f"aggregations[{i}].column(count)")
        alias = a.alias or f"{op}_{col or 'all'}"
        _ensure_alias_safe(alias)
        aggs_norm.append(FCAAggDto(op=op, column=col, alias=alias))
    fca.aggregations = aggs_norm

    # --- select (pode ser inferido) ---
    fca.select = _normalize_select(fca, allowed)

    # --- where ---
    where_norm: list[FCAWhereDto] = []
    for i, w in enumerate(fca.where or []):
        col = _norm_str(w.column)
        if not col:
            raise ValueError(f"FCA inválido: where[{i}].column vazio.")
        _ensure_col(allowed, col, f"where[{i}].column")

        op = _norm_str(w.op).upper()
        if op not in _allowed_where_ops():
            raise ValueError(f"FCA inválido: where[{i}].op '{w.op}' não suportado.")

        # valida IN
        if op == "IN":
            if not isinstance(w.value, (list, tuple)):
                raise ValueError(f"FCA inválido: where[{i}] op=IN exige value como lista.")
            if len(w.value) == 0:
                raise ValueError(f"FCA inválido: where[{i}] op=IN não pode ser lista vazia.")

        # valida LIKE/ILIKE
        if op in ("LIKE", "ILIKE"):
            if not isinstance(w.value, str):
                raise ValueError(f"FCA inválido: where[{i}] op={op} exige value string.")

        where_norm.append(FCAWhereDto(column=col, op=op, value=w.value))
    fca.where = where_norm

    # --- order_by ---
    # expr pode ser:
    # - coluna (whitelist)
    # - alias de agregação (ou alias de item select)
    select_aliases = {(_norm_str(s.alias) if s.alias else "") for s in (fca.select or [])}
    select_aliases = {a for a in select_aliases if a}
    agg_aliases = {(_norm_str(a.alias) if a.alias else "") for a in (fca.aggregations or [])}
    agg_aliases = {a for a in agg_aliases if a}

    order_norm: list[FCAOrderByDto] = []
    for i, ob in enumerate(fca.order_by or []):
        expr = _norm_str(ob.expr)
        if not expr:
            raise ValueError(f"FCA inválido: order_by[{i}].expr vazio.")

        # permite ordenar por coluna ou por alias (select/agg)
        if expr in allowed:
            pass
        elif expr in select_aliases or expr in agg_aliases:
            pass
        else:
            raise ValueError(
                f"FCA inválido: order_by[{i}].expr '{expr}' não é coluna permitida nem alias conhecido."
            )

        d = _norm_str(ob.dir).lower()
        if d not in ("asc", "desc"):
            raise ValueError(f"FCA inválido: order_by[{i}].dir deve ser 'asc'|'desc'.")
        order_norm.append(FCAOrderByDto(expr=expr, dir=d))
    fca.order_by = order_norm

    # --- limit/offset ---
    # default: se limit None -> usa top_k (para evitar SELECT infinito)
    lim = _as_int_or_none(fca.limit)
    off = _as_int_or_none(fca.offset)

    if lim is None:
        lim = int(top_k)
    if lim <= 0:
        raise ValueError("FCA inválido: limit deve ser > 0.")
    if off is not None and off < 0:
        raise ValueError("FCA inválido: offset deve ser >= 0.")

    fca.limit = lim
    fca.offset = off

    return fca
