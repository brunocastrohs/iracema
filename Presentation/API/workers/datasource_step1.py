#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# datasource_builder_step1

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
from typing import Dict, Any, List
import requests
import psycopg2
from psycopg2.extras import execute_batch


def _norm(s):
    if s is None:
        return None
    s = str(s).strip()
    return s if s else None

def ensure_datasources_table(conn) -> None:
    """
    Garante que a tabela public.datasources exista com o schema esperado.
    Operação idempotente.
    """
    ddl = """
    CREATE TABLE IF NOT EXISTS public.datasources
    (
        id bigint NOT NULL DEFAULT nextval('datasources_id_seq'::regclass),
        categoria_informacao character varying(150) NOT NULL,
        classe_maior character varying(150),
        sub_classe_maior character varying(150),
        classe_menor character varying(150),
        identificador_tabela character varying(255) NOT NULL,
        titulo_tabela character varying(255) NOT NULL,
        descricao_tabela text,
        colunas_tabela jsonb NOT NULL DEFAULT '[]'::jsonb,
        fonte_dados text,
        ano_elaboracao smallint,
        is_ativo boolean NOT NULL DEFAULT true,
        created_at timestamptz NOT NULL DEFAULT now(),
        updated_at timestamptz NOT NULL DEFAULT now(),
        palavras_chave text,
        prompt_inicial text,
        prompt_inicial_fc text,
        CONSTRAINT datasources_pkey PRIMARY KEY (id),
        CONSTRAINT uq_datasources_identificador UNIQUE (identificador_tabela),
        CONSTRAINT ck_datasources_ano CHECK (
            ano_elaboracao IS NULL
            OR (ano_elaboracao >= 1900 AND ano_elaboracao <= 2100)
        )
    );
    """

    with conn.cursor() as cur:
        # sequência (caso BD esteja totalmente limpo)
        cur.execute("""
            CREATE SEQUENCE IF NOT EXISTS datasources_id_seq
            START WITH 1
            INCREMENT BY 1
            NO MINVALUE
            NO MAXVALUE
            CACHE 1;
        """)
        cur.execute(ddl)

def run_step1(config: Dict[str, Any]) -> int:
    db = config["db"]
    http = config["http"]
    endpoints = config["endpoints"]

    try:
        r = requests.get(endpoints["info"], timeout=http["timeout_secs"])
        r.raise_for_status()
        items = r.json()
        if not isinstance(items, list):
            raise RuntimeError("Resposta inesperada do endpoint")

        records = []
        for item in items:
            ident = _norm(item.get("nomenclatura_greencloud"))
            if not ident:
                continue

            records.append({
                "id": item.get("id"),
                "categoria_informacao": _norm(item.get("categoria_de_informacao")) or "N/A",
                "classe_maior": _norm(item.get("classe_maior")),
                "sub_classe_maior": _norm(item.get("sub_classe_maior")),
                "classe_menor": _norm(item.get("classe_menor")),
                "identificador_tabela": ident.lower(),
                "titulo_tabela": _norm(item.get("nomenclatura_pedea")) or ident,
                "is_ativo": bool(item.get("exibir_camada", True)),
            })

        conn = psycopg2.connect(**db)
        try:
            conn.autocommit = False

            with conn.cursor() as cur:
                # 🔑 garante existência da tabela
                ensure_datasources_table(conn)

                # 🔥 reset controlado
                cur.execute("TRUNCATE TABLE public.datasources;")

                sql = """
                  INSERT INTO public.datasources
                  (id, categoria_informacao, classe_maior, sub_classe_maior, classe_menor,
                   identificador_tabela, titulo_tabela, is_ativo)
                  VALUES
                  (%(id)s, %(categoria_informacao)s, %(classe_maior)s, %(sub_classe_maior)s,
                   %(classe_menor)s, %(identificador_tabela)s, %(titulo_tabela)s, %(is_ativo)s);
                """
                execute_batch(cur, sql, records, page_size=500)

            conn.commit()
            print(f"[Step1] Inseridos: {len(records)}")
            return 0

        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    except Exception as e:
        print(f"[Step1] ERRO: {e}", file=sys.stderr)
        return 1
