import { now } from "../helpers";

export function newMsgId() {
  return `m_${Date.now()}_${Math.random().toString(16).slice(2)}`;
}

export function makeAssistantMessage(payload = {}) {
  return {
    id: newMsgId(),
    role: "assistant",
    ts: now(),
    ...payload,
  };
}

export function makeUserMessage(text) {
  return {
    id: newMsgId(),
    role: "user",
    ts: now(),
    text,
  };
}

export function makeCatalogLoadedMessage(count) {
  return makeAssistantMessage({
    text: `Catálogo carregado: ${count} tabelas ativas. Pode perguntar!`,
  });
}

export function makeNoTableSelectedMessage() {
  return makeAssistantMessage({
    text: "Você ainda não selecionou uma tabela. Primeiro escolha uma tabela do catálogo.",
  });
}

export function makeAskErrorMessage(strategy, msg) {
  return makeAssistantMessage({
    text: `Erro (${strategy}): ${msg || "falha no /chat/ask"}`,
  });
}

export function makeAskSuccessMessage({ answer_text, result_preview }) {
  return makeAssistantMessage({
    text: String(answer_text || "").trim() || "Sem resposta textual.",
    preview: Array.isArray(result_preview) ? result_preview : [],
    followUps: [ "Trocar tabela"],
  });
}

export function removeTrailingLoading(list) {
  const copy = [...list];
  while (copy.length) {
    const last = copy[copy.length - 1];
    if (last?.role === "assistant" && last?.isLoading) copy.pop();
    else break;
  }
  return copy;
}
