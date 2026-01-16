#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
step3_local — Popular datasources.colunas_tabela e datasources.prompt_inicial
com base nas tabelas já existentes no schema zcm.

- NÃO chama GeoServer
- NÃO cria tabelas zcm.*
- Apenas lê o schema local e atualiza:
  - public.datasources.colunas_tabela (jsonb)
  - public.datasources.prompt_inicial (text)

Regras:
- identificador_tabela no BD é lower case
- TABLE_NAME apontará para zcm."<identificador>"
- prompt inclui instrução de NÃO usar geom
"""

import json
import sys
from typing import Any, Dict, List, Optional, Tuple

import psycopg2

TOP_K = 1000

DB = {
    "host": "localhost",
    "port": 5435,
    "dbname": "iracema",
    "user": "postgres",
    "password": "002100",
}

TARGET_SCHEMA = "zcm"
SRID_DEFAULT = 4674  # se geometry_columns não retornar SRID, usa esse


def ensure_prompt_column(conn) -> None:
    with conn.cursor() as cur:
        cur.execute("""
          ALTER TABLE public.datasources
          ADD COLUMN IF NOT EXISTS prompt_inicial TEXT;
        """)


def fetch_datasource_identifiers(conn) -> List[str]:
    with conn.cursor() as cur:
        cur.execute("""
          SELECT identificador_tabela
          FROM public.datasources
          WHERE identificador_tabela IS NOT NULL
          ORDER BY identificador_tabela;
        """)
        return [r[0] for r in cur.fetchall()]


def table_exists(conn, schema: str, table: str) -> bool:
    with conn.cursor() as cur:
        cur.execute("""
          SELECT EXISTS(
            SELECT 1
            FROM information_schema.tables
            WHERE table_schema = %s AND table_name = %s
          );
        """, (schema, table))
        return bool(cur.fetchone()[0])


def get_geometry_info(conn, schema: str, table: str) -> Dict[str, Dict[str, Any]]:
    """
    Retorna dict: { geom_column_name: {type, srid} }
    Usa public.geometry_columns (PostGIS).
    """
    with conn.cursor() as cur:
        cur.execute("""
          SELECT f_geometry_column, type, srid
          FROM public.geometry_columns
          WHERE f_table_schema = %s AND f_table_name = %s;
        """, (schema, table))
        rows = cur.fetchall()

    out: Dict[str, Dict[str, Any]] = {}
    for col, gtype, srid in rows:
        out[col] = {
            "geom_type": gtype,
            "srid": srid if srid is not None else SRID_DEFAULT,
        }
    return out


def get_table_columns(conn, schema: str, table: str) -> List[Dict[str, Any]]:
    """
    Lista colunas via information_schema, e enriquece com info de geometria quando existir.
    """
    geom_info = get_geometry_info(conn, schema, table)

    with conn.cursor() as cur:
        cur.execute("""
          SELECT
            column_name,
            data_type,
            udt_name,
            is_nullable,
            ordinal_position
          FROM information_schema.columns
          WHERE table_schema = %s AND table_name = %s AND column_name not ilike 'geom'
          ORDER BY ordinal_position;
        """, (schema, table))
        rows = cur.fetchall()

    cols: List[Dict[str, Any]] = []
    for name, data_type, udt_name, is_nullable, _pos in rows:
        nullable = (is_nullable == "YES")

        # geometria: normalmente data_type == "USER-DEFINED" e udt_name == "geometry"
        if name in geom_info or (data_type == "USER-DEFINED" and udt_name == "geometry"):
            gi = geom_info.get(name, {"geom_type": "Geometry", "srid": SRID_DEFAULT})
            geom_type = gi["geom_type"]
            srid = gi["srid"]
            cols.append({
                "name": name,
                "type": f"geometry({geom_type},{srid})",
                "is_geometry": True,
                "nullable": nullable,
                "description": None,
            })
        else:
            # padroniza tipos para algo “legível” no prompt
            pg_type = data_type
            if data_type == "USER-DEFINED":
                pg_type = udt_name  # ex.: "numeric", "uuid", etc.

            cols.append({
                "name": name,
                "type": pg_type,
                "is_geometry": False,
                "nullable": nullable,
                "description": None,
            })

    return cols


def build_prompt_inicial(table_name: str, cols: List[Dict[str, Any]]) -> str:
    """
    Gera o texto do prompt_inicial seguindo o template do usuário,
    mas preenchendo o 'Esquema da tabela' dinamicamente a partir das colunas reais.
    """
    # monta bullets do esquema
    lines = []
    for c in cols:
        col_name = c["name"]
        col_type = c["type"]
        nullable = c["nullable"]
        is_geom = c["is_geometry"]

        null_txt = "NULL" if nullable else "NOT NULL"
        if is_geom:
            lines.append(f"- {col_name:<10} ({col_type}): geometria da feição. ({null_txt})")
        else:
            lines.append(f"- {col_name:<10} ({col_type}): ({null_txt})")

    schema_lines = "\n".join(lines) if lines else "(sem colunas detectadas)"

    return f"""Você é um assistente especializado na base de dados {table_name}. Trabalhe EXCLUSIVAMENTE com a tabela {table_name} no PostgreSQL. Campos/Atributos da tabela:

            {schema_lines}

            Regras importantes:

            1. Gere apenas comandos SQL do tipo SELECT (e agregações).
            2. NUNCA utilize INSERT, UPDATE, DELETE, DROP, ALTER ou comandos de definição de schema.
            3. Sempre referencie explicitamente o nome da tabela: {table_name}.
            4. Prefira filtros em colunas textuais usando ILIKE quando fizer sentido.
            5. Use aliases amigáveis.
            6. Respeite um LIMIT se o usuário não pedir agregações (por exemplo LIMIT {TOP_K}).
            """

def update_datasource(conn, ident: str, cols: List[Dict[str, Any]], prompt_inicial: str) -> None:
    with conn.cursor() as cur:
        cur.execute("""
          UPDATE public.datasources
          SET
            colunas_tabela = %s::jsonb,
            prompt_inicial = %s,
            updated_at = NOW()
          WHERE identificador_tabela = %s;
        """, (json.dumps(cols, ensure_ascii=False), prompt_inicial, ident))


def main() -> int:
    conn = psycopg2.connect(**DB)
    try:
        conn.autocommit = False
        ensure_prompt_column(conn)
        conn.commit()

        ids = fetch_datasource_identifiers(conn)
        print(f"[step3_local] Datasources no BD: {len(ids)}")

        updated = 0
        missing_tables = 0

        for ident in ids:
            if not ident:
                continue

            ident = ident.strip().lower()

            if not table_exists(conn, TARGET_SCHEMA, ident):
                missing_tables += 1
                continue

            cols = get_table_columns(conn, TARGET_SCHEMA, ident)

            # IMPORTANT: aqui definimos o nome completo da tabela para o prompt
            # Se você quiser forçar public."...", basta trocar TARGET_SCHEMA por "public".
            table_name = f'{TARGET_SCHEMA}."{ident}"'

            prompt_inicial = build_prompt_inicial(table_name, cols)

            update_datasource(conn, ident, cols, prompt_inicial)
            conn.commit()
            updated += 1

        print(f"[step3_local] Atualizados (colunas_tabela + prompt_inicial): {updated}")
        print(f"[step3_local] Tabelas ausentes em {TARGET_SCHEMA}: {missing_tables}")

        return 0

    except Exception as e:
        conn.rollback()
        print(f"[step3_local] ERRO: {e}", file=sys.stderr)
        return 1
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
