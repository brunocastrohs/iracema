// src/features/Chat/nlu/intentEngine.js
import { normalizeLite, safeText } from "../helpers";
import { resolveTableByText } from "../helpers";

// -------------------- util --------------------
function hasAny(reList, text) {
  return reList.some((re) => re.test(text));
}

function extractYear(text) {
  const m = text.match(/\b(19\d{2}|20\d{2})\b/);
  return m?.[1] ?? null;
}

function extractPosition(text) {
  const t = normalizeLite(text);
  if (/\bprimeir[ao]\b/.test(t)) return 1;
  if (/\bsegund[ao]\b/.test(t)) return 2;
  if (/\bterceir[ao]\b/.test(t)) return 3;
  const m = t.match(/\b(\d+)\s*(a|ª|o|º)?\b/);
  const n = m ? parseInt(m[1], 10) : NaN;
  return Number.isFinite(n) ? n : null;
}

function extractSourceHint(text) {
  const m = safeText(text).match(/fonte\s*[:\-]\s*(.+)$/i);
  return m?.[1]?.trim() ?? null;
}

function extractCategoryHint(text) {
  const m = safeText(text).match(/categor(ia|ía)\s*[:\-]\s*(.+)$/i);
  return m?.[2]?.trim() ?? null;
}

function isDeicticThis(text) {
  const t = normalizeLite(text);
  return (
    t === "essa" ||
    t === "essa tabela" ||
    t === "essa camada" ||
    t === "esta" ||
    t === "esta tabela" ||
    t === "esta camada" ||
    t === "a tabela" ||
    t === "a camada" ||
    /\bdessa\b/.test(t) ||
    /\bnessa\b/.test(t)
  );
}

function pickFromLastSuggestions({ lastSuggestions = [], year, sourceHint, position }) {
  if (!Array.isArray(lastSuggestions) || lastSuggestions.length === 0) return null;

  if (position && position >= 1 && position <= lastSuggestions.length) {
    return lastSuggestions[position - 1];
  }

  let pool = lastSuggestions;

  if (year) pool = pool.filter((s) => String(s.year ?? "") === String(year));

  if (sourceHint) {
    const sh = normalizeLite(sourceHint);
    pool = pool.filter((s) => normalizeLite(s.source || "").includes(sh));
  }

  return pool[0] ?? lastSuggestions[0] ?? null;
}

// -------------------- parsing --------------------
function makeParsed(rawText) {
  const text = safeText(rawText);
  const t = normalizeLite(text);

  const year = extractYear(t);
  const position = extractPosition(t);
  const sourceHint = extractSourceHint(text);
  const categoryHint = extractCategoryHint(text);

  return { text, t, year, position, sourceHint, categoryHint };
}

function baseEntities(p) {
  return {
    year: p.year,
    sourceHint: p.sourceHint,
    position: p.position,
    categoryHint: p.categoryHint,
  };
}

// -------------------- handlers (um por intent) --------------------
function tryReset(p) {
  if (hasAny([/\b(recome(c|ç)ar|resetar|limpar)\b/], p.t)) {
    return { intent: "RESET", confidence: 0.99, entities: {} };
  }
  return null;
}

function trySwitchTable(p) {
  if (
    hasAny(
      [
        /\b(trocar|mudar|alterar)\b.*\b(tabela|camada|fonte)\b/,
        /\b(outra|outras)\b.*\b(tabela|camada|fonte)\b/,
        /^\btrocar tabela\b$/,
      ],
      p.t
    )
  ) {
    return { intent: "SWITCH_TABLE", confidence: 0.95, entities: {} };
  }
  return null;
}

function tryHelp(p) {
  if (hasAny([/\b(ajuda|como usar|o que você faz|instru(c|ç)(ões|ao))\b/], p.t)) {
    return { intent: "HELP", confidence: 0.85, entities: {} };
  }
  return null;
}

