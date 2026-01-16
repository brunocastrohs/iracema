#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Step 3 — GeoServer (zcm): popular colunas_tabela (atributos) em public.datasources
e materializar tabela no schema zcm via WFS (DescribeFeatureType + GetFeature GeoJSON).

Fluxo por datasource:
1) DescribeFeatureType:
   {geoserverRoot}/{workspace}/ows?service=WFS&version=1.1.0&request=DescribeFeatureType&typeName={workspace}:{layer}

2) Atualiza public.datasources.colunas_tabela (JSONB) com lista de campos
   (name/type/is_geometry/nullable)

3) Se zcm.<layer> não existir:
   - cria schema zcm se necessário
   - cria tabela com colunas inferidas (+ geom como geometry)
   - baixa GeoJSON:
     https://pedea.sema.ce.gov.br/geoserver/wfs?service=WFS&version=1.0.0&request=GetFeature&typeName={layer}&outputFormat=application/json
   - insere features usando ST_GeomFromGeoJSON + ST_SetSRID (EPSG 4674)
"""

import json
import sys
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import requests
import psycopg2
from psycopg2 import sql


# =========================
# Config
# =========================

DB = {
    "host": "localhost",
    "port": 5435,
    "dbname": "iracema",
    "user": "postgres",
    "password": "002100",
}

geoWorkspace = "zcm"
geoserverRoot = "https://pedea.sema.ce.gov.br/geoserver"

DESCRIBE_URL = f"{geoserverRoot}/{geoWorkspace}/ows"
GETFEATURE_URL = f"{geoserverRoot}/wfs"  # conforme seu exemplo

TIMEOUT_SECS = 15
SLEEP_BETWEEN_CALLS = 0.05  # para não martelar o servidor


# EPSG fixo (se no futuro quiser, dá pra inferir do metadado)
SRID = 4674


# =========================
# Tipos auxiliares
# =========================

@dataclass
class FieldDef:
    name: str
    pg_type: str
    is_geometry: bool
    nullable: bool


# =========================
# Mapeamentos de tipos
# =========================

def map_xsd_to_pg(xsd_type: str) -> str:
    """
    Mapeia tipos XSD comuns do DescribeFeatureType para tipos Postgres.
    """
    t = (xsd_type or "").lower()

    if t.endswith(":string"):
        return "text"
    if t.endswith(":boolean"):
        return "boolean"
    if t.endswith(":int") or t.endswith(":integer"):
        return "integer"
    if t.endswith(":long"):
        return "bigint"
    if t.endswith(":short"):
        return "smallint"
    if t.endswith(":double") or t.endswith(":decimal") or t.endswith(":float"):
        return "double precision"
    if t.endswith(":date"):
        return "date"
    if t.endswith(":datetime"):
        return "timestamptz"

    # fallback seguro
    return "text"


def map_gml_geometry_to_pg(gml_type: str) -> Tuple[str, Optional[str]]:
    """
    Mapeia tipos GML do DescribeFeatureType para geometry(<Type>,SRID).

    Exemplo:
      gml:MultiSurfacePropertyType -> MultiPolygon
      gml:PointPropertyType -> Point
    """
    t = (gml_type or "").lower()

    # padrões comuns em GeoServer/WFS DescribeFeatureType
    if "points" in t or "pointpropertytype" in t:
        return f"geometry(Point,{SRID})", "Point"
    if "multisurface" in t or "multipolygon" in t or "surfaceproperty" in t:
        return f"geometry(MultiPolygon,{SRID})", "MultiPolygon"
    if "multicurve" in t or "multilinestring" in t or "curveproperty" in t:
        return f"geometry(MultiLineString,{SRID})", "MultiLineString"
    if "polygon" in t:
        return f"geometry(Polygon,{SRID})", "Polygon"
    if "linestring" in t or "line" in t:
        return f"geometry(LineString,{SRID})", "LineString"

    # fallback genérico
    return f"geometry(Geometry,{SRID})", "Geometry"


# =========================
# HTTP
# =========================

def http_get(url: str, params: Dict[str, Any], want: str = "text") -> Tuple[Optional[Any], Optional[str]]:
    try:
        r = requests.get(url, params=params, timeout=TIMEOUT_SECS)
    except requests.exceptions.Timeout:
        return None, f"timeout: {url}"
    except requests.exceptions.RequestException as e:
        return None, f"request_exception: {url} | {e}"

    if r.status_code != 200:
        return None, f"http_{r.status_code}: {r.url}"

    if want == "json":
        try:
            return r.json(), None
        except Exception as e:
            return None, f"json_parse_error: {r.url} | {e}"

    return r.text, None


def fetch_describe_feature_type(layer: str) -> Tuple[Optional[str], Optional[str]]:
    params = {
        "service": "WFS",
        "version": "1.1.0",
        "request": "DescribeFeatureType",
        "typeName": f"{geoWorkspace}:{layer}",
    }
    return http_get(DESCRIBE_URL, params=params, want="text")


def fetch_geojson(layer: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    params = {
        "service": "WFS",
        "version": "1.0.0",
        "request": "GetFeature",
        "typeName": layer,  # conforme seu exemplo (sem workspace)
        "outputFormat": "application/json",
    }
    return http_get(GETFEATURE_URL, params=params, want="json")


# =========================
# Parse DescribeFeatureType
# =========================

def parse_describe_feature_type_xml(xml_text: str) -> List[FieldDef]:
    """
    Extrai campos do XSD. Procura por xsd:element dentro do complexType do layer.
    """
    # Namespaces típicos do XSD
    ns = {
        "xsd": "http://www.w3.org/2001/XMLSchema",
    }

    root = ET.fromstring(xml_text)

    fields: List[FieldDef] = []

    # pega todos xsd:element do schema (pode ter imports, etc.)
    for el in root.findall(".//xsd:element", ns):
        name = el.attrib.get("name")
        xsd_type = el.attrib.get("type", "")
        nillable = (el.attrib.get("nillable", "true").lower() == "true")

        if not name:
            continue

        # geom costuma vir como gml:*PropertyType
        if xsd_type.lower().startswith("gml:"):
            pg_geom_type, _ = map_gml_geometry_to_pg(xsd_type)
            fields.append(FieldDef(name=name, pg_type=pg_geom_type, is_geometry=True, nullable=nillable))
        else:
            pg_type = map_xsd_to_pg(xsd_type)
            fields.append(FieldDef(name=name, pg_type=pg_type, is_geometry=False, nullable=nillable))

    # remove duplicatas por nome (se aparecer repetido)
    uniq: Dict[str, FieldDef] = {}
    for f in fields:
        uniq[f.name] = f
    return list(uniq.values())


def fields_to_jsonb(fields: List[FieldDef]) -> List[Dict[str, Any]]:
    """
    Formato sugerido para colunas_tabela (JSONB) no datasources.
    """
    out = []
    for f in fields:
        out.append({
            "name": f.name,
            "type": f.pg_type,
            "is_geometry": f.is_geometry,
            "nullable": f.nullable,
        })
    return out


# =========================
# DB helpers
# =========================

def ensure_postgis_and_schema(conn) -> None:
    with conn.cursor() as cur:
        cur.execute("CREATE EXTENSION IF NOT EXISTS postgis;")
        cur.execute("CREATE SCHEMA IF NOT EXISTS zcm;")


def fetch_all_datasources(conn) -> List[str]:
    """
    Retorna lista de identificador_tabela (lowercase) para processar.
    Você pode filtrar por is_ativo se quiser.
    """
    q = """
      SELECT identificador_tabela
      FROM public.datasources
      WHERE identificador_tabela IS NOT NULL
      ORDER BY identificador_tabela;
    """
    with conn.cursor() as cur:
        cur.execute(q)
        return [r[0] for r in cur.fetchall()]


def update_datasource_columns(conn, layer: str, cols_json: List[Dict[str, Any]]) -> None:
    q = """
      UPDATE public.datasources
      SET colunas_tabela = %s::jsonb,
          updated_at = NOW()
      WHERE identificador_tabela = %s;
    """
    with conn.cursor() as cur:
        cur.execute(q, (json.dumps(cols_json, ensure_ascii=False), layer))


def table_exists(conn, schema: str, table: str) -> bool:
    q = """
      SELECT EXISTS(
        SELECT 1
        FROM information_schema.tables
        WHERE table_schema = %s AND table_name = %s
      );
    """
    with conn.cursor() as cur:
        cur.execute(q, (schema, table))
        return bool(cur.fetchone()[0])


def create_table_from_fields(conn, schema: str, table: str, fields: List[FieldDef]) -> None:
    """
    Cria tabela zcm.<table> com colunas de acordo com o DescribeFeatureType.
    Se existir 'geom' com geometry(...), será criado como coluna geom.
    """
    # garante que geom venha por último (opcional, só estética)
    fields_sorted = sorted(fields, key=lambda f: (f.is_geometry is True, f.name))
    # mas se preferir geom no final, inverta:
    fields_sorted = sorted(fields, key=lambda f: (f.is_geometry, f.name))

    col_defs = []
    for f in fields_sorted:
        col_name = sql.Identifier(f.name)
        col_type = sql.SQL(f.pg_type)
        null_sql = sql.SQL("NULL") if f.nullable else sql.SQL("NOT NULL")
        col_defs.append(sql.SQL("{} {} {}").format(col_name, col_type, null_sql))

    create_stmt = sql.SQL("CREATE TABLE IF NOT EXISTS {}.{} ({});").format(
        sql.Identifier(schema),
        sql.Identifier(table),
        sql.SQL(", ").join(col_defs),
    )

    with conn.cursor() as cur:
        cur.execute(create_stmt)

    # índice espacial se houver geom
    geom_fields = [f for f in fields if f.is_geometry]
    if geom_fields:
        geom_col = geom_fields[0].name
        idx_stmt = sql.SQL("CREATE INDEX IF NOT EXISTS {} ON {}.{} USING GIST ({});").format(
            sql.Identifier(f"idx_{table}_{geom_col}_gist"),
            sql.Identifier(schema),
            sql.Identifier(table),
            sql.Identifier(geom_col),
        )
        with conn.cursor() as cur:
            cur.execute(idx_stmt)


def insert_geojson_features(conn, schema: str, table: str, fields: List[FieldDef], geojson: Dict[str, Any]) -> int:
    """
    Insere FeatureCollection no Postgres.
    - propriedades entram nas colunas não-geom (por nome)
    - geometry entra na coluna geom (ou outra geometria detectada) via ST_SetSRID(ST_GeomFromGeoJSON(...), SRID)
    """
    feats = geojson.get("features") or []
    if not feats:
        return 0

    # acha a coluna geom no schema
    geom_cols = [f.name for f in fields if f.is_geometry]
    geom_col = geom_cols[0] if geom_cols else None

    # colunas não geom em ordem estável
    prop_cols = [f.name for f in fields if not f.is_geometry]

    # Monta SQL de insert usando psycopg2.sql para escapar identificadores
    cols_all = prop_cols + ([geom_col] if geom_col else [])
    if not cols_all:
        return 0

    # placeholders:
    # - props: %s
    # - geom: ST_SetSRID(ST_GeomFromGeoJSON(%s), SRID)
    values_sql_parts = []
    for c in cols_all:
        if geom_col and c == geom_col:
            values_sql_parts.append(sql.SQL(f"ST_SetSRID(ST_GeomFromGeoJSON(%s), {SRID})"))
        else:
            values_sql_parts.append(sql.SQL("%s"))

    insert_stmt = sql.SQL("INSERT INTO {}.{} ({}) VALUES ({});").format(
        sql.Identifier(schema),
        sql.Identifier(table),
        sql.SQL(", ").join([sql.Identifier(c) for c in cols_all]),
        sql.SQL(", ").join(values_sql_parts),
    )

    inserted = 0
    with conn.cursor() as cur:
        for feat in feats:
            props = feat.get("properties") or {}
            geom_obj = feat.get("geometry")

            row = []
            for c in prop_cols:
                row.append(props.get(c))

            if geom_col:
                row.append(json.dumps(geom_obj) if geom_obj is not None else None)

            try:
                cur.execute(insert_stmt, row)
                inserted += 1
            except Exception:
                # Para não abortar o batch inteiro: loga e segue.
                # Se preferir abortar, remova o try/except.
                conn.rollback()
                conn.autocommit = False
                continue

    return inserted


# =========================
# Main
# =========================

def main() -> int:
    conn = psycopg2.connect(**DB)
    try:
        conn.autocommit = False
        ensure_postgis_and_schema(conn)
        conn.commit()

        layers = fetch_all_datasources(conn)
        print(f"[Step3] Datasources no BD: {len(layers)}")

        updated_cols = 0
        created_tables = 0
        inserted_total = 0
        describe_fail = 0
        geojson_fail = 0

        for layer in layers:
            # segurança: normaliza para lower case (padrão do step1)
            layer = (layer or "").strip().lower()
            if not layer:
                continue

            time.sleep(SLEEP_BETWEEN_CALLS)

            # 1) DescribeFeatureType
            xml_text, err = fetch_describe_feature_type(layer)
            if xml_text is None:
                describe_fail += 1
                print(f"[Step3] WARN describe fail: {layer} | {err}")
                continue

            try:
                fields = parse_describe_feature_type_xml(xml_text)
            except Exception as e:
                describe_fail += 1
                print(f"[Step3] WARN describe parse fail: {layer} | {e}")
                continue

            # 2) Atualiza colunas_tabela (JSONB) em datasources
            try:
                update_datasource_columns(conn, layer, fields_to_jsonb(fields))
                conn.commit()
                updated_cols += 1
            except Exception as e:
                conn.rollback()
                print(f"[Step3] WARN update colunas_tabela fail: {layer} | {e}")
                continue

            # 3) Se tabela não existe, cria e popula
            if table_exists(conn, "zcm", layer):
                continue

            try:
                create_table_from_fields(conn, "zcm", layer, fields)
                conn.commit()
                created_tables += 1
            except Exception as e:
                conn.rollback()
                print(f"[Step3] WARN create table fail: {layer} | {e}")
                continue

            # 4) Fetch GeoJSON e inserir
            time.sleep(SLEEP_BETWEEN_CALLS)
            geojson, err2 = fetch_geojson(layer)
            if geojson is None:
                geojson_fail += 1
                print(f"[Step3] WARN geojson fail: {layer} | {err2}")
                continue

            try:
                inserted = insert_geojson_features(conn, "zcm", layer, fields, geojson)
                conn.commit()
                inserted_total += inserted
            except Exception as e:
                conn.rollback()
                print(f"[Step3] WARN insert fail: {layer} | {e}")
                continue

        print(f"[Step3] colunas_tabela atualizadas: {updated_cols}")
        print(f"[Step3] tabelas criadas em zcm: {created_tables}")
        print(f"[Step3] features inseridas: {inserted_total}")
        print(f"[Step3] falhas describe: {describe_fail}")
        print(f"[Step3] falhas geojson: {geojson_fail}")

        return 0

    except Exception as e:
        conn.rollback()
        print(f"[Step3] ERRO CRÍTICO: {e}", file=sys.stderr)
        return 1
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
