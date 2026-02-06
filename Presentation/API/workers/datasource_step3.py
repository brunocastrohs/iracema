#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
datasource_step3.py

step3_local — Popular:
- public.datasources.colunas_tabela (jsonb)
- public.datasources.prompt_inicial (text)        -> SQLCoder style (gera SQL)
- public.datasources.prompt_inicial_fc (text)     -> Function Calling style (gera JSON args)

com base nas tabelas já existentes no schema TARGET_SCHEMA (ex.: zcm).

Regras:
- NÃO chama GeoServer
- NÃO cria tabelas zcm.*
- identificador_tabela no BD é lower case
- prompt inclui instrução de NÃO usar geom
"""

import json
import sys
from typing import Any, Dict, List, Optional

import psycopg2


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


def get_geometry_info(conn, schema: str, table: str, default_srid: int) -> Dict[str, Dict[str, Any]]:
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
            "srid": srid if srid is not None else default_srid,
        }
    return out


def get_table_columns(conn, schema: str, table: str, default_srid: int) -> List[Dict[str, Any]]:
    """
    Lista colunas via information_schema, e enriquece com info de geometria quando existir.

    Observação:
    - Mantém a regra: AND column_name not ilike 'geom' (não traz "geom" literal).
      Se você quiser excluir qualquer coluna geometry (mesmo com outro nome),
      dá pra ajustar depois.
    """
    geom_info = get_geometry_info(conn, schema, table, default_srid)

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
            gi = geom_info.get(name, {"geom_type": "Geometry", "srid": default_srid})
            cols.append({
                "name": name,
                "type": f'geometry({gi["geom_type"]},{gi["srid"]})',
                "is_geometry": True,
                "nullable": nullable,
                "description": None,
            })
        else:
            pg_type = data_type
            if data_type == "USER-DEFINED":
                pg_type = udt_name  # ex.: "uuid", "numeric", etc.

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
    Template SQLCoder (PT-BR). Termina com "### SQL".
    """
    col_defs: List[str] = []
    for c in cols or []:
        col_name = str(c.get("name", "")).strip()
        col_type = str(c.get("type", "TEXT")).strip() or "TEXT"
        nullable = bool(c.get("nullable", True))

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

    numeric_cols: List[str] = []
    text_cols: List[str] = []

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
# Public step entrypoint
# -----------------------------------------------------------------------------

def run_step3(config: Dict[str, Any]) -> int:
    """
    Executa o step3 usando config injetado pelo pipeline.
    """
    db = config["db"]
    schema_cfg = config.get("schemas") or {}
    target_schema = schema_cfg.get("target_schema", "zcm")
    default_srid = int(schema_cfg.get("default_srid", 4674))

    conn = psycopg2.connect(**db)
    try:
        conn.autocommit = False

        ensure_prompt_columns(conn)
        conn.commit()

        ids = fetch_datasource_identifiers(conn)
        print(f"[Step3] Datasources no BD: {len(ids)}")

        updated = 0
        missing_tables = 0

        for ident in ids:
            ident = (ident or "").strip().lower()
            if not ident:
                continue

            if not table_exists(conn, target_schema, ident):
                missing_tables += 1
                continue

            cols = get_table_columns(conn, target_schema, ident, default_srid)
            table_name = f'{target_schema}."{ident}"'

            prompt_inicial = build_prompt_inicial(table_name, cols)
            prompt_inicial_fc = build_prompt_inicial_fc(table_name, cols)

            update_datasource(conn, ident, cols, prompt_inicial, prompt_inicial_fc)
            conn.commit()
            updated += 1

        print(f"[Step3] Atualizados (colunas_tabela + prompt_inicial + prompt_inicial_fc): {updated}")
        print(f"[Step3] Tabelas ausentes em {target_schema}: {missing_tables}")

        return 0

    except Exception as e:
        conn.rollback()
        print(f"[Step3] ERRO: {e}", file=sys.stderr)
        return 1
    finally:
        conn.close()