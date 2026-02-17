// src/features/Chat/index.js
import { useEffect, useMemo, useRef, useState } from "react";
import "./styles.css";

import ChatMessageList from "./components/ChatMessageList";
import ChatInputBar from "./components/ChatInputBar";

import {
  safeText,
  formatDetails,
  resolveTableByText,
  normalizeColumns,
  pickRandom,
  formatColumnsList,
} from "./helpers";
import { searchCatalog, buildReason, buildRefinementChips } from "./catalogEngine";

import { useCatalog } from "./hooks/useCatalog";
import { useAutoScroll } from "./hooks/useAutoScroll";
import { useChatMessages } from "./hooks/useChatMessages";

import { interpretIntent, resolveTargetTable } from "./nlu/intentEngine";
import { askChat } from "./service";

import { makeInitialFcaDraft } from "./fca/fcaDraftFactory";
import { parseFcaBuilderText } from "./fca/fcaParser";
import { applyFcaCommand, validateFcaDraft } from "./fca/fcaReducer";
import { buildFcaPreviewText } from "./fca/fcaPreviewBuilder";
import { buildFcaPayload } from "./fca/fcaPayloadBuilder";

import { makeAssistantMessage, removeTrailingLoading } from "./domain/messageFactories";

const INITIAL_TEXT =
  "Olá! Posso te ajudar a encontrar tabelas no catálogo e montar consultas.\n\n" +
  "Descreva o que você procura (tema, palavra-chave, ano, fonte) e eu sugiro as opções mais próximas.\n\n" +
  "Dica: você também pode digitar o título ou o identificador_tabela para selecionar direto.";

function looksLikeExplicitSelection(text) {
  const q = String(text || "").trim().toLowerCase();
  if (!q) return false;
  if (/^(usar|use|selecionar|seleciona|select|abrir|open)\b/.test(q)) return true;
  if (/^id\s*[:\-]\s*\S+/.test(q)) return true;
  if (/^(tabela|table)\s*[:\-]\s*\S+/.test(q)) return true;
  return false;
}

function isSkip(text) {
  const q = String(text || "").trim().toLowerCase();
  return ["nao", "não", "n", "pular", "skip", "nenhum", "nenhuma"].includes(q);
}

// etapas do wizard
const FCA_STEPS = {
  SELECT: "SELECT",
  WHERE: "WHERE",
  GROUP_BY: "GROUP_BY",
  AGG: "AGG",
  ORDER_BY: "ORDER_BY",
  LIMIT: "LIMIT",
  READY: "READY",
};

