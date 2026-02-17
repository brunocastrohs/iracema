// src/features/Chat/fca/fcaParser.js

function norm(s) {
  return String(s || "")
    .trim()
    .normalize("NFD")
    .replace(/\p{Diacritic}/gu, "")
    .toLowerCase();
}

function splitList(s) {
  return String(s || "")
    .split(/[;,|]/g)
    .map((x) => x.trim())
    .filter(Boolean);
}

function stripQuotes(v) {
  const t = String(v ?? "").trim();
  if ((t.startsWith('"') && t.endsWith('"')) || (t.startsWith("'") && t.endsWith("'"))) {
    return t.slice(1, -1);
  }
  return t;
}

function parseScalar(raw) {
  const v = stripQuotes(raw);
  if (v === "") return "";

  // boolean
  if (/^(true|false)$/i.test(v)) return v.toLowerCase() === "true";

  // null
  if (/^null$/i.test(v)) return null;

  // number
  const n = Number(v);
  if (!Number.isNaN(n) && /^-?\d+(\.\d+)?$/.test(v)) return n;

  return v;
}

function parseInList(rawInside) {
  // ex: (1,2,3) OR "a,b,c"
  const inner = rawInside.trim().replace(/^\(/, "").replace(/\)$/, "");
  return splitList(inner).map(parseScalar);
}

function parseWhereExpr(raw) {
  // formatos aceitos:
  //  col op value
  //  col IN (a,b,c)
  //  col LIKE %x%
  //  col ILIKE %x%
  const s = String(raw || "").trim();

  // IN (...)
  let m = s.match(/^([a-zA-Z_][\w]*)\s+(IN)\s+(\(.+\))$/i);
  if (m) {
    return { column: m[1], op: "IN", value: parseInList(m[3]) };
  }

  // op simples: = != > >= < <= LIKE ILIKE
  m = s.match(/^([a-zA-Z_][\w]*)\s*(=|!=|>=|>|<=|<|LIKE|ILIKE)\s*(.+)$/i);
  if (m) {
    const column = m[1];
    const op = m[2].toUpperCase();
    const valueRaw = m[3].trim();
    return { column, op, value: parseScalar(valueRaw) };
  }

  return null;
}

function parseOrderExpr(raw) {
  // "col desc" | "col asc" | "col"
  const s = String(raw || "").trim();
  const m = s.match(/^([a-zA-Z_][\w]*)(\s+(asc|desc))?$/i);
  if (!m) return null;
  return { expr: m[1], dir: (m[3] || "asc").toLowerCase() };
}

export function parseFcaBuilderText(rawText) {
  const original = String(rawText ?? "").trim();
  const t = norm(original);

  if (!t) return { kind: "UNKNOWN", raw: original };

  // reset / limpar tudo
  if (/\b(reset(ar)?|recomecar|limpar consulta|nova consulta)\b/.test(t)) {
    return { kind: "RESET_DRAFT" };
  }

  // preview
  if (/\b(preview|pre-?via|mostrar consulta|ver consulta|mostrar fca|ver fca)\b/.test(t)) {
    return { kind: "PREVIEW" };
  }

  // executar
  if (/\b(executar|rodar|consultar|buscar dados|enviar|ok pode ir)\b/.test(t)) {
    return { kind: "EXECUTE" };
  }

  // select all
  if (/\b(todas as colunas|tudo|selecionar tudo|todas)\b/.test(t)) {
    return { kind: "SET_SELECT_ALL", value: true };
  }

  // columns:
  // "colunas: a,b,c" | "selecionar colunas: a,b,c"
  let m =
    original.match(/^(colunas|selecionar colunas)\s*[:\-]\s*(.+)$/i) ||
    original.match(/^select\s*[:\-]\s*(.+)$/i);
  if (m) {
    const listStr = m[2] ?? m[1];
    const cols = splitList(listStr);
    return { kind: "SET_COLUMNS", columns: cols };
  }

  // add columns
  m = original.match(/^(adicionar colunas|add colunas|colunas)\s*[:\-]\s*(.+)$/i);
  if (m) {
    return { kind: "ADD_COLUMNS", columns: splitList(m[2]) };
  }

  // remove columns
  m = original.match(/^(remover colunas|del colunas|-colunas)\s*[:\-]\s*(.+)$/i);
  if (m) {
    return { kind: "REMOVE_COLUMNS", columns: splitList(m[2]) };
  }

  // clear columns
  if (/\b(limpar colunas|remover todas as colunas)\b/.test(t)) {
    return { kind: "CLEAR_COLUMNS" };
  }

  // filter:
  // "filtro: area > 10" | "where: ..."
  m = original.match(/^(filtro|filtrar|where)\s*[:\-]\s*(.+)$/i);
  if (m) {
    const expr = parseWhereExpr(m[2]);
    if (!expr) return { kind: "UNKNOWN", raw: original, error: "Filtro inválido. Ex: filtro: area_km2 > 10" };
    return { kind: "ADD_WHERE", where: expr };
  }

  // clear filters
  if (/\b(limpar filtros|remover filtros|sem filtro)\b/.test(t)) {
    return { kind: "CLEAR_WHERE" };
  }

  // group by
  m = original.match(/^(agrupar por|group by)\s*[:\-]\s*(.+)$/i);
  if (m) {
    return { kind: "SET_GROUP_BY", columns: splitList(m[2]) };
  }

  if (/\b(limpar grupo|limpar agrupamento|sem grupo)\b/.test(t)) {
    return { kind: "CLEAR_GROUP_BY" };
  }

  // order by
  m = original.match(/^(ordenar por|order by)\s*[:\-]\s*(.+)$/i);
  if (m) {
    // aceita "a desc, b asc"
    const parts = splitList(m[2]);
    const parsed = parts.map(parseOrderExpr).filter(Boolean);
    if (!parsed.length) return { kind: "UNKNOWN", raw: original, error: "Ordem inválida. Ex: ordenar por: area_km2 desc" };
    return { kind: "SET_ORDER_BY", orderBy: parsed };
  }

  if (/\b(limpar ordem|sem ordem)\b/.test(t)) {
    return { kind: "CLEAR_ORDER_BY" };
  }

  // limit
  m = original.match(/^(limite|limit)\s*[:\-]\s*(\d+)$/i);
  if (m) return { kind: "SET_LIMIT", value: parseInt(m[2], 10) };

  // offset
  m = original.match(/^(offset)\s*[:\-]\s*(\d+)$/i);
  if (m) return { kind: "SET_OFFSET", value: parseInt(m[2], 10) };

  // explain on/off (opcional)
  if (/\b(explicar|explain)\b/.test(t) && /\b(sim|true|on|ligar|ativar)\b/.test(t)) {
    return { kind: "SET_EXPLAIN", value: true };
  }
  if (/\b(explicar|explain)\b/.test(t) && /\b(nao|false|off|desligar|desativar)\b/.test(t)) {
    return { kind: "SET_EXPLAIN", value: false };
  }

  // se estiver em fca_builder e cair aqui, é UNKNOWN (o Chat decide como responder)
  return { kind: "UNKNOWN", raw: original };
}
