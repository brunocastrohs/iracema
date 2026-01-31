import re

def normalize_question(q: str) -> str:
    s = (q or "").strip().lower()
    s = re.sub(r"\s+", " ", s)
    return s