function tryDetails(p) {
  if (
    hasAny(
      [
        /\bdetalhar\b/,
        /\bdetalhes\b/,
        /\bcolunas\b/,
        /\b(campos|schema|descri(c|ç)(ão|ao))\b/,
        /\bquais\s+s(ã|a)o\s+as\s+colunas\b/,
        /\bmostra(r)?\s+(as\s+)?colunas\b/,
      ],
      p.t
    )
  ) {
    return {
      intent: "DETAILS",
      confidence: 0.9,
      entities: baseEntities(p),
    };
  }
  return null;
}

function trySelect(p) {
  if (
    hasAny(
      [
        /^\b(usar|use|selecionar|seleciona|confirmar|confirma)\b/,
        /\b(vai com|vamos com)\b/,
      ],
      p.t
    )
  ) {
    return {
      intent: "SELECT",
      confidence: 0.9,
      entities: { ...baseEntities(p), selectionText: p.text },
    };
  }
  return null;
}

function tryRefine(p) {
  const hasRefineWords = hasAny([/\bano\b/, /\bcategor(ia|ía)\b/, /\bfonte\b/], p.t);
  const hasAnyEntity = Boolean(p.year || p.sourceHint || p.categoryHint);

  if (hasRefineWords && hasAnyEntity) {
    return {
      intent: "REFINE",
      confidence: 0.7,
      entities: { year: p.year, sourceHint: p.sourceHint, categoryHint: p.categoryHint },
    };
  }
  return null;
}

function trySelectImplicit(p, ctx) {
  // contextual: "essa", "a segunda", "a de 2022", "COBIO" etc.
  if (isDeicticThis(p.text) || p.position || p.year || p.sourceHint) {
    return {
      intent: "SELECT_IMPLICIT",
      confidence: 0.6,
      entities: baseEntities(p),
    };
  }
  return null;
}

function fallbackByMode(p, ctx) {
  if (ctx?.mode === "ask") {
    return { intent: "ASK_QUESTION", confidence: 0.8, entities: { question: p.text } };
  }
  return {
    intent: "CATALOG_SEARCH",
    confidence: 0.7,
    entities: { query: p.text, year: p.year, sourceHint: p.sourceHint, categoryHint: p.categoryHint },
  };
}

// -------------------- public API --------------------
export function interpretIntent(rawText, ctx) {
  const p = makeParsed(rawText);

  // ordem = do mais “forte” ao mais “fraco”
  const handlers = [
    tryReset,
    trySwitchTable,
    tryHelp,
    tryDetails,
    trySelect,
    tryRefine,
    (pp) => trySelectImplicit(pp, ctx),
  ];

  for (const h of handlers) {
    const r = h(p, ctx);
    if (r) return r;
  }

  return fallbackByMode(p, ctx);
}

// -------------------- target resolution (mantém igual) --------------------
export function resolveTargetTable({ rawText, docs, index, selectedTableId, lastSuggestions }) {
  const text = safeText(rawText);

  // 1) se o usuário colou id/título, usa resolveTableByText
  const r = resolveTableByText({ query: text, docs, index });
  if (r?.doc) return { kind: "doc", doc: r.doc, directContinue: r.directContinue };

  // 2) se tem tabela já selecionada e o texto for deíctico (“essa”), usa ela
  if (selectedTableId && isDeicticThis(text)) {
    const d = docs.find((x) => x.id === selectedTableId);
    if (d) return { kind: "doc", doc: d, directContinue: true };
  }

  // 3) tentar resolver por lastSuggestions
  const t = normalizeLite(text);
  const year = extractYear(t);
  const position = extractPosition(t);
  const sourceHint = extractSourceHint(text);

  const picked = pickFromLastSuggestions({ lastSuggestions, year, sourceHint, position });
  if (picked?.id) {
    const d = docs.find((x) => x.id === picked.id) || picked;
    return { kind: "doc", doc: d, directContinue: true };
  }

  return { kind: "none" };
}
