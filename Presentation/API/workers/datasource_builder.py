#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
datasource_builder.py

Orquestrador do pipeline de datasources.
- run_pipeline(): executa step1 -> step2 -> step3
- run_pipeline_as_seed(): só executa o pipeline se ainda não houver seed
"""

import sys
from typing import Dict, Any, Tuple

import psycopg2

from Presentation.API.settings import settings
from Presentation.API.workers.datasource_step1 import run_step1
from Presentation.API.workers.datasource_step2 import run_step2
from Presentation.API.workers.datasource_step3 import run_step3


def build_config() -> Dict[str, Any]:
    """
    Centraliza TODA configuração usada pelos steps.
    """
    return {
        "db": {
            "host": settings.DB_HOST,
            "port": settings.DB_PORT,
            "dbname": settings.DB_NAME,
            "user": settings.DB_USER,
            "password": settings.DB_PASSWORD,
        },
        "http": {
            "timeout_secs": settings.HTTP_TIMEOUT_SECS,
        },
        "schemas": {
            "target_schema": "zcm",
            "default_srid": 4674,
        },
        "endpoints": {
            "info": "https://pedea.sema.ce.gov.br/gestorapi/v1/infoDataExplorer",
            "txt_gestorapi": "https://pedea.sema.ce.gov.br/gestorapi/v1/arquivotxt/",
            "txt_portal": "https://pedea.sema.ce.gov.br/portal/metadata/",
            "txt_suffix": "_metadados.txt",
        },
    }


def _get_conn(config: Dict[str, Any]):
    return psycopg2.connect(**config["db"])


def _column_exists(conn, table_schema: str, table_name: str, column_name: str) -> bool:
    sql = """
      SELECT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = %s
          AND table_name = %s
          AND column_name = %s
      );
    """
    with conn.cursor() as cur:
        cur.execute(sql, (table_schema, table_name, column_name))
        return bool(cur.fetchone()[0])


def _count_datasources(conn) -> int:
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(1) FROM public.datasources;")
        return int(cur.fetchone()[0] or 0)


def _count_with_step2_metadata(conn) -> int:
    """
    Heurística: step2 preenche alguma dessas colunas.
    """
    sql = """
      SELECT COUNT(1)
      FROM public.datasources
      WHERE
        (descricao_tabela IS NOT NULL AND btrim(descricao_tabela) <> '')
        OR (palavras_chave IS NOT NULL AND btrim(palavras_chave) <> '')
        OR (ano_elaboracao IS NOT NULL)
        OR (fonte_dados IS NOT NULL AND btrim(fonte_dados) <> '');
    """
    with conn.cursor() as cur:
        cur.execute(sql)
        return int(cur.fetchone()[0] or 0)


def _count_with_step3_payload(conn) -> int:
    """
    Heurística: step3 preenche colunas_tabela (jsonb) e/ou prompt_inicial(_fc).
    """
    sql = """
      SELECT COUNT(1)
      FROM public.datasources
      WHERE
        (colunas_tabela IS NOT NULL)
        OR (prompt_inicial IS NOT NULL AND btrim(prompt_inicial) <> '')
        OR (prompt_inicial_fc IS NOT NULL AND btrim(prompt_inicial_fc) <> '');
    """
    with conn.cursor() as cur:
        cur.execute(sql)
        return int(cur.fetchone()[0] or 0)


def _seed_status(config: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Retorna (is_seeded, reason).
    """
    conn = _get_conn(config)
    try:
        conn.autocommit = True

        # Step 1: existe conteúdo em datasources?
        total = _count_datasources(conn)
        if total <= 0:
            return False, "public.datasources vazia (step1 não executado)."

        # Step 2: existe pelo menos um registro com metadados preenchidos?
        step2_count = _count_with_step2_metadata(conn)
        if step2_count <= 0:
            return False, "sem metadados (step2 não executado ou não persistiu nada)."

        # Step 3: colunas existem + tem payload/prompt preenchido?
        has_prompt = _column_exists(conn, "public", "datasources", "prompt_inicial")
        has_prompt_fc = _column_exists(conn, "public", "datasources", "prompt_inicial_fc")
        if not (has_prompt and has_prompt_fc):
            return False, "colunas prompt_inicial/prompt_inicial_fc não existem (step3 não executou)."

        step3_count = _count_with_step3_payload(conn)
        if step3_count <= 0:
            return False, "sem colunas_tabela/prompt preenchidos (step3 não executado ou não persistiu nada)."

        return True, f"seed OK (total={total}, step2={step2_count}, step3={step3_count})."

    finally:
        conn.close()


def run_pipeline() -> int:
    """
    Executa o pipeline completo:
    step1 → step2 → step3
    """
    config = build_config()

    print("[Pipeline] Iniciando datasource builder")

    for step_fn, name in [
        (run_step1, "STEP 1"),
        (run_step2, "STEP 2"),
        (run_step3, "STEP 3"),
    ]:
        print(f"[Pipeline] Executando {name}")
        rc = step_fn(config)
        if rc != 0:
            print(f"[Pipeline] {name} falhou (rc={rc})", file=sys.stderr)
            return rc

    print("[Pipeline] Concluído com sucesso")
    return 0


def run_pipeline_as_seed(force: bool = False) -> int:
    """
    Executa o pipeline SOMENTE se o seed ainda não estiver aplicado.

    - force=True: ignora checagens e roda o pipeline
    """
    config = build_config()

    if force:
        print("[Seed] force=True => executando pipeline completo.")
        return run_pipeline()

    try:
        seeded, reason = _seed_status(config)
    except Exception as e:
        # Em caso de dúvida (ex.: tabela ainda não existe), roda o seed.
        print(f"[Seed] Não foi possível avaliar seed com segurança: {e}", file=sys.stderr)
        print("[Seed] Executando pipeline para garantir estado.")
        return run_pipeline()

    if seeded:
        print(f"[Seed] Seed já aplicado: {reason}")
        return 0

    print(f"[Seed] Seed ausente: {reason}")
    print("[Seed] Executando pipeline completo...")
    return run_pipeline()


if __name__ == "__main__":
    # Por padrão, roda em modo seed (não destrói se já estiver pronto)
    raise SystemExit(run_pipeline_as_seed())
