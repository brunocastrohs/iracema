// src/features/Chat/fca/fcaPayloadBuilder.js

import { DEFAULT_LIMIT } from "./fcaDraftFactory";

export function buildFcaPayload({
  questionForLogging = "",
  table_identifier,
  top_k,
  explain = false,
  conversation_id = null,
  draft,
}) {
  
  const d = draft || {};

  const limit = Number.isFinite(d.limit) ? d.limit : (Number.isFinite(top_k) ? top_k : DEFAULT_LIMIT);

  return {
    question: String(questionForLogging || ""),
    table_identifier: String(table_identifier || ""),
    top_k: Number.isFinite(top_k) ? top_k : limit,
    explain: Boolean(explain),
    conversation_id: conversation_id ?? null,

    fca: {
      select: d._selectAll ? [] : (Array.isArray(d.select) ? d.select : []),
      where: Array.isArray(d.where) ? d.where : [],
      group_by: Array.isArray(d.group_by) ? d.group_by : [],
      order_by: Array.isArray(d.order_by) ? d.order_by : [],
      limit: Number.isFinite(d.limit) ? d.limit : null,
      offset: Number.isFinite(d.offset) ? d.offset : 0,
    },
  };
}