export default function Chat() {
  const { loadingCatalog, catalogError, docs, index } = useCatalog();
  const { bottomRef, scrollToBottom } = useAutoScroll();

  const lastSuggestionsRef = useRef([]);
  const [prefill, setPrefill] = useState("");

  const {
    messages,
    setMessages,
    typedDone,
    markDone,
    lastAssistantId,
    pushUser,
    pushAssistant,
    pushCatalogLoaded,
  } = useChatMessages({ initialAssistantText: INITIAL_TEXT });

  const [mode, setMode] = useState("catalog"); // "catalog" | "fca_builder"
  const [selectedTableId, setSelectedTableId] = useState(null);
  const [sending, setSending] = useState(false);

  const [fcaDraft, setFcaDraft] = useState(null);
  const [fcaStep, setFcaStep] = useState(FCA_STEPS.SELECT);

  const selectedDoc = useMemo(() => {
    if (!selectedTableId) return null;
    return (docs || []).find((d) => d.id === selectedTableId) || null;
  }, [docs, selectedTableId]);

  useEffect(() => {
    if (!loadingCatalog && !catalogError && (docs || []).length) {
      const already = messages.some((m) => (m.text || "").startsWith("Catálogo carregado:"));
      if (!already) pushCatalogLoaded((docs || []).length);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [loadingCatalog, catalogError, (docs || []).length]);

  useEffect(() => {
    scrollToBottom();
  }, [messages, scrollToBottom]);

  function pushSuggestedPromptsForCatalog() {
    return ["mineração", "biodiversidade", "unidades de conservação", "ano: 2022", "fonte: mapbiomas"];
  }

  function pushSuggestedPromptsForSelect() {
    return ["todas as colunas", "colunas: processo, ano, area_ha", "preview", "trocar tabela"];
  }

  function pushSuggestedPromptsForWhere() {
    return ["filtro: ano = 2021", "filtro: area_ha >= 1", "pular", "executar agora", "preview"];
  }

  function pushSuggestedPromptsForGroupBy() {
    return ["agrupar por: uf", "agrupar por: uso", "pular", "preview"];
  }

  function pushSuggestedPromptsForAgg() {
    return ["agregar: sum(area_ha) como area_total", "agregar: count(*) como n", "pular", "preview"];
  }

  function pushSuggestedPromptsForOrderBy() {
    return ["ordenar por: area_ha desc", "ordenar por: ano asc", "pular", "preview"];
  }

  function pushSuggestedPromptsForLimit() {
    return ["limit: 20", "limit: 100", "pular", "preview", "executar"];
  }

  function pushSuggestedPromptsForReady() {
    return ["preview", "executar", "nova consulta", "trocar tabela", "voltar"];
  }

  function resetChat() {
    setMode("catalog");
    setSelectedTableId(null);
    setFcaDraft(null);
    setFcaStep(FCA_STEPS.SELECT);
    lastSuggestionsRef.current = [];

    setMessages([
      makeAssistantMessage({
        text:
          "Recomeçando.\n\n" +
          "Descreva o que você procura no catálogo (tema, recorte, ano, fonte).\n\n" +
          "Dica: você pode digitar o título ou o identificador_tabela para selecionar direto.",
        suggestedPrompts: pushSuggestedPromptsForCatalog(),
      }),
      ...(loadingCatalog
        ? []
        : [
            makeAssistantMessage({
              text: `Catálogo carregado (${(docs || []).length} tabelas ativas).`,
              suggestedPrompts: ["mineração", "buscar: uso do solo", "buscar: unidades de conservação"],
            }),
          ]),
    ]);
  }

  function onSelectTable(id) {
    const doc = (docs || []).find((d) => d.id === id);

    if (!doc) {
      pushAssistant({
        text: "Não encontrei os detalhes dessa tabela no índice.",
        suggestedPrompts: pushSuggestedPromptsForCatalog(),
      });
      return;
    }

    // contexto conversacional
    lastSuggestionsRef.current = [{ id: doc.id, title: doc.title, year: doc.year, source: doc.source, path: doc.path }];

    // ✅ entra direto no wizard
    startFcaBuilder(doc.id);
  }

  function startFcaBuilder(selectedId) {
    const doc = (docs || []).find((d) => d.id === selectedId) || null;

    // ✅ estado do wizard
    setSelectedTableId(selectedId);
    setMode("fca_builder");
    setFcaStep(FCA_STEPS.SELECT);

    const draft = makeInitialFcaDraft();
    setFcaDraft(draft);

    // ✅ mostra colunas no início do wizard
    const { allNames, nonGeomNames } = doc ? normalizeColumns(doc) : { allNames: [], nonGeomNames: [] };
    const sample = pickRandom(nonGeomNames.length ? nonGeomNames : allNames, 3);

    const columnsText =
      allNames.length ? `\n\nColunas (${allNames.length}):\n${formatColumnsList(allNames, 20)}` : "";

    pushAssistant({
      text:
        `Tabela selecionada:\n\n` +
        `• ${doc?.title ?? selectedId}\n` +
        (doc?.year ? `• Ano: ${doc.year}\n` : "") +
        columnsText +
        `\n\nPasso 1/6 — Seleção de colunas:\n` +
        `Você quer consultar todas as colunas ou apenas algumas?\n` +
        `- "todas as colunas"\n` +
        `- "colunas: a, b, c"\n` +
        `Você também pode digitar "pular" nas próximas etapas.\n`,
      suggestedPrompts: [
        "todas as colunas",
        sample.length ? `colunas: ${sample.join(", ")}` : "colunas: processo, ano, area_ha",
        "preview",
        "trocar tabela",
      ],
    });
  }

  function restartFcaWizardSameTable({ reasonText = "" } = {}) {
    if (!selectedTableId) {
      pushAssistant({
        text: "Ainda não há tabela selecionada.",
        suggestedPrompts: pushSuggestedPromptsForCatalog(),
      });
      return;
    }

    const doc = (docs || []).find((d) => d.id === selectedTableId) || null;

    setMode("fca_builder");
    setFcaStep(FCA_STEPS.SELECT);

    const draft = makeInitialFcaDraft();
    setFcaDraft(draft);

    const { allNames, nonGeomNames } = doc ? normalizeColumns(doc) : { allNames: [], nonGeomNames: [] };
    const sample = pickRandom(nonGeomNames.length ? nonGeomNames : allNames, 3);

    const columnsText =
      allNames.length ? `\n\nColunas (${allNames.length}):\n${formatColumnsList(allNames, 20)}` : "";

    pushAssistant({
      text:
        (reasonText ? `${reasonText}\n\n` : "") +
        `Vamos montar uma nova consulta para:\n\n` +
        `• ${doc?.title ?? selectedTableId}\n` +
        (doc?.year ? `• Ano: ${doc.year}\n` : "") +
        columnsText +
        `\n\nPasso 1/6 — Seleção de colunas:\n` +
        `Você quer consultar todas as colunas ou apenas algumas?\n` +
        `- "todas as colunas"\n` +
        `- "colunas: a, b, c"\n`,
      suggestedPrompts: [
        "todas as colunas",
        sample.length ? `colunas: ${sample.join(", ")}` : "colunas: processo, ano, area_ha",
        "preview",
        "trocar tabela",
      ],
    });
  }

  function askNewQueryAfterRun() {
    pushAssistant({
      text:
        "Consulta executada ✅\n\n" +
        "Você quer fazer uma nova consulta?\n" +
        "- \"nova consulta\" (mesma tabela)\n" +
        "- \"trocar tabela\"",
      suggestedPrompts: ["nova consulta", "trocar tabela", "preview"],
    });
  }

  function goBackToCatalog() {
    setMode("catalog");
    setSelectedTableId(null);
    setFcaDraft(null);
    setFcaStep(FCA_STEPS.SELECT);

    pushAssistant({
      text: "Certo — vamos escolher outra tabela. Descreva o que você quer encontrar no catálogo.",
      suggestedPrompts: pushSuggestedPromptsForCatalog(),
    });
  }

  function showDetailsFlow(originalText) {
    const resolved = resolveTargetTable({
      rawText: originalText,
      docs: docs || [],
      index,
      selectedTableId,
      lastSuggestions: lastSuggestionsRef.current,
    });

    const doc = resolved.kind === "doc" ? resolved.doc : selectedDoc;

    if (!doc) {
      pushAssistant({
        text:
          "Não consegui identificar qual tabela você quer detalhar.\n" +
          "Você pode colar o id/título ou selecionar uma opção exibida.",
        suggestedPrompts: pushSuggestedPromptsForCatalog(),
      });
      return;
    }

    pushAssistant({
      text: formatDetails(doc),
      suggestedPrompts: ["nova consulta", "todas as colunas", "colunas: processo, ano, area_ha", "preview", "trocar tabela"],
    });
  }

  function previewFca() {
    if (!selectedTableId) {
      pushAssistant({
        text: "Ainda não há uma tabela selecionada para montar consulta.",
        suggestedPrompts: pushSuggestedPromptsForCatalog(),
      });
      return;
    }

    const preview = buildFcaPreviewText({
      table_identifier: selectedTableId,
      fca: fcaDraft || makeInitialFcaDraft(),
    });

    pushAssistant({
      text: `Prévia da consulta:\n\n${preview}`,
      suggestedPrompts:
        fcaStep === FCA_STEPS.SELECT
          ? pushSuggestedPromptsForSelect()
          : fcaStep === FCA_STEPS.WHERE
          ? pushSuggestedPromptsForWhere()
          : fcaStep === FCA_STEPS.GROUP_BY
          ? pushSuggestedPromptsForGroupBy()
          : fcaStep === FCA_STEPS.AGG
          ? pushSuggestedPromptsForAgg()
          : fcaStep === FCA_STEPS.ORDER_BY
          ? pushSuggestedPromptsForOrderBy()
          : fcaStep === FCA_STEPS.LIMIT
          ? pushSuggestedPromptsForLimit()
          : pushSuggestedPromptsForReady(),
    });
  }

  async function runFca({ questionForLogging = "" } = {}) {
    if (!selectedTableId) {
      pushAssistant({
        text: "Antes de executar, selecione uma tabela e monte a consulta.",
        suggestedPrompts: pushSuggestedPromptsForCatalog(),
      });
      return;
    }

    const draft = fcaDraft || makeInitialFcaDraft();
    const v = validateFcaDraft(draft);
    if (!v.ok) {
      pushAssistant({ text: v.message, suggestedPrompts: pushSuggestedPromptsForReady() });
      return;
    }

    setSending(true);
    pushAssistant({ text: "Executando…", isLoading: true });

    try {
      const explain = localStorage.getItem("iracema_explain") === "true";

      const payload = buildFcaPayload({
        question: questionForLogging || "",
        table_identifier: selectedTableId,
        top_k: draft?.limit ?? 100,
        explain,
        conversation_id: null,
        fca: draft,
      });

      const res = await askChat(payload);

      setMessages((prev) => {
        const base = removeTrailingLoading(prev);

        if (!res?.ok) {
          const errText = `Não consegui executar a consulta agora.${
            res?.error ? ` Detalhes: ${res.error}` : ""
          }`.trim();

          // reinicia o wizard depois de renderizar a msg de erro
          setTimeout(() => {
            restartFcaWizardSameTable({
              reasonText: "Houve um erro ao executar. Vamos reconstruir a consulta do zero.",
            });
          }, 0);

          return [
            ...base,
            makeAssistantMessage({
              text: errText,
              suggestedPrompts: ["nova consulta", "trocar tabela"],
            }),
          ];
        }

        if (res?.data?.error) {
          const errText = `Não consegui executar a consulta: ${res.data.error}`;

          setTimeout(() => {
            restartFcaWizardSameTable({
              reasonText: "O backend retornou erro. Vamos reconstruir a consulta do zero.",
            });
          }, 0);

          return [
            ...base,
            makeAssistantMessage({
              text: errText,
              suggestedPrompts: ["nova consulta", "trocar tabela"],
            }),
          ];
        }

        const answerText = safeText(res?.data?.answer_text || res?.data?.answer || "") || "Ok. Consulta executada.";
        const preview = Array.isArray(res?.data?.result_preview) ? res.data.result_preview : [];

        return [
          ...base,
          makeAssistantMessage({
            text: answerText,
            preview,
            suggestedPrompts: ["nova consulta", "trocar tabela", "preview"],
          }),
          makeAssistantMessage({
            text:
              "Você quer fazer uma nova consulta?\n" +
              "- \"nova consulta\" (mesma tabela)\n" +
              "- \"trocar tabela\"",
            suggestedPrompts: ["nova consulta", "trocar tabela"],
          }),
        ];
      });

      setFcaStep(FCA_STEPS.READY);
    } catch (e) {
      setMessages((prev) => [
        ...removeTrailingLoading(prev),
        makeAssistantMessage({
          text: "Erro inesperado ao executar. Vou reiniciar o wizard para você tentar de novo.",
          suggestedPrompts: ["nova consulta", "trocar tabela"],
        }),
      ]);

      setTimeout(() => {
        restartFcaWizardSameTable({
          reasonText: "Erro inesperado. Vamos reconstruir a consulta do zero.",
        });
      }, 0);
    } finally {
      setSending(false);
    }
  }

  function askNextWizardQuestion(nextStep) {
    setFcaStep(nextStep);

    if (nextStep === FCA_STEPS.WHERE) {
      pushAssistant({
        text:
          "Passo 2/6 — Filtros (WHERE):\n" +
          "Você quer filtrar alguma coluna?\n" +
          `Ex.: "filtro: ano = 2021" ou "filtro: area_ha >= 1"\n` +
          `Se não quiser, digite "pular".\n` +
          `Se quiser executar já, digite "executar agora".`,
        suggestedPrompts: pushSuggestedPromptsForWhere(),
      });
      return;
    }

    if (nextStep === FCA_STEPS.GROUP_BY) {
      pushAssistant({
        text:
          "Passo 3/6 — Agrupamento (GROUP BY):\n" +
          "Você quer agrupar por alguma coluna?\n" +
          `Ex.: "agrupar por: uf"\n` +
          `Se não quiser, digite "pular".`,
        suggestedPrompts: pushSuggestedPromptsForGroupBy(),
      });
      return;
    }

    if (nextStep === FCA_STEPS.AGG) {
      pushAssistant({
        text:
          "Passo 4/6 — Agregações (SUM/COUNT/AVG...):\n" +
          "Você quer adicionar alguma agregação?\n" +
          `Ex.: "agregar: sum(area_ha) como area_total"\n` +
          `Ou "agregar: count(*) como n"\n` +
          `Se não quiser, digite "pular".`,
        suggestedPrompts: pushSuggestedPromptsForAgg(),
      });
      return;
    }

    if (nextStep === FCA_STEPS.ORDER_BY) {
      pushAssistant({
        text:
          "Passo 5/6 — Ordenação (ORDER BY):\n" +
          "Você quer ordenar por alguma coluna (ou alias)?\n" +
          `Ex.: "ordenar por: area_ha desc"\n` +
          `Se não quiser, digite "pular".`,
        suggestedPrompts: pushSuggestedPromptsForOrderBy(),
      });
      return;
    }

    if (nextStep === FCA_STEPS.LIMIT) {
      pushAssistant({
        text:
          "Passo 6/6 — Limite (LIMIT):\n" +
          "Quantas linhas no máximo você quer retornar?\n" +
          `Ex.: "limit: 20"\n` +
          `Se não quiser ajustar, digite "pular".`,
        suggestedPrompts: pushSuggestedPromptsForLimit(),
      });
      return;
    }

    pushAssistant({
      text:
        "Pronto ✅\n\n" +
        "Você pode:\n" +
        "- " + `"preview"` + " (ver SQL/consulta)\n" +
        "- " + `"executar"` + " (rodar no backend)\n" +
        "- " + `"nova consulta"` + " (recomeçar o wizard)\n" +
        "- " + `"trocar tabela"` + "\n",
      suggestedPrompts: pushSuggestedPromptsForReady(),
    });
  }

  function handleWizardProgress(cmd, rawText) {
    const lower = rawText.trim().toLowerCase();

    // comando textual global (sem depender do parser)
    if (lower === "nova consulta") {
      restartFcaWizardSameTable();
      return;
    }

    // ✅ atalho após WHERE (ou em qualquer momento)
    if (lower === "executar agora") {
      runFca({ questionForLogging: "" });
      return;
    }

    // comandos globais do builder
    if (cmd.kind === "BACK" || lower === "voltar") {
      goBackToCatalog();
      return;
    }
    if (cmd.kind === "PREVIEW") {
      previewFca();
      return;
    }
    if (cmd.kind === "EXECUTE") {
      runFca({ questionForLogging: "" });
      return;
    }
    if (lower === "trocar tabela") {
      goBackToCatalog();
      return;
    }

    // pular / não em um passo
    if (isSkip(rawText)) {
      const next =
        fcaStep === FCA_STEPS.SELECT
          ? FCA_STEPS.WHERE
          : fcaStep === FCA_STEPS.WHERE
          ? FCA_STEPS.GROUP_BY
          : fcaStep === FCA_STEPS.GROUP_BY
          ? FCA_STEPS.AGG
          : fcaStep === FCA_STEPS.AGG
          ? FCA_STEPS.ORDER_BY
          : fcaStep === FCA_STEPS.ORDER_BY
          ? FCA_STEPS.LIMIT
          : fcaStep === FCA_STEPS.LIMIT
          ? FCA_STEPS.READY
          : FCA_STEPS.READY;

      askNextWizardQuestion(next);
      return;
    }

    if (cmd.kind === "UNKNOWN") {
      pushAssistant({
        text:
          "Não entendi esse comando.\n\n" +
          "Exemplos válidos:\n" +
          "- todas as colunas\n" +
          "- colunas: processo, ano, area_ha\n" +
          "- filtro: area_ha >= 1\n" +
          "- agrupar por: uf\n" +
          "- agregar: sum(area_ha) como area_total\n" +
          "- ordenar por: area_ha desc\n" +
          "- limit: 20\n" +
          "- preview\n" +
          "- executar\n" +
          "- executar agora\n" +
          "- pular\n" +
          "- nova consulta\n",
        suggestedPrompts:
          fcaStep === FCA_STEPS.SELECT
            ? pushSuggestedPromptsForSelect()
            : fcaStep === FCA_STEPS.WHERE
            ? pushSuggestedPromptsForWhere()
            : fcaStep === FCA_STEPS.GROUP_BY
            ? pushSuggestedPromptsForGroupBy()
            : fcaStep === FCA_STEPS.AGG
            ? pushSuggestedPromptsForAgg()
            : fcaStep === FCA_STEPS.ORDER_BY
            ? pushSuggestedPromptsForOrderBy()
            : pushSuggestedPromptsForLimit(),
      });
      return;
    }

    // aplica no draft
    setFcaDraft((prev) => applyFcaCommand(prev, cmd));

    // avança o wizard
    if (fcaStep === FCA_STEPS.SELECT) {
      askNextWizardQuestion(FCA_STEPS.WHERE);
      return;
    }
    if (fcaStep === FCA_STEPS.WHERE) {
      askNextWizardQuestion(FCA_STEPS.GROUP_BY);
      return;
    }
    if (fcaStep === FCA_STEPS.GROUP_BY) {
      askNextWizardQuestion(FCA_STEPS.AGG);
      return;
    }
    if (fcaStep === FCA_STEPS.AGG) {
      askNextWizardQuestion(FCA_STEPS.ORDER_BY);
      return;
    }
    if (fcaStep === FCA_STEPS.ORDER_BY) {
      askNextWizardQuestion(FCA_STEPS.LIMIT);
      return;
    }
    if (fcaStep === FCA_STEPS.LIMIT) {
      askNextWizardQuestion(FCA_STEPS.READY);
      return;
    }

    pushAssistant({
      text: "Ok. Atualizei a consulta. Quer um preview ou executar?",
      suggestedPrompts: pushSuggestedPromptsForReady(),
    });
  }

  function dispatchIntent(nlu, originalText) {
    const lower = String(originalText || "").trim().toLowerCase();

    // atalho: "nova consulta" em qualquer modo
    if (lower === "nova consulta") {
      if (selectedTableId) {
        restartFcaWizardSameTable();
      } else {
        pushAssistant({
          text: "Ainda não há tabela selecionada. Primeiro selecione uma tabela no catálogo.",
          suggestedPrompts: pushSuggestedPromptsForCatalog(),
        });
      }
      return true;
    }

    if (nlu.intent === "RESET") {
      resetChat();
      return true;
    }

    if (nlu.intent === "HELP") {
      pushAssistant({
        text:
          "Eu te ajudo a:\n" +
          "1) buscar tabelas no catálogo\n" +
          "2) selecionar uma tabela\n" +
          "3) montar a consulta passo a passo (filtros, group by, agregações, order by e limit)\n\n" +
          "Exemplos:\n" +
          "- mineração\n" +
          "- usar 1200_ce_atividade_mineracao_2021_pol\n" +
          "- detalhar\n" +
          "- todas as colunas\n" +
          "- colunas: processo, ano, area_ha\n" +
          "- filtro: area_ha >= 1\n" +
          "- executar agora (após filtros)\n" +
          "- preview\n" +
          "- executar\n",
        suggestedPrompts: ["mineração", "detalhar", "todas as colunas", "colunas: processo, ano, area_ha"],
      });
      return true;
    }

    if (nlu.intent === "SWITCH_TABLE") {
      goBackToCatalog();
      return true;
    }

    if (nlu.intent === "DETAILS") {
      showDetailsFlow(originalText);
      return true;
    }

    if (nlu.intent === "SELECT" || nlu.intent === "SELECT_IMPLICIT") {
      const resolved = resolveTargetTable({
        rawText: nlu.entities?.selectionText || originalText,
        docs: docs || [],
        index,
        selectedTableId,
        lastSuggestions: lastSuggestionsRef.current,
      });

      const doc = resolved.kind === "doc" ? resolved.doc : null;

      if (!doc) {
        pushAssistant({
          text:
            "Não consegui identificar exatamente qual tabela você quer usar.\n" +
            "Me dê mais um detalhe (tema/ano/fonte) e eu mostro opções.",
          suggestedPrompts: pushSuggestedPromptsForCatalog(),
        });
        return true;
      }

      startFcaBuilder(doc.id);
      return true;
    }

    return false;
  }

  function catalogSearchPipeline(query) {
    const q = safeText(query);
    if (!q) return;

    const docsArr = docs || [];

    // match exato por id colado
    const exactDoc = docsArr.find((d) => String(d.id) === String(q).trim());
    if (exactDoc) {
      onSelectTable(exactDoc.id);
      return;
    }

    // seleção por texto somente se explícito
    if (looksLikeExplicitSelection(q)) {
      const { doc, directContinue, ambiguousDocs } = resolveTableByText({ query: q, docs: docsArr, index });

      if (ambiguousDocs?.length) {
        const suggestions = ambiguousDocs.slice(0, 20).map((d) => ({
          id: d.id,
          title: d.title,
          path: d.path,
          year: d.year ?? null,
          source: d.source ?? null,
          reason: "nome/título parecido",
        }));
        lastSuggestionsRef.current = suggestions;

        pushAssistant({
          text: "Encontrei mais de uma tabela parecida. Selecione uma ou escreva “usar <id>”.",
          suggestions,
          suggestedPrompts: [
            suggestions[0]?.id ? `usar ${suggestions[0].id}` : null,
            suggestions[0]?.id ? `mostrar detalhes de ${suggestions[0].id}` : null,
            "trocar tabela",
          ].filter(Boolean),
        });
        return;
      }

      if (doc) {
        onSelectTable(doc.id);
        if (directContinue) startFcaBuilder(doc.id);
        return;
      }
    }

    // busca semântica
    if (!index) {
      pushAssistant({
        text: "Índice ainda não está pronto.",
        suggestedPrompts: ["tentar novamente", "trocar tabela"],
      });
      return;
    }

    const results = searchCatalog(index, q, 1000);
    const top = results.slice(0, 20);

    if (!top.length) {
      lastSuggestionsRef.current = [];
      pushAssistant({
        text:
          "Não achei nada bem próximo. Me dá mais uma pista:\n" +
          "- tema (ex.: mineração, biodiversidade, UC...)\n" +
          "- ano\n" +
          "- fonte\n",
        suggestedPrompts: pushSuggestedPromptsForCatalog(),
      });
      return;
    }

    const suggestions = top.map((r) => ({
      id: r.id,
      title: r.title,
      path: r.path,
      year: r.year ?? null,
      source: r.source ?? null,
      reason: buildReason(q, r),
    }));

    lastSuggestionsRef.current = suggestions;

    const refinements = buildRefinementChips(top);

    pushAssistant({
      text: "Encontrei opções próximas. Selecione uma ou refine (ano/categoria/fonte).",
      suggestions,
      suggestedPrompts: refinements.length ? refinements : pushSuggestedPromptsForCatalog(),
    });
  }

  async function onSend(text) {
    const q = safeText(text);
    if (!q) return;

    const lower = q.trim().toLowerCase();

    pushUser(q);

    if (loadingCatalog) {
      pushAssistant({
        text: "Ainda estou carregando o catálogo… tenta de novo em instantes.",
        suggestedPrompts: ["tentar novamente"],
      });
      return;
    }

    if (catalogError) {
      pushAssistant({
        text: `Não consegui carregar o catálogo: ${catalogError}`,
        suggestedPrompts: ["recomeçar", "tentar novamente"],
      });
      return;
    }

    // ✅ comandos globais (independente do modo)
    if (lower === "nova consulta") {
      if (selectedTableId) restartFcaWizardSameTable();
      else {
        pushAssistant({
          text: "Ainda não há tabela selecionada. Primeiro selecione uma tabela no catálogo.",
          suggestedPrompts: pushSuggestedPromptsForCatalog(),
        });
      }
      return;
    }

    // ===================== FCA BUILDER (WIZARD) =====================
    if (mode === "fca_builder") {
      const cmd = parseFcaBuilderText(q);
      handleWizardProgress(cmd, q);
      return;
    }

    // ===================== CATALOG MODE =====================
    const nlu = interpretIntent(q, { mode, selectedTableId });
    const handled = dispatchIntent(nlu, q);
    if (handled) return;

    // se o usuário digitou "detalhar" sem NLU pegar, trate como detalhes da última tabela
    if (lower === "detalhar" && (selectedDoc || lastSuggestionsRef.current?.length)) {
      showDetailsFlow(q);
      return;
    }

    if (lower === "trocar tabela") {
      goBackToCatalog();
      return;
    }

    // fallback: busca catálogo
    catalogSearchPipeline(q);
  }

  return (
    <div className="chat-page">
      <div className="chat-container">
        <ChatMessageList
          messages={messages}
          typedDone={typedDone}
          lastAssistantId={lastAssistantId}
          markDone={markDone}
          bottomRef={bottomRef}
          loadingCatalog={loadingCatalog}
          onSelectTable={(id) => {
            onSelectTable(id);
            scrollToBottom();
          }}
          onSuggestPrompt={(p) => setPrefill(String(p || ""))}
          onTickScroll={scrollToBottom}
        />

        <ChatInputBar
          disabled={loadingCatalog}
          mode={mode}
          sending={sending}
          onSend={onSend}
          onReset={resetChat}
          externalValue={prefill}
          onExternalValueConsumed={() => setPrefill("")}
        />

        {catalogError ? <div className="chat-error">Erro: {catalogError}</div> : null}
      </div>
    </div>
  );
}
