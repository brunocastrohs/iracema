#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Etapa 1 — Popular public.datasources a partir do endpoint PEDEA infoDataExplorer

- Faz TRUNCATE (reset completo) na tabela public.datasources
- Busca JSON em:
  https://pedea.sema.ce.gov.br/gestorapi/v1/infoDataExplorer
- Mapeia campos:
  id -> id
  categoria_de_informacao -> categoria_informacao
  classe_maior -> classe_maior
  sub_classe_maior -> sub_classe_maior
  classe_menor -> classe_menor
  nomenclatura_greencloud -> identificador_tabela (SEMPRE lower case no BD)
  nomenclatura_pedea -> titulo_tabela
  exibir_camada -> is_ativo
"""

import sys
from typing import Optional, Any, Dict, List

import requests
import psycopg2
from psycopg2.extras import execute_batch


DB = {
    "host": "localhost",
    "port": 5435,
    "dbname": "iracema",
    "user": "postgres",
    "password": "002100",
}

ENDPOINT_INFO = "https://pedea.sema.ce.gov.br/gestorapi/v1/infoDataExplorer"
TIMEOUT_SECS = 60


def _norm(s: Optional[str]) -> Optional[str]:
    if s is None:
        return None
    s = str(s).strip()
    return s if s else None


def fetch_info_data() -> List[Dict[str, Any]]:
    r = requests.get(ENDPOINT_INFO, timeout=TIMEOUT_SECS)
    r.raise_for_status()
    data = r.json()
    if not isinstance(data, list):
        raise RuntimeError("Resposta inesperada do endpoint: esperava uma lista JSON.")
    return data


def build_records(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []

    for item in items:
        identificador = _norm(item.get("nomenclatura_greencloud"))
        if not identificador:
            continue

        identificador = identificador.lower()  # REGRA: sempre lower case no BD

        titulo = _norm(item.get("nomenclatura_pedea")) or identificador
        cat = _norm(item.get("categoria_de_informacao")) or "N/A"

        rec = {
            "id": item.get("id"),
            "categoria_informacao": cat,
            "classe_maior": _norm(item.get("classe_maior")),
            "sub_classe_maior": _norm(item.get("sub_classe_maior")),
            "classe_menor": _norm(item.get("classe_menor")),
            "identificador_tabela": identificador,
            "titulo_tabela": titulo,
            "is_ativo": bool(item.get("exibir_camada", True)),
        }
        records.append(rec)

    return records


def truncate_table(conn) -> None:
    # Reset total. Se você quiser também resetar sequence, pode adicionar RESTART IDENTITY.
    sql = "TRUNCATE TABLE public.datasources;"
    with conn.cursor() as cur:
        cur.execute(sql)


def insert_all(conn, records: List[Dict[str, Any]]) -> int:
    if not records:
        return 0

    sql = """
      INSERT INTO public.datasources
      (id, categoria_informacao, classe_maior, sub_classe_maior, classe_menor,
       identificador_tabela, titulo_tabela, is_ativo)
      VALUES
      (%(id)s, %(categoria_informacao)s, %(classe_maior)s, %(sub_classe_maior)s, %(classe_menor)s,
       %(identificador_tabela)s, %(titulo_tabela)s, %(is_ativo)s);
    """

    with conn.cursor() as cur:
        execute_batch(cur, sql, records, page_size=500)

    return len(records)


def main() -> int:
    try:
        items = fetch_info_data()
        records = build_records(items)

        print(f"[Step1] Itens recebidos do endpoint: {len(items)}")
        print(f"[Step1] Registros válidos p/ inserir: {len(records)}")

        conn = psycopg2.connect(**DB)
        try:
            conn.autocommit = False
            truncate_table(conn)
            inserted = insert_all(conn, records)
            conn.commit()
            print(f"[Step1] TRUNCATE + INSERT concluído. Inseridos: {inserted}")
            return 0
        except Exception as e:
            conn.rollback()
            print(f"[Step1] ERRO BD: {e}", file=sys.stderr)
            return 1
        finally:
            conn.close()

    except Exception as e:
        print(f"[Step1] ERRO: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
