
export function now() {
  return Date.now();
}

export function safeText(v) {
  return String(v ?? "").trim();
}

export function normalizeLite(s) {
  return String(s || "")
    .normalize("NFD")
    .replace(/\p{Diacritic}/gu, "")
    .toLowerCase()
    .trim();
}

export function formatDetails(doc) {
  const lines = [];

  lines.push(doc.title?.toUpperCase());

  if (doc.path) lines.push(`Caminho: ${doc.path}`);
  if (doc.year) lines.push(`Ano: ${doc.year}`);
  if (doc.source) lines.push(`Fonte: ${doc.source}`);

  if (doc.keywords?.length) {
    lines.push("");
    lines.push(`Palavras-chave: ${doc.keywords.join(", ")}`);
  }

  if (doc.descricao) {
    lines.push("");
    lines.push("Descrição:");
    lines.push(doc.descricao);
  }

  if (doc.columns?.length) {
    lines.push("");
    lines.push(`Colunas (${doc.columns.length}):`);

    const preview = doc.columns.slice(0, 40);
    preview.forEach((c) => lines.push(`- ${c}`));

    if (doc.columns.length > preview.length) {
      lines.push(`- ... (+${doc.columns.length - preview.length} colunas)`);
    }
  }

  return lines.join("\n");
}

/**
 * Interpreta intenção de "usar/selecionar/continuar com" uma tabela pelo texto digitado.
 * Retorna:
 * - directContinue: se o usuário explicitamente pediu pra usar/continuar (vai direto pro modo ASK)
 * - hint: o texto que deve ser usado para bater com título/ID
 */
export function extractSelectionIntent(text) {
  const raw = String(text || "");
  const q = normalizeLite(raw);

  const directContinue = [
    /^usar\s+/i,
    /^use\s+/i,
    /^continuar\s+com\s+/i,
    /^quero\s+(?:a|essa)\b/i,
    /^selecion(ar|a)\s+/i,
    /^vai\s+com\s+/i,
    /^vamos\s+com\s+/i,
  ].some((re) => re.test(q));

  // Tenta capturar o "resto" como alvo: "usar X", "tabela: X", "id: X"
  const patterns = [
    /^usar\s+(.+)$/i,
    /^use\s+(.+)$/i,
    /^selecionar\s+(.+)$/i,
    /^seleciona\s+(.+)$/i,
    /^continuar\s+com\s+(.+)$/i,
    /^quero\s+(?:a|essa)\s*[:\-]?\s*(.+)$/i,
    /^essa\s*[:\-]?\s*(.+)$/i,
    /^tabela\s*[:\-]?\s*(.+)$/i,
    /^id\s*[:\-]?\s*(.+)$/i,
  ];

  for (const re of patterns) {
    const m = q.match(re);
    if (m?.[1]) return { directContinue, hint: m[1].trim() };
  }

  // fallback: pode ser o título/ID puro colado
  return { directContinue, hint: q };
}

export function scoreDocMatch(needleRaw, doc) {
  const needle = normalizeLite(needleRaw);
  if (!needle || needle.length < 3) return 0;

  const id = normalizeLite(doc.id);
  const title = normalizeLite(doc.title);
  const path = normalizeLite(doc.path || "");

  // match forte: igualdade
  if (needle === id) return 120;
  if (needle === title) return 110;

  // contém (bem forte para id)
  if (id.includes(needle)) return 105;

  // contém no título
  if (title.includes(needle)) return 90;

  // tokens: cobre casos "parte do título"
  const tokens = needle.split(/\s+/).filter(Boolean);
  if (tokens.length) {
    const hitTitle = tokens.filter((t) => t.length >= 3 && title.includes(t)).length;
    const hitPath = tokens.filter((t) => t.length >= 3 && path.includes(t)).length;
    return hitTitle * 12 + hitPath * 5;
  }

  return 0;
}

/**
 * Resolve seleção por texto:
 * - tenta scoring direto em docs
 * - fallback: minisearch para puxar candidatos e re-score
 * Retorna { doc, directContinue, ambiguousDocs }
 */
export function resolveTableByText({ query, docs, index }) {
  const { directContinue, hint } = extractSelectionIntent(query);

  if (!hint || hint.length < 3) return { doc: null, directContinue, ambiguousDocs: [] };

  // 1) scoring direto em todos docs
  const scored = [];
  for (const d of docs) {
    const s = scoreDocMatch(hint, d);
    if (s > 0) scored.push({ d, s });
  }
  scored.sort((a, b) => b.s - a.s);

  const best = scored[0];
  const second = scored[1];

  // Ambiguidade: scores muito próximos e ambos relevantes
  if (best && second && best.s >= 80 && second.s >= 80 && best.s - second.s < 8) {
    return {
      doc: null,
      directContinue,
      ambiguousDocs: scored.slice(0, 3).map((x) => x.d),
    };
  }

  // Seleção segura: score alto (evita “uso do solo 2021” auto-selecionar errado)
  if (best && best.s >= 105) {
    return { doc: best.d, directContinue, ambiguousDocs: [] };
  }

  // 2) fallback via minisearch (quando título parcial)
  if (index) {
    const res = index.search(normalizeLite(hint), { limit: 8 });
    const candidates = res
      .map((r) => docs.find((d) => d.id === r.id))
      .filter(Boolean);

    const scored2 = candidates
      .map((d) => ({ d, s: scoreDocMatch(hint, d) }))
      .sort((a, b) => b.s - a.s);

    const best2 = scored2[0];
    const second2 = scored2[1];

    if (best2 && second2 && best2.s >= 70 && second2.s >= 70 && best2.s - second2.s < 8) {
      return {
        doc: null,
        directContinue,
        ambiguousDocs: scored2.slice(0, 3).map((x) => x.d),
      };
    }

    // threshold menor aqui, porque já veio rankeado pelo índice
    if (best2 && best2.s >= 90) {
      return { doc: best2.d, directContinue, ambiguousDocs: [] };
    }
  }

  return { doc: null, directContinue, ambiguousDocs: [] };
}