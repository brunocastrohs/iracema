#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
step3_local — Popular datasources.colunas_tabela e prompts iniciais
com base nas tabelas já existentes no schema zcm.

- NÃO chama GeoServer
- NÃO cria tabelas zcm.*
- Apenas lê o schema local e atualiza:
  - public.datasources.colunas_tabela (jsonb)
  - public.datasources.prompt_inicial (text)        -> SQLCoder style (gera SQL)
  - public.datasources.prompt_inicial_fc (text)     -> Function Calling style (gera JSON args)

Regras:
- identificador_tabela no BD é lower case
- TABLE_NAME apontará para zcm."<identificador>"
- prompt inclui instrução de NÃO usar geom
"""

import json
import sys
from typing import Any, Dict, List, Optional

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


# -----------------------------------------------------------------------------
# Schema / migrations (colunas prompt)
# -----------------------------------------------------------------------------

def ensure_prompt_columns(conn) -> None:
    """
    Garante que datasources tem as colunas prompt_inicial e prompt_inicial_fc.
    """
    with conn.cursor() as cur:
        cur.execute("""
          ALTER TABLE public.datasources
          ADD COLUMN IF NOT EXISTS prompt_inicial TEXT;
        """)
        cur.execute("""
          ALTER TABLE public.datasources
          ADD COLUMN IF NOT EXISTS prompt_inicial_fc TEXT;
        """)


# -----------------------------------------------------------------------------
# Datasources + introspecção
# -----------------------------------------------------------------------------

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
    Retorna dict: { geom_column_name: {geom_type, srid} }
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

    Observação:
    - Mantive a regra original do seu script: AND column_name not ilike 'geom'
      (ou seja, não traz a coluna geom literal). Se você quiser incluir colunas
      geom com outros nomes, o detector ainda funciona.
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
          WHERE table_schema = %s
            AND table_name = %s
            AND column_name not ilike 'geom'
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


# -----------------------------------------------------------------------------
# Prompt builders
# -----------------------------------------------------------------------------

def build_prompt_inicial(
    table_name: str,
    cols: List[Dict[str, Any]],
    question_placeholder: str = "{PERGUNTA_DO_USUARIO}",
) -> str:
    """
    Gera o prompt inicial no template do SQLCoder (PT-BR),
    preenchendo dinamicamente a seção ### Esquema com um CREATE TABLE.

    - Termina com "### SQL"
    - A pergunta entra em {PERGUNTA_DO_USUARIO}
    """
    def norm_bool(v: Any) -> bool:
        return bool(v) if v is not None else False

    col_defs: List[str] = []
    for c in cols or []:
        col_name = str(c.get("name", "")).strip()
        col_type = str(c.get("type", "TEXT")).strip() or "TEXT"
        nullable = norm_bool(c.get("nullable", True))

        if not col_name:
            continue

        null_sql = "" if nullable else " NOT NULL"
        col_defs.append(f"  {col_name} {col_type}{null_sql}")

    if col_defs:
        create_table = "CREATE TABLE " + table_name + " (\n" + ",\n".join(col_defs) + "\n);"
    else:
        create_table = f"CREATE TABLE {table_name} (\n  -- (sem colunas detectadas)\n);"

    return f"""### Tarefa
Escreva UMA consulta SELECT em PostgreSQL que responda à pergunta.
Retorne APENAS a consulta SQL.

### Esquema
{create_table}

### Pergunta
{question_placeholder}

### SQL
"""


def build_prompt_inicial_fc(
    table_name: str,
    cols: List[Dict[str, Any]],
    question_placeholder: str = "{PERGUNTA_DO_USUARIO}",
) -> str:
    non_geom_cols: List[str] = []
    geom_cols: List[str] = []

    for c in cols or []:
        name = str(c.get("name") or "").strip()
        if not name:
            continue
        if c.get("is_geometry"):
            geom_cols.append(name)
        else:
            non_geom_cols.append(name)

    non_geom_str = ", ".join(non_geom_cols) if non_geom_cols else "(nenhuma detectada)"
    geom_str = ", ".join(geom_cols) if geom_cols else "(nenhuma)"

    numeric_cols = []
    text_cols = []
    for c in cols or []:
        name = str(c.get("name") or "").strip()
        ctype = str(c.get("type") or "").lower()
        if not name or c.get("is_geometry"):
            continue
        if any(t in ctype for t in ["numeric", "double", "real", "float", "int", "bigint", "smallint", "decimal"]):
            numeric_cols.append(name)
        else:
            text_cols.append(name)

    numeric_str = ", ".join(numeric_cols) if numeric_cols else "(nenhuma)"
    text_str = ", ".join(text_cols) if text_cols else "(nenhuma)"

    return f"""Você é um assistente que converte perguntas em linguagem natural em um PLANO ESTRUTURADO (JSON) para consultas em PostgreSQL.

