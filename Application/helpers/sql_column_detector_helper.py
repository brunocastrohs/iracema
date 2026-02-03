# Application/helpers/sql/sql_column_detector.py

import re
from typing import Optional

from Application.helpers.sql_intent_detector_helper import has_area_hint, has_perim_hint

def _normalize_text(s: str) -> str:
    return re.sub(r"[^a-z0-9_]+", " ", (s or "").lower()).strip()

def _token_boundary_pattern(col_name: str) -> re.Pattern:
    escaped = re.escape(col_name.lower())
    return re.compile(rf"(?<![a-z0-9_]){escaped}(?![a-z0-9_])", re.IGNORECASE)

def detect_target_column(question: str, columns_meta: list[dict]) -> Optional[str]:
    q = (question or "").lower()
    for col in columns_meta or []:
        name = col.get("name")
        if not name or col.get("is_geometry"):
            continue
        # aqui ainda é substring; ok para "quais valores de zonas"
        if name.lower() in q:
            return name
    return None

def detect_groupby_column(question: str, columns_meta: list[dict]) -> Optional[str]:
    q_norm = _normalize_text(question)

    cols = [
        c.get("name")
        for c in (columns_meta or [])
        if c.get("name") and not c.get("is_geometry")
    ]

    # prioridade: nomes maiores primeiro (nomepan > pan)
    cols_sorted = sorted(cols, key=lambda x: len(x), reverse=True)

    for col in cols_sorted:
        if _token_boundary_pattern(col).search(q_norm):
            return col

    return None

def detect_sum_column(question: str, columns_meta: list[dict]) -> Optional[str]:
    cols = [c.get("name") for c in (columns_meta or []) if c.get("name")]

    if has_area_hint(question):
        for name in cols:
            if name and "area" in name.lower():
                return name

    if has_perim_hint(question):
        for name in cols:
            if name and ("perimet" in name.lower() or "perimetro" in name.lower()):
                return name

    return None
