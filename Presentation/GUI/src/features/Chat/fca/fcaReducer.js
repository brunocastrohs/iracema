// src/features/Chat/fca/fcaReducer.js

import { makeInitialFcaDraft, DEFAULT_LIMIT } from "./fcaDraftFactory";

function uniq(arr) {
  return [...new Set((arr || []).map((x) => String(x).trim()).filter(Boolean))];
}

function normalizeCols(cols) {
  return uniq(cols).map((c) => String(c));
}

function asSelectColumn(name) {
  const n = String(name || "").trim();
  if (!n) return null;
  return { type: "column", name: n, alias: n };
}

function keepValidOrderBy(list) {
  return (list || [])
    .map((x) => ({
      expr: String(x?.expr || "").trim(),
      dir: (String(x?.dir || "asc").toLowerCase() === "desc" ? "desc" : "asc"),
    }))
    .filter((x) => x.expr);
}

export function applyFcaCommand(draft, cmd) {
  
  const d = draft || makeInitialFcaDraft();

  if (!cmd || !cmd.kind) return d;

  switch (cmd.kind) {
    case "RESET_DRAFT":
      return makeInitialFcaDraft();

    case "SET_SELECT_ALL":
      return {
        ...d,
        _selectAll: Boolean(cmd.value),
        // se marcou selectAll, limpamos select específico
        select: Boolean(cmd.value) ? [] : d.select,
      };

    case "SET_COLUMNS": {
      const cols = normalizeCols(cmd.columns || []);
      const select = cols.map(asSelectColumn).filter(Boolean);
      return { ...d, _selectAll: false, select };
    }

    case "ADD_COLUMNS": {
      const cols = normalizeCols(cmd.columns || []);
      const currentNames = new Set((d.select || []).map((s) => s?.type === "column" ? s.name : null).filter(Boolean));
      const toAdd = cols.filter((c) => !currentNames.has(c)).map(asSelectColumn).filter(Boolean);
      return { ...d, _selectAll: false, select: [...(d.select || []), ...toAdd] };
    }

    case "REMOVE_COLUMNS": {
      const cols = new Set(normalizeCols(cmd.columns || []));
      const next = (d.select || []).filter((s) => {
        if (s?.type !== "column") return true;
        return !cols.has(String(s.name));
      });
      return { ...d, _selectAll: false, select: next };
    }

    case "CLEAR_COLUMNS":
      return { ...d, _selectAll: false, select: [] };

    case "ADD_WHERE": {
      const w = cmd.where;
      if (!w?.column || !w?.op) return d;
      const next = [...(d.where || []), { column: w.column, op: w.op, value: w.value }];
      return { ...d, where: next };
    }

    case "CLEAR_WHERE":
      return { ...d, where: [] };

    case "SET_GROUP_BY": {
      const cols = normalizeCols(cmd.columns || []);
      return { ...d, group_by: cols };
    }

    case "CLEAR_GROUP_BY":
      return { ...d, group_by: [] };

    case "SET_ORDER_BY":
      return { ...d, order_by: keepValidOrderBy(cmd.orderBy || []) };

    case "CLEAR_ORDER_BY":
      return { ...d, order_by: [] };

    case "SET_LIMIT": {
      const n = Number(cmd.value);
      if (!Number.isFinite(n) || n <= 0) return d;
      return { ...d, limit: Math.min(10000, Math.floor(n)) };
    }

    case "SET_OFFSET": {
      const n = Number(cmd.value);
      if (!Number.isFinite(n) || n < 0) return d;
      return { ...d, offset: Math.floor(n) };
    }

    default:
      return d;
  }
}

/**
 * Utilidade: checa se draft “está pronto” para executar.
 * Regra: precisa ter selectAll OU ao menos 1 coluna OU ter agregação (se você adicionar agg depois).
 */
export function validateFcaDraft(draft) {
  const d = draft || {};
  const hasSelectAll = Boolean(d._selectAll);
  const hasSelect = Array.isArray(d.select) && d.select.length > 0;

  if (!hasSelectAll && !hasSelect) {
    return { ok: false, message: "Você ainda não escolheu colunas. Use: 'todas as colunas' ou 'colunas: a,b,c'." };
  }

  // limit default
  const limit = d.limit ?? DEFAULT_LIMIT;
  if (!Number.isFinite(limit) || limit <= 0) {
    return { ok: false, message: "O limite está inválido. Use: 'limite: 20'." };
  }

  return { ok: true };
}
