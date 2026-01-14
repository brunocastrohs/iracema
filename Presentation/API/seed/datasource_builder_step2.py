#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Etapa 2 — Atualizar public.datasources a partir de metadados TXT do PEDEA

Fluxo de busca (fallback):
1) Tenta endpoint gestorapi:
   https://pedea.sema.ce.gov.br/gestorapi/v1/arquivotxt/<identificador_com_replace__ce__por__CE_>_metadados.txt

2) Se falhar (404/5xx/timeout/etc), tenta endpoint portal:
   https://pedea.sema.ce.gov.br/portal/metadata/<identificador_sem__ce__com_uppercase>_metadados.txt

3) Se ambos falharem, registra falha e segue para o próximo identificador (NUNCA aborta por falha remota).

Extrai campos do TXT:
- 02.Resumo + 03.Palavras-chave -> descricao_tabela
- 04.Data de elaboração -> ano_elaboracao (ano)
- 06.Fonte dos Dados -> fonte_dados

Regra de consistência:
- identificador_tabela no BD é sempre lower case (step1 garante).
"""

import re
import sys
from typing import Optional, Dict, List, Tuple

import requests
import psycopg2


DB = {
    "host": "localhost",
    "port": 5435,
    "dbname": "iracema",
    "user": "postgres",
    "password": "002100",
}

# Endpoint 1 (gestorapi)
ENDPOINT_TXT_BASE = "https://pedea.sema.ce.gov.br/gestorapi/v1/arquivotxt/"

# Endpoint 2 (portal)
ENDPOINT_PORTAL_METADATA_BASE = "https://pedea.sema.ce.gov.br/portal/metadata/"

TIMEOUT_SECS = 1
FILE_SUFFIX = "_metadados.txt"

FIELD_RE = re.compile(r"^\s*(\d{2})\s*\.\s*([^:]+)\s*:\s*(.*)\s*$")
YEAR_RE = re.compile(r"(\d{4})")

CODE_LINE_RE = re.compile(r"^\s*(\d{2})\s*\.\s*$")                 # "02."
INLINE_RE = re.compile(r"^\s*(\d{2})\s*\.\s*[^:]+:\s*(.*)\s*$")    # "02.Resumo: valor"
LABEL_RE = re.compile(r"^\s*([^:]{2,80})\s*:\s*(.*)\s*$")          # "Resumo: valor" ou "Fonte dos Dados: ..."



def latin1_to_utf8_clean(text: str) -> str:
    """
    Normaliza texto 'sujo' (Latin-1 / Windows-1252 / mojibake) para Unicode estável.
    """
    if not text:
        return ""

    replacements = {
        "": '"',
        "": '"',
        "“": '"',
        "”": '"',
        "": "-",
        "–": "-",
        "": "-",
        "—": "-",
        "": "'",
        "‘": "'",
        "’": "'",
        "\u00a0": " ",  # NBSP
    }
    for bad, good in replacements.items():
        text = text.replace(bad, good)

    # tenta reparar casos de dupla conversão típica (Ã§ etc.)
    try:
        repaired = text.encode("latin-1", errors="ignore").decode("utf-8", errors="ignore")
        if repaired and (repaired.count("�") <= text.count("�")):
            # só substitui se parecer melhor/igual
            text = repaired
    except Exception:
        pass

    # compacta whitespace
    return " ".join(text.strip().split())


def parse_year(text: Optional[str]) -> Optional[int]:
    if not text:
        return None
    text = (text)
    m = YEAR_RE.search(text)
    if not m:
        return None
    try:
        year = int(m.group(1))
        if 1900 <= year <= 2100:
            return year
        return None
    except ValueError:
        return None


def parse_metadata(content: str) -> Dict[str, str]:
    """
    Parser tolerante a:
    - '02.Resumo: ...' (inline)
    - '02.' + 'Resumo:' + texto em várias linhas

    Retorna dict com chaves "02", "03", "04", "06" quando encontradas.
    """
    data: Dict[str, str] = {}

    current_code: Optional[str] = None
    collecting = False
    buffer: List[str] = []
    label_seen_for_code = False  # indica que já vimos a linha "Resumo:" / "Palavras-chave:" etc.

    def flush():
        nonlocal buffer, current_code, collecting, label_seen_for_code
        if current_code and buffer:
            value = "\n".join([ln.rstrip() for ln in buffer]).strip()
            if value:
                data[current_code] = value
        buffer = []
        collecting = False
        label_seen_for_code = False

    lines = content.splitlines()

    for raw in lines:
        line = raw.strip()

        # ignora linhas vazias, mas se estiver coletando, preserva como quebra lógica
        if not line:
            if collecting:
                buffer.append("")  # mantém parágrafo
            continue

        # Caso 1: linha inline "02.Resumo: valor"
        m_inline = INLINE_RE.match(line)
        if m_inline:
            # antes de sobrescrever, flush do anterior
            flush()
            code = m_inline.group(1)
            value = m_inline.group(2).strip()
            if value:
                data[code] = value
            current_code = None
            continue

        # Caso 2: só o código "02."
        m_code = CODE_LINE_RE.match(line)
        if m_code:
            # começa novo campo -> flush do anterior
            flush()
            current_code = m_code.group(1)
            collecting = True
            continue

        # Se estamos em um código do tipo "02." e ainda não vimos "Resumo:"
        # aceita "Resumo:" / "Palavras-chave:" / etc.
        if collecting and current_code:
            m_label = LABEL_RE.match(line)
            if m_label and not label_seen_for_code:
                label_seen_for_code = True
                # se já tiver valor na mesma linha após ':', entra no buffer
                after = (m_label.group(2) or "").strip()
                if after:
                    buffer.append(after)
                continue

            # Caso 3: conteúdo em múltiplas linhas (após o label)
            if label_seen_for_code:
                buffer.append(raw.strip())
                continue

        # Se chegou aqui, é uma linha que não conseguimos associar.
        # (ignore silenciosamente para não quebrar o parsing)
        continue

    # flush final
    flush()

    return data

def fetch_all_identificadores(conn) -> List[str]:
    sql = """
      SELECT identificador_tabela
      FROM public.datasources
      WHERE identificador_tabela IS NOT NULL
      ORDER BY identificador_tabela;
    """
    with conn.cursor() as cur:
        cur.execute(sql)
        return [r[0] for r in cur.fetchall()]


def _http_get_text(url: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Retorna (text, err). Nunca levanta exceção para falhas HTTP.
    """
    try:
        r = requests.get(url, timeout=TIMEOUT_SECS)
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


