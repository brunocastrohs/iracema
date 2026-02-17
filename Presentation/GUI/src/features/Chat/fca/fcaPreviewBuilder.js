// src/features/Chat/fca/fcaPreviewBuilder.js

function qIdent(s) {
  // simples: não coloca aspas duplas, só retorna como veio
  // (se você quiser, pode aprimorar com quoting seguro)
  return String(s || "").trim();
}

function formatValue(v) {
  if (Array.isArray(v)) return `(${v.map(formatValue).join(", ")})`;
  if (v === null) return "NULL";
  if (typeof v === "boolean") return v ? "TRUE" : "FALSE";
  if (typeof v === "number") return String(v);
  const s = String(v);
  // se já parece um padrão like %x% ou texto, quote
  if (s.includes("%")) return `'${s.replace(/'/g, "''")}'`;
  return `'${s.replace(/'/g, "''")}'`;
}

function buildSelect(select, selectAll) {
  if (selectAll) return "*";
  if (!Array.isArray(select) || !select.length) return "(nenhuma coluna)";

  return select
    .map((s) => {
      if (s?.type === "column") {
        const name = qIdent(s.name);
        const alias = s.alias ? qIdent(s.alias) : null;
        return alias && alias !== name ? `${name} AS ${alias}` : name;
      }
      if (s?.type === "agg") {
        const agg = String(s.agg || "").toUpperCase();
        const col = s.column ? qIdent(s.column) : "*";
        const alias = s.alias ? qIdent(s.alias) : null;
        const expr = `${agg}(${col})`;
        return alias ? `${expr} AS ${alias}` : expr;
      }
      return null;
    })
    .filter(Boolean)
    .join(", ");
}

function buildWhere(where) {
  if (!Array.isArray(where) || !where.length) return "";
  const parts = where.map((w) => {
    const col = qIdent(w.column);
    const op = String(w.op || "").toUpperCase();
    if (op === "IN") return `${col} IN ${formatValue(w.value)}`;
    return `${col} ${op} ${formatValue(w.value)}`;
  });
  return `WHERE ${parts.join(" AND ")}`;
}

function buildGroupBy(groupBy) {
  if (!Array.isArray(groupBy) || !groupBy.length) return "";
  return `GROUP BY ${groupBy.map(qIdent).join(", ")}`;
}

function buildOrderBy(orderBy) {
  if (!Array.isArray(orderBy) || !orderBy.length) return "";
  const parts = orderBy
    .map((o) => {
      const expr = qIdent(o.expr);
      const dir = String(o.dir || "asc").toUpperCase() === "DESC" ? "DESC" : "ASC";
      return `${expr} ${dir}`;
    })
    .filter(Boolean);
  return parts.length ? `ORDER BY ${parts.join(", ")}` : "";
}

export function buildFcaPreviewText({ table_identifier, fca }) {
  const t = qIdent(table_identifier);
  const d = fca || {};

  const selectAll = Boolean(d._selectAll);
  const selectSql = buildSelect(d.select, selectAll);
  const whereSql = buildWhere(d.where);
  const groupSql = buildGroupBy(d.group_by);
  const orderSql = buildOrderBy(d.order_by);

  const limit = d.limit ?? null;
  const offset = d.offset ?? null;

  const limitSql = Number.isFinite(limit) && limit > 0 ? `LIMIT ${Math.floor(limit)}` : "";
  const offsetSql = Number.isFinite(offset) && offset >= 0 ? `OFFSET ${Math.floor(offset)}` : "";

  const lines = [
    `SELECT ${selectSql}`,
    `FROM ${t}`,
    whereSql,
    groupSql,
    orderSql,
    limitSql,
    offsetSql,
  ].filter(Boolean);

  return lines.join("\n");
}
