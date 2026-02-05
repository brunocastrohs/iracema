// src/features/Chat/index.js
import { useEffect, useRef, useState } from "react";
import "./styles.css";

import ChatMessageList from "./components/ChatMessageList";
import ChatInputBar from "./components/ChatInputBar";

import { safeText, formatDetails, resolveTableByText } from "./helpers";
import { searchCatalog, buildReason, buildRefinementChips } from "./catalogEngine";

import { useCatalog } from "./hooks/useCatalog";
import { useAutoScroll } from "./hooks/useAutoScroll";
import { useChatMessages } from "./hooks/useChatMessages";
import { useAskFlow } from "./hooks/useAskFlow";

import { interpretIntent, resolveTargetTable } from "./nlu/intentEngine";

import {
  makeAssistantMessage,
  makeNoTableSelectedMessage,
  makeAskErrorMessage,
  makeAskSuccessMessage,
  removeTrailingLoading,
} from "./domain/messageFactories";

const INITIAL_TEXT =
  "Olá! Fico feliz em lhe fornecer informações sobre a nossa base de dados. \n\n" +
  "Me diga o que você quer encontrar no catálogo (tema, palavra chave, ano, fonte). " +
  "Eu vou sugerir as fontes de dados mais próximas e explicar o porquê.\n\n" +
  "Dica: você também pode digitar o título ou o nome de uma camada da PEDEA para selecionar direto.";

