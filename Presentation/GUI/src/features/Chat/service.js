// src/features/Chat/service.js
import api from "../../_config/axios";

/**
 * Busca o catálogo completo (uma única chamada).
 * Espera resposta no formato:
 * { version, generated_at, count, items: [...] }
 */
export async function getCatalog() {
  try {
    const { data } = await api.get("/start/catalog");

    const items = data?.items;

    if (!Array.isArray(items)) {
      return {
        ok: false,
        error: "Catálogo inválido: resposta não contém 'items' como array.",
      };
    }

    return { ok: true, data: items, meta: { ...data, items: undefined } };
  } catch (error) {
    const msg =
      error.response?.data?.detail ||
      error.response?.data?.message ||
      "Erro ao carregar catálogo.";
    return { ok: false, error: msg };
  }
}


/**
 * Chama o endpoint /chat/ask usando a tabela escolhida no passo anterior
 * Payload:
 * { question, table_identifier, top_k }
 */
export async function askChat({ question, table_identifier, top_k = 1000 }) {
  try {
    const payload = { question, table_identifier, top_k };
    const { data } = await api.post("/chat/ask", payload);
    return { ok: true, data };
  } catch (error) {
    const msg =
      error.response?.data?.detail ||
      error.response?.data?.message ||
      "Erro ao consultar /chat/ask.";
    return { ok: false, error: msg };
  }
}