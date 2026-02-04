// src/features/Chat/nlu/intentEngine.js
import { normalizeLite, safeText } from "../helpers";
import { resolveTableByText } from "../helpers";

// --- util ---
function hasAny(reList, text) {
  return reList.some((re) => re.test(text));
}

function extractYear(text) {
  const m = text.match(/\b(19\d{2}|20\d{2})\b/);
  return m?.[1] ?? null;
}

function extractPosition(text) {
  // "primeira", "segunda", "3a", "terceira"
  const t = normalizeLite(text);
  if (/\bprimeir[ao]\b/.test(t)) return 1;
  if (/\bsegund[ao]\b/.test(t)) return 2;
  if (/\bterceir[ao]\b/.test(t)) return 3;
  const m = t.match(/\b(\d+)\s*(a|ª|o|º)?\b/);
  const n = m ? parseInt(m[1], 10) : NaN;
  return Number.isFinite(n) ? n : null;
}

function extractSourceHint(text) {
  // bem simples: pega depois de "fonte:"
  const t = safeText(text);
  const m = t.match(/fonte\s*[:\-]\s*(.+)$/i);
  return m?.[1]?.trim() ?? null;
}

function extractCategoryHint(text) {
  // "categoria: X"
  const t = safeText(text);
  const m = t.match(/categor(ia|ía)\s*[:\-]\s*(.+)$/i);
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

  // 1) posição explícita (1 = primeira)
  if (position && position >= 1 && position <= lastSuggestions.length) {
    return lastSuggestions[position - 1];
  }

  // 2) filtra por ano
  let pool = lastSuggestions;
  if (year) pool = pool.filter((s) => String(s.year ?? "") === String(year));

  // 3) filtra por fonte
  if (sourceHint) {
    const sh = normalizeLite(sourceHint);
    pool = pool.filter((s) => normalizeLite(s.source || "").includes(sh));
  }

  // 4) retorna melhor candidato (primeiro)
  return pool[0] ?? lastSuggestions[0] ?? null;
}

// --- Intents ---
// Retorno padrão:
// { intent, confidence, entities: { ... }, debug? }
export function interpretIntent(rawText, ctx) {
  const text = safeText(rawText);
  const t = normalizeLite(text);

  const year = extractYear(t);
  const position = extractPosition(t);
  const sourceHint = extractSourceHint(text);
  const categoryHint = extractCategoryHint(text);

  // ====== intents fortes (alta precisão) ======

  // RESET
  if (hasAny([/\b(recome(c|ç)ar|resetar|limpar)\b/], t)) {
    return { intent: "RESET", confidence: 0.99, entities: {} };
  }

  // SWITCH_TABLE
  if (
    hasAny(
      [
        /\b(trocar|mudar|alterar)\b.*\b(tabela|camada|fonte)\b/,
        /\b(outra|outras)\b.*\b(tabela|camada|fonte)\b/,
        /^\btrocar tabela\b$/,
      ],
      t
    )
  ) {
    return { intent: "SWITCH_TABLE", confidence: 0.95, entities: {} };
  }

  // HELP
  if (hasAny([/\b(ajuda|como usar|o que você faz|instru(c|ç)(ões|ao))\b/], t)) {
    return { intent: "HELP", confidence: 0.85, entities: {} };
  }

  // DETAILS
  if (
    hasAny(
      [
        /\b(detalhes|colunas|campos|schema|descri(c|ç)(ão|ao))\b/,
        /\bquais\s+s(ã|a)o\s+as\s+colunas\b/,
        /\bmostra(r)?\s+(as\s+)?colunas\b/,
      ],
      t
    )
  ) {
    // tentar resolver alvo
    return {
      intent: "DETAILS",
      confidence: 0.9,
      entities: { year, sourceHint, position, categoryHint },
    };
  }

  // SELECT (usar/confirmar)
  if (
    hasAny(
      [
        /^\b(usar|use|selecionar|seleciona|confirmar|confirma)\b/,
        /\b(vai com|vamos com)\b/,
      ],
      t
    )
  ) {
    return {
      intent: "SELECT",
      confidence: 0.9,
      entities: { year, sourceHint, position, categoryHint, selectionText: text },
    };
  }

  // REFINE (ano/categoria/fonte soltos)
  if (hasAny([/\b(ano)\b/, /\bcategor(ia|ía)\b/, /\bfonte\b/], t) && (year || sourceHint || categoryHint)) {
    return {
      intent: "REFINE",
      confidence: 0.7,
      entities: { year, sourceHint, categoryHint },
    };
  }

  // ====== intents contextuais ======
  // "essa", "a segunda", "a de 2022" -> normalmente SELECT ou DETAILS dependendo do verbo
  if (isDeicticThis(text) || position || year || sourceHint) {
    // se contém palavra tipo "usar"/"confirmar" já caiu em SELECT acima.
    // aqui: se modo ask -> pergunta; se catalog -> interpretar como SELECT implícito
    return {
      intent: "SELECT_IMPLICIT",
      confidence: 0.6,
      entities: { year, sourceHint, position, categoryHint },
    };
  }

  // ====== fallback por modo ======
  // Se está em ASK, qualquer texto vira pergunta
  if (ctx?.mode === "ask") {
    return { intent: "ASK_QUESTION", confidence: 0.8, entities: { question: text } };
  }

  // Se está em CATALOG, qualquer texto vira busca
  return { intent: "CATALOG_SEARCH", confidence: 0.7, entities: { query: text, year, sourceHint, categoryHint } };
}

// Resolve “qual tabela?” baseado no contexto: seleção direta, ou últimas sugestões
export function resolveTargetTable({ rawText, docs, index, selectedTableId, lastSuggestions }) {
  const text = safeText(rawText);

  // 1) se o usuário colou id/título, usa seu resolveTableByText
  const r = resolveTableByText({ query: text, docs, index });
  if (r?.doc) return { kind: "doc", doc: r.doc, directContinue: r.directContinue };

  // 2) se tem tabela já selecionada e o texto for deíctico (“essa”), usa ela
  if (selectedTableId && isDeicticThis(text)) {
    const d = docs.find((x) => x.id === selectedTableId);
    if (d) return { kind: "doc", doc: d, directContinue: true };
  }

  // 3) tentar resolver por lastSuggestions (primeira/segunda/ano/fonte)
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