def fetch_metadata_txt_portal(identificador_local: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Endpoint gestorapi (primeira tentativa):
    https://pedea.sema.ce.gov.br/gestorapi/v1/arquivotxt/<identificador_com__ce__por__CE_>_metadados.txt

    Regra pedida originalmente:
    antes de chamar, aplicar replace("_ce_", "_CE_").
    """
    remote_id = identificador_local.replace("_ce_", "_CE_")
    url = f"{ENDPOINT_TXT_BASE}{remote_id}{FILE_SUFFIX}"
    return _http_get_text(url)


def fetch_metadata_txt_portal_pedea(identificador_local: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Endpoint portal (fallback):
    https://pedea.sema.ce.gov.br/portal/metadata/<identificador_lowercase>_metadados.txt

    IMPORTANTE:
    - resposta vem em Latin-1
    - decodificar manualmente para UTF-8
    """
    url = f"{ENDPOINT_PORTAL_METADATA_BASE}{identificador_local}{FILE_SUFFIX}"

    try:
        r = requests.get(url, timeout=TIMEOUT_SECS)
    except requests.exceptions.Timeout:
        return None, f"timeout: {url}"
    except requests.exceptions.RequestException as e:
        return None, f"request_exception: {url} | {e}"

    if r.status_code == 200:
        try:
            # 🔑 conversão explícita Latin-1 → Unicode (UTF-8 interno do Python)
            text = r.content.decode("latin-1")
            return text, None
        except Exception as e:
            return None, f"decode_latin1_error: {url} | {e}"

    if r.status_code == 404:
        return None, f"not_found_404: {url}"

    if 500 <= r.status_code <= 599:
        return None, f"server_error_{r.status_code}: {url}"

    return None, f"http_{r.status_code}: {url}"



def fetch_metadata_with_fallback(identificador_local: str) -> Tuple[Optional[str], Optional[str], str]:
    """
    Tenta primeiro gestorapi, depois portal. Retorna (txt, err, source).
    source ∈ {"gestorapi", "portal", "none"}
    """
    #print(identificador_local)
    #print("Tentando fetch 1")
    txt, err = fetch_metadata_txt_portal(identificador_local)
    if txt is not None:
        #print("fetch 1 ok!")
        return txt, None, "gestorapi"

    #print("Tentando fetch 2")
    txt2, err2 = fetch_metadata_txt_portal_pedea(identificador_local)
    if txt2 is not None:
        #print("fetch 2 ok!")
        return txt2, None, "portal"
    
    #print("fetch nao ok!")
    # falhou em ambos
    combined_err = f"gestorapi_fail=({err}); portal_fail=({err2})"
    return None, combined_err, "none"


def update_datasource(
    conn,
    identificador_local: str,
    resumo: Optional[str],
    palavras: Optional[str],
    ano: Optional[int],
    fonte: Optional[str],
) -> bool:
    sql = """
      UPDATE public.datasources
      SET
        descricao_tabela = COALESCE(%s, descricao_tabela),
        palavras_chave = COALESCE(%s, palavras_chave),
        ano_elaboracao = COALESCE(%s, ano_elaboracao),
        fonte_dados = COALESCE(%s, fonte_dados),
        updated_at = NOW()
      WHERE identificador_tabela = %s;
    """

    fonte_norm = fonte or "" if fonte else None

    with conn.cursor() as cur:
        cur.execute(sql, (resumo, palavras, ano, fonte_norm, identificador_local))
        return cur.rowcount > 0


def main() -> int:
    conn = psycopg2.connect(**DB)
    try:
        conn.autocommit = False

        ids = fetch_all_identificadores(conn)
        print(f"[Step2] Identificadores no BD: {len(ids)}")

        updated = 0
        remote_fail = 0
        local_miss = 0
        used_gestorapi = 0
        used_portal = 0

        errors: List[str] = []

        for ident in ids:
            # ident já está em lower case (padrão do step1)
            txt, err, source = fetch_metadata_with_fallback(ident)

            if txt is None:
                remote_fail += 1
                errors.append(f"{ident} | {err}")
                continue

            if source == "gestorapi":
                used_gestorapi += 1
            elif source == "portal":
                used_portal += 1

            meta = parse_metadata(txt)

            resumo = (meta.get("02") or "") 
            palavras = (meta.get("03") or "") 
            ano = parse_year(meta.get("04"))
            fonte = (meta.get("06") or "")

            ok = update_datasource(conn, ident, resumo, palavras, ano, fonte)
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
            print(f"[Step2] Exemplos de falhas (até 30):")
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


if __name__ == "__main__":
    raise SystemExit(main())