export default function Chat() {
  // catalog
  const { loadingCatalog, catalogError, docs, index } = useCatalog();

  // scrolling
  const { bottomRef, scrollToBottom } = useAutoScroll();

  // contexto de conversa (para “a segunda”, “essa”, etc.)
  const lastSuggestionsRef = useRef([]); // [{id,title,year,source,path,reason...}]

  // prefill do input (sugestões estilo GPT)
  const [prefill, setPrefill] = useState("");

  // messages
  const {
    messages,
    setMessages,
    typedDone,
    markDone,
    lastAssistantId,
    pushUser,
    pushAssistant,
    pushCatalogLoaded,
    replaceRemoveTrailingLoadingAndAppend,
  } = useChatMessages({ initialAssistantText: INITIAL_TEXT });

  // ask flow
  const { runAskWithFallback } = useAskFlow();

  // chat state
  const [mode, setMode] = useState("catalog"); // "catalog" | "ask"
  const [selectedTableId, setSelectedTableId] = useState(null);
  const [sending, setSending] = useState(false);

  // quando catálogo terminar, notifica no chat 1 vez
  useEffect(() => {
    if (!loadingCatalog && !catalogError && docs?.length) {
      const already = messages.some((m) => (m.text || "").startsWith("Catálogo carregado:"));
      if (!already) pushCatalogLoaded(docs.length);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [loadingCatalog, catalogError, docs?.length]);

  // rolagem: sempre que messages mudar, rola pra baixo
  useEffect(() => {
    scrollToBottom();
  }, [messages, scrollToBottom]);

  function resetChat() {
    setMode("catalog");
    setSelectedTableId(null);
    lastSuggestionsRef.current = [];

    setMessages([
      makeAssistantMessage({
        text:
          "Recomeçando nossa conversa!\n\n" +
          "Descreva o que você procura no catálogo (tema, recorte, ano, fonte). " +
          "Eu vou sugerir as tabelas mais próximas e explicar o porquê.\n\n" +
          "Dica: você pode digitar o *título* ou o *identificador_tabela* para selecionar direto.",
        suggestedPrompts: ["buscar: uso do solo", "buscar: biodiversidade", "ano: 2022", "fonte: mapbiomas"],
      }),
      ...(loadingCatalog
        ? []
        : [
          makeAssistantMessage({
            text: `Catálogo ainda está carregado (${docs.length} tabelas ativas). Pode perguntar!`,
            suggestedPrompts: ["buscar: fiscalização", "buscar: unidades de conservação"],
          }),
        ]),
    ]);
  }

  function pushSuggestedPromptsForAsk() {
    return [
      "quais são as colunas mais relevantes?",
      "traga um resumo em 5 tópicos",
      "mostrar uma prévia com 20 linhas",
      "trocar tabela",
    ];
  }

  function onSelectTable(id) {
    const doc = docs.find((d) => d.id === id);
    if (!doc) {
      pushAssistant({
        text: "Não encontrei os detalhes dessa tabela no índice.",
        suggestedPrompts: ["buscar: uso do solo", "trocar tabela"],
      });
      return;
    }

    // atualiza contexto (ajuda “essa”, “a segunda”, etc.)
    lastSuggestionsRef.current = [{ id: doc.id, title: doc.title, year: doc.year, source: doc.source, path: doc.path }];

    pushAssistant({
      text:
        `Eis a fonte de dados compatível:\n\n` +
        `• ${doc.title}\n` +
        `• ${doc.path}\n` +
        (doc.year ? `• Ano: ${doc.year}\n` : "") +
        (doc.source ? `• Fonte: ${doc.source}\n` : "") +
        `\nSe quiser, eu posso detalhar as colunas, ou você já pode começar a perguntar usando essa tabela.`,
      suggestedPrompts: [
        `usar ${doc.id}`,
        `mostrar detalhes de ${doc.id}`,
        "quais colunas existem?",
        "trocar tabela",
      ],
    });
  }

  function continueWithSelected(selectedId) {
    if (!selectedId) return;

    setSelectedTableId(selectedId);
    setMode("ask");

    const doc = docs.find((d) => d.id === selectedId);

    pushAssistant({
      text:
        `Certo. Vou responder usando a tabela:\n\n` +
        `• ${doc?.title ?? selectedId}\n` +
        `• identificador_tabela: ${selectedId}\n\n` +
        `Pode mandar sua pergunta.`,
      suggestedPrompts: pushSuggestedPromptsForAsk(),
    });
  }

  async function handleAsk(question) {
    setSending(true);
    pushAssistant({ text: "Consultando…", isLoading: true });

    try {
      if (!selectedTableId) {
        setMode("catalog");
        replaceRemoveTrailingLoadingAndAppend(makeNoTableSelectedMessage());
        return;
      }

      const result = await runAskWithFallback({
        question,
        table_identifier: selectedTableId,
      });

      setMessages((prev) => {
        const base = removeTrailingLoading(prev);

        if (!result.ok) {
          return [
            ...base,
            {
              ...makeAskErrorMessage(result.usedStrategy, result.error),
              suggestedPrompts: pushSuggestedPromptsForAsk(),
            },
          ];
        }

        if (result.data?.error) {
          return [
            ...base,
            {
              ...makeAskErrorMessage(result.usedStrategy, result.data.error),
              suggestedPrompts: pushSuggestedPromptsForAsk(),
            },
          ];
        }

        // sucesso
        return [
          ...base,
          {
            ...makeAskSuccessMessage(result.data),
            suggestedPrompts: pushSuggestedPromptsForAsk(),
          },
        ];
      });
    } catch (e) {
      setMessages((prev) => [
        ...removeTrailingLoading(prev),
        makeAssistantMessage({
          text: "Erro inesperado ao consultar. Tente novamente.",
          suggestedPrompts: pushSuggestedPromptsForAsk(),
        }),
      ]);
    } finally {
      setSending(false);
    }
  }

  function dispatchIntent(nlu, originalText) {
    // RESET
    if (nlu.intent === "RESET") {
      resetChat();
      return true;
    }

    // HELP
    if (nlu.intent === "HELP") {
      pushAssistant({
        text:
          "Eu te ajudo a encontrar e consultar dados da PEDEA.\n\n" +
          "Como usar:\n" +
          "1) Descreva o que você procura (tema, ano, fonte, recorte)\n" +
          "2) Selecione uma tabela (ex.: 'usar landuse_2021')\n" +
          "3) Faça perguntas sobre a tabela selecionada.\n\n" +
          "Exemplos:\n" +
          "- buscar: uso do solo 2021\n" +
          "- usar landuse_2021\n" +
          "- quais municípios têm maior área?\n",
        suggestedPrompts: ["buscar: uso do solo 2021", "usar landuse_2021", "trocar tabela"],
      });
      return true;
    }

    // SWITCH_TABLE
    if (nlu.intent === "SWITCH_TABLE") {
      setMode("catalog");
      setSelectedTableId(null);
      pushAssistant({
        text: "Certo — vamos escolher outra tabela. Descreva o que você quer encontrar no catálogo.",
        suggestedPrompts: ["buscar: biodiversidade", "ano: 2022", "fonte: mapbiomas"],
      });
      return true;
    }

    // DETAILS
    if (nlu.intent === "DETAILS") {
      const resolved = resolveTargetTable({
        rawText: originalText,
        docs,
        index,
        selectedTableId,
        lastSuggestions: lastSuggestionsRef.current,
      });

      const doc = resolved.kind === "doc"
        ? resolved.doc
        : docs.find((d) => d.id === selectedTableId);

      if (!doc) {
        pushAssistant({
          text:
            "Não consegui identificar qual tabela você quer detalhar.\n" +
            "Você pode colar o id/título, ou selecionar uma opção do catálogo.",
          suggestedPrompts: ["buscar: uso do solo", "trocar tabela"],
        });
        return true;
      }

      setSelectedTableId(doc.id);
      setMode("ask");

      pushAssistant({
        text: formatDetails(doc),
        suggestedPrompts: [
          "consultar todos os idpan e pan",
          "quais são os valores distintos?",
          "traga um resumo em 5 tópicos",
          "trocar tabela",
        ],
      });

      return true;
    }


    // SELECT / SELECT_IMPLICIT
    if (nlu.intent === "SELECT" || nlu.intent === "SELECT_IMPLICIT") {
      const resolved = resolveTargetTable({
        rawText: nlu.entities?.selectionText || originalText,
        docs,
        index,
        selectedTableId,
        lastSuggestions: lastSuggestionsRef.current,
      });

      const doc = resolved.kind === "doc" ? resolved.doc : null;

      if (!doc) {
        setMode("catalog");
        pushAssistant({
          text:
            "Não consegui identificar exatamente qual tabela você quer usar.\n" +
            "Me dê mais um detalhe (tema/ano/fonte) e eu mostro as melhores opções.",
          suggestedPrompts: ["buscar: biodiversidade", "ano: 2022", "fonte: mapbiomas"],
        });
        return true;
      }

      continueWithSelected(doc.id);
      return true;
    }

    // ASK_QUESTION
    if (nlu.intent === "ASK_QUESTION") {
      if (!selectedTableId) {
        setMode("catalog");
        pushAssistant({
          text:
            "Antes de consultar, preciso que você selecione uma tabela do catálogo (ou cole o id/título).",
          suggestedPrompts: ["buscar: uso do solo 2021", "usar landuse_2021", "trocar tabela"],
        });
        return true;
      }
      handleAsk(originalText);
      return true;
    }

    // REFINE -> transforma em query e cai no pipeline de busca
    if (nlu.intent === "REFINE") {
      setMode("catalog");
      const parts = [];
      if (nlu.entities?.categoryHint) parts.push(nlu.entities.categoryHint);
      if (nlu.entities?.year) parts.push(`ano ${nlu.entities.year}`);
      if (nlu.entities?.sourceHint) parts.push(`fonte ${nlu.entities.sourceHint}`);

      const mergedQuery = parts.join(" ").trim();
      if (mergedQuery) {
        catalogSearchPipeline(mergedQuery);
        return true;
      }
      return false;
    }

    return false; // não tratou
  }

  function catalogSearchPipeline(query) {
    const q = safeText(query);
    if (!q) return;

    // modo catalog: tenta seleção por texto (id/título)
    const { doc, directContinue, ambiguousDocs } = resolveTableByText({ query: q, docs, index });

    if (ambiguousDocs?.length) {
      const suggestions = ambiguousDocs.slice(0, 8).map((d) => ({
        id: d.id,
        title: d.title,
        path: d.path,
        year: d.year ?? null,
        source: d.source ?? null,
        reason: "nome/título parecido",
      }));

      lastSuggestionsRef.current = suggestions;

      pushAssistant({
        text:
          "Encontrei mais de uma tabela parecida. Você pode selecionar uma, ou escrever “usar <id>”.",
        suggestions,
        suggestedPrompts: [
          suggestions[0]?.id ? `usar ${suggestions[0].id}` : null,
          suggestions[0]?.id ? `mostrar detalhes de ${suggestions[0].id}` : null,
          "ano: 2022",
          "trocar tabela",
        ].filter(Boolean),
      });
      return;
    }

    if (doc) {
      // seleção direta
      onSelectTable(doc.id);
      if (directContinue) continueWithSelected(doc.id);
      return;
    }

    // busca local (MiniSearch)
    if (!index) {
      pushAssistant({
        text: "Índice ainda não está pronto.",
        suggestedPrompts: ["tentar novamente", "trocar tabela"],
      });
      return;
    }

    const results = searchCatalog(index, q, 1000);
    const top = results.slice(0, 6);

    if (!top.length) {
      lastSuggestionsRef.current = [];
      pushAssistant({
        text:
          "Não achei nada bem próximo. Me dá mais uma pista:\n" +
          "- tema (ex.: biodiversidade, UC, fiscalização...)\n" +
          "- ano\n" +
          "- município/UF\n",
        suggestedPrompts: ["biodiversidade", "fiscalização", "ano: 2022", "fonte: mapbiomas"],
      });
      return;
    }

    const suggestions = top.slice(0, 8).map((r) => ({
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
      text: "Encontrei opções próximas. Selecione uma ou refine sua busca (ano/categoria/fonte).",
      suggestions,
      suggestedPrompts: refinements.length
        ? refinements
        : [
          suggestions[0]?.id ? `usar ${suggestions[0].id}` : null,
          "ano: 2022",
          "categoria: biodiversidade",
          "fonte: mapbiomas",
          "trocar tabela",
        ].filter(Boolean),
    });
  }

  function onSend(text) {
    const q = safeText(text);
    if (!q) return;

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

    // 1) interpreta intenção
    const nlu = interpretIntent(q, { mode, selectedTableId });

    // 2) se for algo tratado por intenção, encerra
    const handled = dispatchIntent(nlu, q);
    if (handled) return;

    // 3) fallback: pipeline conforme modo
    if (mode === "ask") {
      handleAsk(q);
      return;
    }

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