REGRAS OBRIGATÓRIAS:
- NÃO gere SQL.
- NÃO gere explicações em texto.
- RETORNE APENAS um JSON compatível com QueryPlanArgsDto.
- Use SOMENTE colunas existentes na tabela.
- NUNCA use colunas geométricas para cálculos, filtros, agrupamentos ou seleção.

TABELA ALVO:
{table_name}

COLUNAS DISPONÍVEIS (não-geom):
{non_geom_str}

COLUNAS NUMÉRICAS (candidatas a SUM):
{numeric_str}

COLUNAS TEXTUAIS (candidatas a GROUP BY / DISTINCT):
{text_str}

COLUNAS GEOMÉTRICAS (PROIBIDAS):
{geom_str}

INTENÇÕES SUPORTADAS (campo 'intent'):
- schema        -> listar colunas / estrutura
- count         -> contar registros
- distinct      -> listar valores distintos (1+ colunas)
- sum           -> somar valores de uma coluna numérica
- grouped_sum   -> somar valores agrupados por 1+ colunas
- detail        -> retornar linhas detalhadas (pode selecionar 1+ colunas)

MAPEAMENTO OBRIGATÓRIO PARA DETAIL (MULTI-COLUNA):
- Se a pergunta pedir "consultar/trazer/mostrar/listar A e B" (ou múltiplas colunas),
  use intent="detail" e preencha "select_columns" com uma LISTA de colunas.
  Exemplo: "Consultar data e num_proces" -> intent="detail", select_columns=["data","num_proces"].

REGRAS PARA CAMPOS:
- detail:
  - use select_columns (lista) quando houver colunas explícitas.
  - se o usuário não citar colunas, pode omitir select_columns (executor usa "*").
- distinct:
  - use select_columns com 1+ colunas para DISTINCT.
- grouped_sum:
  - group_by DEVE ser lista (1+ colunas).
  - value_column DEVE ser uma coluna numérica.

PERGUNTA:
{question_placeholder}

RETORNE APENAS JSON. Sem markdown. Sem texto extra.
Campos esperados: intent, select_columns, target_column, value_column, group_by, filters, order_by, order_dir, limit.
"""



# -----------------------------------------------------------------------------
# Update datasource
# -----------------------------------------------------------------------------

def update_datasource(
    conn,
    ident: str,
    cols: List[Dict[str, Any]],
    prompt_inicial: str,
    prompt_inicial_fc: str,
) -> None:
    with conn.cursor() as cur:
        cur.execute("""
          UPDATE public.datasources
          SET
            colunas_tabela = %s::jsonb,
            prompt_inicial = %s,
            prompt_inicial_fc = %s,
            updated_at = NOW()
          WHERE identificador_tabela = %s;
        """, (json.dumps(cols, ensure_ascii=False), prompt_inicial, prompt_inicial_fc, ident))


# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------

def main() -> int:
    conn = psycopg2.connect(**DB)
    try:
        conn.autocommit = False

        ensure_prompt_columns(conn)
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

            table_name = f'{TARGET_SCHEMA}."{ident}"'

            prompt_inicial = build_prompt_inicial(table_name, cols)
            prompt_inicial_fc = build_prompt_inicial_fc(table_name, cols)

            update_datasource(conn, ident, cols, prompt_inicial, prompt_inicial_fc)
            conn.commit()
            updated += 1

        print(f"[step3_local] Atualizados (colunas_tabela + prompt_inicial + prompt_inicial_fc): {updated}")
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
