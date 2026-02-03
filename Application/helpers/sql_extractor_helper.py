# Application/helpers/sql/sql_extractor.py

import re
from typing import Optional

_CODE_FENCE_SQL = re.compile(r"```(?:sql)?\s*(.*?)\s*```", re.IGNORECASE | re.DOTALL)

def extract_sql(raw: Optional[str]) -> str:
    """
    Extrai SQL de uma string potencialmente contendo:
      - ```sql ... ```
      - ``` ... ```
      - backticks
      - texto extra

    Retorna string "crua", sem normalização de whitespace.
    """
    if not raw:
        return ""

    s = str(raw).strip()

    # se vier em code fence, pega conteúdo interno
    m = _CODE_FENCE_SQL.search(s)
    if m:
        s = m.group(1).strip()

    # remove backticks soltos
    s = s.strip("`").strip()

    # Em alguns modelos, pode vir prefixos tipo "SQL:" ou "### SQL"
    # Não removemos agressivamente para não cortar queries válidas.
    # Se quiser, você pode adicionar uma limpeza opcional aqui.

    return s
