#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
datasource_step2.py (standalone)

Step2 — Atualiza public.datasources a partir de TXT de metadados do PEDEA.

- Config hardcoded (sem importar settings)
- Parser por LABEL (robusto para "2. Resumo:" e "02.Resumo:")
- Reparo de mojibake (UTF-8 interpretado como Latin-1) SEM destruir quebras de linha
"""

import argparse
import re
import sys
from typing import Any, Dict, List, Optional, Tuple

import psycopg2
import requests


# =========================
# Hardcoded defaults
# =========================

DEFAULT_DB = {
    "host": "localhost",
    "port": 5435,
    "dbname": "iracema",
    "user": "postgres",
    "password": "002100",
}

DEFAULT_HTTP_TIMEOUT_SECS = 100

DEFAULT_TARGET = {
    "schema": "public",
    "table": "datasources",
    "id_column": "identificador_tabela",
}

DEFAULT_ENDPOINTS = {
    "txt_gestorapi": "https://pedea.sema.ce.gov.br/gestorapi/v1/arquivotxt/",
    "txt_portal": "https://pedea.sema.ce.gov.br/portal/metadata/",
    "txt_suffix": "_metadados.txt",
}


# =========================
# Parsing helpers
# =========================

YEAR_RE = re.compile(r"(\d{4})")

# "02.Resumo: ..." / "2. Resumo: ..." / "Resumo: ..."
LINE_ITEM_RE = re.compile(r"^\s*(?:(\d{1,2})\s*[\.\)]\s*)?(.+?)\s*:\s*(.*)\s*$")


def parse_year(text: Optional[str]) -> Optional[int]:
    if not text:
        return None
    m = YEAR_RE.search(text)
    if not m:
        return None
    try:
        year = int(m.group(1))
        return year if 1900 <= year <= 2100 else None
    except ValueError:
        return None


# =========================
# Encoding / mojibake repair (sem achatar linhas)
# =========================

_MOJIBAKE_MARKERS = ("Ã", "Â", "¤", "¢", "£", "§", "ª", "º")


def looks_like_mojibake(s: str) -> bool:
    """
    Mojibake típico UTF-8 interpretado como Latin-1 contém 'Ã' e/ou 'Â'.
    Ex.: 'CearÃ¡', 'Ã§', 'Ã£', 'Â ' (NBSP)
    """
    if not s:
        return False
    if ("Ã" not in s) and ("Â" not in s):
        return False
    # se tem 'Ã' ou 'Â' já é evidência forte
    return True



def repair_mojibake_utf8_from_latin1(s: str) -> Optional[str]:
    """
    Repara somente quando a conversão é válida em modo strict.
    Se não for válida, retorna None (não mexe no texto original).
    """
    try:
        return s.encode("latin-1", errors="strict").decode("utf-8", errors="strict")
    except Exception:
        return None



def repair_text_preserve_lines(text: str) -> str:
    if not text:
        return ""

    replacements = {
        "\u00a0": " ",
        "": '"', "": '"', "“": '"', "”": '"',
        "": "-", "–": "-", "": "-", "—": "-",
        "": "'", "‘": "'", "’": "'",
    }
    for bad, good in replacements.items():
        text = text.replace(bad, good)

    if looks_like_mojibake(text):
        repaired = repair_mojibake_utf8_from_latin1(text)
        if repaired is not None:
            # só troca se melhorou (menos Ã/Â e não aumentou �)
            if (repaired.count("Ã") + repaired.count("Â")) < (text.count("Ã") + text.count("Â")) and repaired.count("�") <= text.count("�"):
                text = repaired

    return text



def normalize_field(value: str) -> str:
    """
    Compacta whitespace APENAS do campo final (resumo/palavras/fonte),
    mantendo texto legível e sem corromper parse por linhas.
    """
    if not value:
        return ""
    # transforma quebras de linha em espaço, e compacta
    return " ".join(value.replace("\r", "\n").split())


def decode_portal_content(content_bytes: bytes) -> str:
    """
    Portal pode vir sem charset.
    Estratégia:
      1) tenta utf-8
      2) fallback latin-1
    """
    if not content_bytes:
        return ""
    try:
        return content_bytes.decode("utf-8")
    except Exception:
        return content_bytes.decode("latin-1", errors="replace")


# =========================
# HTTP helpers
# =========================

def _http_get_text(url: str, timeout_secs: int) -> Tuple[Optional[str], Optional[str]]:
    try:
        r = requests.get(url, timeout=timeout_secs)
    except requests.exceptions.Timeout:
        return None, f"timeout: {url}"
    except requests.exceptions.RequestException as e:
        return None, f"request_exception: {url} | {e}"

    if r.status_code == 200:
        return r.text, None
    if r.status_code == 404:
        return None, f"not_found_404: {url}"
    if 500 <= r.status_code <= 599:
        return None, f"server_error_{r.status_code}: {url}"
    return None, f"http_{r.status_code}: {url}"


def fetch_metadata_txt_gestorapi(
    identificador_local: str,
    endpoints: Dict[str, Any],
    timeout_secs: int,
) -> Tuple[Optional[str], Optional[str]]:
    remote_id = identificador_local.replace("_ce_", "_CE_")
    url = f'{endpoints["txt_gestorapi"]}{remote_id}{endpoints["txt_suffix"]}'
    return _http_get_text(url, timeout_secs)


def fetch_metadata_txt_portal(
    identificador_local: str,
    endpoints: Dict[str, Any],
    timeout_secs: int,
) -> Tuple[Optional[str], Optional[str]]:
    url = f'{endpoints["txt_portal"]}{identificador_local}{endpoints["txt_suffix"]}'
    try:
        r = requests.get(url, timeout=timeout_secs)
    except requests.exceptions.Timeout:
        return None, f"timeout: {url}"
    except requests.exceptions.RequestException as e:
        return None, f"request_exception: {url} | {e}"

    if r.status_code == 200:
        return decode_portal_content(r.content), None

    if r.status_code == 404:
        return None, f"not_found_404: {url}"
    if 500 <= r.status_code <= 599:
        return None, f"server_error_{r.status_code}: {url}"
    return None, f"http_{r.status_code}: {url}"


def fetch_metadata_with_fallback(
    identificador_local: str,
    endpoints: Dict[str, Any],
    timeout_secs: int,
) -> Tuple[Optional[str], Optional[str], str]:
    txt, err = fetch_metadata_txt_gestorapi(identificador_local, endpoints, timeout_secs)
    if txt is not None:
        return txt, None, "gestorapi"

    txt2, err2 = fetch_metadata_txt_portal(identificador_local, endpoints, timeout_secs)
    if txt2 is not None:
        return txt2, None, "portal"

    return None, f"gestorapi_fail=({err}); portal_fail=({err2})", "none"


# =========================
# Label-based metadata parser
# =========================

def parse_metadata(content: str) -> Dict[str, str]:
    """
    Retorna dict com chaves canônicas:
      - titulo
      - resumo
      - palavras_chave
      - data_elaboracao
      - fonte_dados
    """
    out: Dict[str, str] = {}

    def canon_label(label: str) -> Optional[str]:
        l = label.strip().lower()
        l2 = re.sub(r"\(.*?\)", "", l).strip()

        if l2.startswith("título") or l2.startswith("titulo"):
            return "titulo"
        if l2.startswith("resumo"):
            return "resumo"
        if l2.startswith("palavras-chave") or l2.startswith("palavras chave"):
            return "palavras_chave"
        if l2.startswith("data de elaboração") or l2.startswith("data de elaboracao"):
            return "data_elaboracao"
        if l2.startswith("fonte dos dados") or l2.startswith("fonte de dados"):
            return "fonte_dados"
        return None

    current_key: Optional[str] = None

    for raw in content.splitlines():
        line = raw.strip()

        if not line:
            continue

        m = LINE_ITEM_RE.match(line)
        if m:
            label = m.group(2) or ""
            value = (m.group(3) or "").strip()

            key = canon_label(label)
            if key:
                current_key = key
                # inicia/define valor
                out[key] = value if value else ""
                continue

        # continuação do último campo reconhecido
        if current_key:
            prev = out.get(current_key, "")
            out[current_key] = (prev + "\n" + line).strip() if prev else line

    return out


# =========================
# DB helpers
# =========================

def _get_conn(db: Dict[str, Any]):
    return psycopg2.connect(**db)


def fetch_all_identificadores(
    conn,
    schema: str,
    table: str,
    id_column: str,
    prefix: Optional[str],
    limit: Optional[int],
) -> List[str]:
    where = [f"{id_column} IS NOT NULL"]
    params: List[Any] = []

    if prefix:
        where.append(f"{id_column} ILIKE %s")
        params.append(prefix + "%")

    sql = f"""
      SELECT {id_column}
      FROM {schema}.{table}
      WHERE {" AND ".join(where)}
      ORDER BY {id_column}
    """
    if limit and limit > 0:
        sql += " LIMIT %s"
        params.append(limit)

    with conn.cursor() as cur:
        cur.execute(sql, params)
        return [r[0] for r in cur.fetchall()]


def update_datasource(
    conn,
    schema: str,
    table: str,
    id_column: str,
    identificador_local: str,
    resumo: Optional[str],
    palavras: Optional[str],
    ano: Optional[int],
    fonte: Optional[str],
    force: bool,
) -> bool:
    if force:
        sql = f"""
          UPDATE {schema}.{table}
          SET
            descricao_tabela = COALESCE(%s, descricao_tabela),
            palavras_chave   = COALESCE(%s, palavras_chave),
            ano_elaboracao   = COALESCE(%s, ano_elaboracao),
            fonte_dados      = COALESCE(%s, fonte_dados),
            updated_at       = NOW()
          WHERE {id_column} = %s;
        """
        params = (resumo, palavras, ano, fonte, identificador_local)
    else:
        sql = f"""
          UPDATE {schema}.{table}
          SET
            descricao_tabela = CASE
              WHEN descricao_tabela IS NULL OR btrim(descricao_tabela) = '' THEN COALESCE(%s, descricao_tabela)
              ELSE descricao_tabela
            END,
            palavras_chave = CASE
              WHEN palavras_chave IS NULL OR btrim(palavras_chave) = '' THEN COALESCE(%s, palavras_chave)
              ELSE palavras_chave
            END,
            ano_elaboracao = CASE
              WHEN ano_elaboracao IS NULL THEN COALESCE(%s, ano_elaboracao)
              ELSE ano_elaboracao
            END,
            fonte_dados = CASE
              WHEN fonte_dados IS NULL OR btrim(fonte_dados) = '' THEN COALESCE(%s, fonte_dados)
              ELSE fonte_dados
            END,
            updated_at = NOW()
          WHERE {id_column} = %s;
        """
        params = (resumo, palavras, ano, fonte, identificador_local)

    with conn.cursor() as cur:
        cur.execute(sql, params)
        return cur.rowcount > 0


# =========================
# Step runner
# =========================

def run_step2(
    *,
    db: Dict[str, Any],
    endpoints: Dict[str, Any],
    timeout_secs: int,
    schema: str,
    table: str,
    id_column: str,
    force: bool,
    prefix: Optional[str],
    limit: Optional[int],
) -> int:
    conn = _get_conn(db)
    try:
        conn.autocommit = False

        ids = fetch_all_identificadores(conn, schema, table, id_column, prefix, limit)
        print(f"[Step2] Identificadores no BD: {len(ids)} (schema={schema}, table={table})")

        updated = 0
        remote_fail = 0
        local_miss = 0
        used_gestorapi = 0
        used_portal = 0
        errors: List[str] = []

        for ident in ids:
            ident = (ident or "").strip().lower()
            if not ident:
                continue

            txt, err, source = fetch_metadata_with_fallback(ident, endpoints, timeout_secs)
            if txt is None:
                remote_fail += 1
                errors.append(f"{ident} | {err}")
                continue

            if source == "gestorapi":
                used_gestorapi += 1
            elif source == "portal":
                used_portal += 1

            # IMPORTANTE: repara encoding SEM achatar linhas
            txt_fixed = repair_text_preserve_lines(txt)

            meta = parse_metadata(txt_fixed)

            # Normaliza cada campo separadamente
            resumo = normalize_field(meta.get("resumo") or "") or None
            palavras = normalize_field(meta.get("palavras_chave") or "") or None
            ano = parse_year(meta.get("data_elaboracao"))
            fonte = normalize_field(meta.get("fonte_dados") or "") or None

            ok = update_datasource(
                conn,
                schema=schema,
                table=table,
                id_column=id_column,
                identificador_local=ident,
                resumo=resumo,
                palavras=palavras,
                ano=ano,
                fonte=fonte,
                force=force,
            )
            if ok:
                updated += 1
            else:
                local_miss += 1

        conn.commit()

        print(f"[Step2] Atualizados: {updated}")
        print(f"[Step2] Sucesso via gestorapi: {used_gestorapi}")
        print(f"[Step2] Sucesso via portal: {used_portal}")
        print(f"[Step2] Falhas remotas (ambos endpoints): {remote_fail}")
        print(f"[Step2] Identificadores não encontrados no BD (inesperado): {local_miss}")

        if errors:
            print("[Step2] Exemplos de falhas (até 30):")
            for line in errors[:30]:
                print(f"[Step2] FAIL: {line}")
            if len(errors) > 30:
                print(f"[Step2] ... ({len(errors) - 30} falhas adicionais)")

        return 0

    except Exception as e:
        conn.rollback()
        print(f"[Step2] ERRO: {e}", file=sys.stderr)
        return 1
    finally:
        conn.close()


# =========================
# CLI
# =========================

def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="datasource_step2 (standalone, config hardcoded)")
    p.add_argument("--force", action="store_true")
    p.add_argument("--prefix", type=str, default=None)
    p.add_argument("--limit", type=int, default=None)
    p.add_argument("--timeout", type=int, default=None)

    p.add_argument("--schema", type=str, default=None)
    p.add_argument("--table", type=str, default=None)
    p.add_argument("--id-column", type=str, default=None)

    p.add_argument("--db-host", type=str, default=None)
    p.add_argument("--db-port", type=int, default=None)
    p.add_argument("--db-user", type=str, default=None)
    p.add_argument("--db-password", type=str, default=None)
    p.add_argument("--db-name", type=str, default=None)

    return p.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv)

    db = dict(DEFAULT_DB)
    if args.db_host is not None:
        db["host"] = args.db_host
    if args.db_port is not None:
        db["port"] = int(args.db_port)
    if args.db_user is not None:
        db["user"] = args.db_user
    if args.db_password is not None:
        db["password"] = args.db_password
    if args.db_name is not None:
        db["dbname"] = args.db_name

    timeout_secs = int(args.timeout) if args.timeout is not None else int(DEFAULT_HTTP_TIMEOUT_SECS)
    schema = args.schema or DEFAULT_TARGET["schema"]
    table = args.table or DEFAULT_TARGET["table"]
    id_column = args.id_column or DEFAULT_TARGET["id_column"]

    return run_step2(
        db=db,
        endpoints=DEFAULT_ENDPOINTS,
        timeout_secs=timeout_secs,
        schema=schema,
        table=table,
        id_column=id_column,
        force=bool(True),
        prefix=args.prefix,
        limit=args.limit,
    )


if __name__ == "__main__":
    raise SystemExit(main())
