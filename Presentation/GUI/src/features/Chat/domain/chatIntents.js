// src/features/Chatter/domain/chatIntent.js

import { safeText } from "../helpers";

/**
 * Normaliza comandos rápidos.
 * Retorna: { type: "SWITCH_TABLE" | "NEW_QUESTION" | null }
 */
export function parseQuickCommand(raw) {
  const q = safeText(raw).toLowerCase();

  if (q === "trocar tabela") return { type: "SWITCH_TABLE" };
  if (q === "nova pergunta") return { type: "NEW_QUESTION" };

  return { type: null };
}

/**
 * Decide fallback de estratégia conforme sua regra:
 * - se preferida = ask/fc e falhar => tenta ask
 * - se preferida = ask e falhar => tenta ask/fc
 * - se for outra => tenta ask/fc
 */
export function computeFallbackStrategy(preferred) {
  if (preferred === "ask/fc/args") return "ask";
  if (preferred === "ask") return "ask/fc/args";
  return "ask/fc/args";
}
