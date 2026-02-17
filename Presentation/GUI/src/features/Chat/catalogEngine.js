// src/features/Chat/catalogEngine.js
import MiniSearch from "minisearch";

function normalizeStr(s) {
  return String(s || "")
    .normalize("NFD")
    .replace(/\p{Diacritic}/gu, "")
    .toLowerCase();
}

function splitKeywords(s) {
  return String(s || "")
    .split(/[;,|]/g)
    .map((x) => x.trim())
    .filter(Boolean);
}

function buildPath(row) {
  const parts = [
    row.categoria_informacao,
    row.classe_maior,
    row.sub_classe_maior,
    row.classe_menor,
  ].filter(Boolean);
  return parts.join(" > ");
}

/**
 * Adapte ao formato real do jsonb colunas_tabela.
 * Suporta:
 * - array de strings
 * - array de objetos com {name, label}
 */
function extractColumns(colunas_tabela) {
  if (!Array.isArray(colunas_tabela)) return [];
  const cols = [];
  for (const c of colunas_tabela) {
    if (!c) continue;
    if (typeof c === "string") cols.push(c);
    else {
      if (c.name) cols.push(String(c.name));
      if (c.label) cols.push(String(c.label));
      if (c.titulo) cols.push(String(c.titulo));
      if (c.nome) cols.push(String(c.nome));
    }
  }
  return [...new Set(cols.map((x) => x.trim()).filter(Boolean))];
}

/**
 * Converte rows -> docs indexáveis
 */
export function buildDocs(rows) {
  return (rows || [])
    .filter((r) => r?.is_ativo !== false)
    .map((r) => {
      const path = buildPath(r);
      const keywords = splitKeywords(r.palavras_chave);
      const columns = extractColumns(r.colunas_tabela);

      return {
        id: r.identificador_tabela,
        title: r.titulo_tabela,
        descricao: r.descricao_tabela || "",
        path,
        year: r.ano_elaboracao ?? null,
        source: r.fonte_dados ?? null,
        keywords,
        columns,
        // Campo indexado: inclui TUDO (titulo + desc + keywords + path + colunas + fonte + ano)
        text: normalizeStr(
          [
            r.titulo_tabela,
            r.descricao_tabela || "",
            keywords.join(" "),
            path,
            columns.join(" "),
            r.fonte_dados || "",
            String(r.ano_elaboracao ?? ""),
            r.identificador_tabela,
          ].join(" ")
        ),
        raw: r,
      };
    });
}

/**
 * Cria índice MiniSearch.
 * Guardamos campos para render (storeFields).
 */
export function buildIndex(docs) {
  const ms = new MiniSearch({
    fields: ["text"],
    storeFields: [
      "id",
      "title",
      "descricao",
      "path",
      "keywords",
      "columns",
      "year",
      "source",
    ],
    searchOptions: {
      prefix: true,
      fuzzy: 0.2,
    },
  });

  ms.addAll(docs);
  return ms;
}



const STOPWORDS_PT = new Set([
  "a","o","as","os","um","uma","uns","umas",
  "de","da","do","das","dos",
  "e","ou","em","no","na","nos","nas",
  "por","para","com","sem","sobre","entre","até",
  "que","se","ao","aos","à","às",
  "não","sim","mais","menos",
  "ser","estar","ter","há",
]);

function isUsefulToken(t) {
  if (!t) return false;
  // regra: aceita 2 letras só se NÃO for stopword
  if (t.length >= 3) return true;
  return t.length >= 2 && !STOPWORDS_PT.has(t);
}

function tokens(query) {
  return normalizeStr(query)
    .split(/\s+/)
    .map((x) => x.trim())
    .filter(isUsefulToken);
}

/**
 * Explicação curta baseada em:
 * - match em keywords
 * - match em colunas
 * - descrição presente
 */
export function buildReason(query, doc) {
  const q = tokens(query); // agora já vem filtrado

  const kw = (doc.keywords || []).map(normalizeStr);
  const cols = (doc.columns || []).map(normalizeStr);

  const hitsKw = q.filter((t) => kw.some((k) => k.includes(t)));
  const hitsCols = q.filter((t) => cols.some((c) => c.includes(t)));

  const parts = [];
  if (hitsKw.length) parts.push(`keywords: ${[...new Set(hitsKw)].slice(0, 4).join(", ")}`);
  if (hitsCols.length) parts.push(`colunas: ${[...new Set(hitsCols)].slice(0, 4).join(", ")}`);
  if (doc.descricao) parts.push("descrição compatível");

  return parts.length ? parts.join(" · ") : "compatibilidade geral";
}

/**
 * Busca top N e monta sugestões.
 */
export function searchCatalog(index, query, limit = 20) {
  const res = index.search(normalizeStr(query), { limit });
  return res;
}

/**
 * Sugere “refinos” (chips) puxando as categorias/anos mais frequentes no top.
 * Isso dá MUITO a sensação de ChatGPT: ele propõe filtros conversacionais.
 */
export function buildRefinementChips(topResults) {
  const years = new Map();
  const categories = new Map();

  for (const r of topResults) {
    // path começa com categoria (se existir)
    const cat = String(r.path || "").split(" > ")[0]?.trim();
    if (cat) categories.set(cat, (categories.get(cat) || 0) + 1);

    const y = r.year;
    if (y) years.set(String(y), (years.get(String(y)) || 0) + 1);
  }

  const topCats = [...categories.entries()]
    .sort((a, b) => b[1] - a[1])
    .slice(0, 4)
    .map(([c]) => `Categoria: ${c}`);

  const topYears = [...years.entries()]
    .sort((a, b) => b[1] - a[1])
    .slice(0, 4)
    .map(([y]) => `Ano: ${y}`);

  return [...topCats, ...topYears].slice(0, 6);
}
