// src/features/Chatter/domain/messageFactories.js

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

function humanizeAskError(msg) {
  const m = String(msg || "").toLowerCase();

  // caso específico do seu print
  if (m.includes("sql") && (m.includes("inseguro") || m.includes("unsafe"))) {
    return (
      "Não consegui entender sua pergunta com segurança para consultar a base.\n\n" +
      "Tente reformular deixando mais explícito:\n" +
      "• qual período (ex.: 2024-04 a 2024-06)\n" +
      "• qual recorte (ex.: unidade de conservação, município)\n" +
      "• qual saída (ex.: contagem, lista, top 10)\n"
    );
  }

  // fallback geral
  return (
    "Não consegui entender sua pergunta do jeito que ela foi escrita.\n\n" +
    "Tente reformular com um pouco mais de contexto (o que exatamente você quer ver na tabela)."
  );
}

export function makeAskErrorMessage(strategy, msg) {
  return makeAssistantMessage({
    text: humanizeAskError(msg),
    meta: {
      // útil pra debug sem poluir o usuário (se quiser usar futuramente)
      strategy,
      rawError: msg || null,
    },
  });
}


export function makeAskSuccessMessage({ answer_text, result_preview }) {
  return makeAssistantMessage({
    text: String(answer_text || "").trim() || "",
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
