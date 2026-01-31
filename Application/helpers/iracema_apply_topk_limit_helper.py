import re

_LIMIT_RE = re.compile(r"\blimit\s+(\d+)\b", re.IGNORECASE)

def apply_topk_limit(sql: str, top_k: int) -> str:
    s = (sql or "").strip().rstrip(";")
    if _LIMIT_RE.search(s):
        s = _LIMIT_RE.sub(f"LIMIT {int(top_k)}", s)
    else:
        # só aplica LIMIT se for query "listável" (opcional)
        s = f"{s}\nLIMIT {int(top_k)}"
    return s + ";"
