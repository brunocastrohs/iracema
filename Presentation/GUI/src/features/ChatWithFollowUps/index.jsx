// src/features/Chat/index.js
import { useEffect, useState } from "react";
import "./styles.css";

import ChatMessageList from "./components/ChatMessageList";
import ChatInputBar from "./components/ChatInputBar";

import { safeText, formatDetails, resolveTableByText } from "./helpers";
import { searchCatalog, buildReason, buildRefinementChips } from "./catalogEngine";

import { useCatalog } from "./hooks/useCatalog";
import { useAutoScroll } from "./hooks/useAutoScroll";
import { useChatMessages } from "./hooks/useChatMessages";
import { useAskFlow } from "./hooks/useAskFlow";

import { parseQuickCommand } from "./domain/chatIntents";
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

export default function ChatWithFollowUps() {
  // catalog
  const { loadingCatalog, catalogError, docs, index } = useCatalog();

  // scrolling
  const { bottomRef, scrollToBottom } = useAutoScroll();

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
      // evita duplicar caso o hook re-renderize
      // só adiciona se ainda não existe uma mensagem “Catálogo carregado”
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

    setMessages([
      makeAssistantMessage({
        text:
          "Recomeçando nossa conversa!\n\n" +
          "Descreva o que você procura no catálogo (tema, recorte, ano, fonte). " +
          "Eu vou sugerir as tabelas mais próximas e explicar o porquê.\n\n" +
          "Dica: você pode digitar o *título* ou o *identificador_tabela* para selecionar direto.",
        followUps: [],
      }),
      ...(loadingCatalog
        ? []
        : [
          makeAssistantMessage({
            text: `Catálogo ainda está carregado (${docs.length} tabelas ativas). Pode perguntar!`,
          }),
        ]),
    ]);
  }

  function onSelectTable(id) {
    const doc = docs.find((d) => d.id === id);
    if (!doc) {
      pushAssistant({ text: "Não encontrei os detalhes dessa tabela no índice." });
      return;
    }

    pushAssistant({
      text:
        `Encontrei a seguinte fonte de dados para você:\n\n` +
        `• Camada ${doc.title}\n` +
        `• ${doc.path}\n` +
        (doc.year ? `• Ano: ${doc.year}\n` : "") +
        (doc.source ? `• Fonte: ${doc.source}\n` : "") +
        `\nQuer ver as colunas e a descrição completa, ou confirmar a camada para a consulta?`,
      followUps: ["Ver detalhes", "Confirmar"],
      context: { selectedId: doc.id },
    });
  }

  function continueWithSelected(selectedId) {
    if (!selectedId) return;

    setSelectedTableId(selectedId);
    setMode("ask");

    const doc = docs.find((d) => d.id === selectedId);

    pushAssistant({
      text:
        `Ok. A partir de agora vou responder usando a tabela:\n\n` +
        `• ${doc?.title ?? selectedId}\n` +
        `• identificador_tabela: ${selectedId}\n\n` +
        `Pode mandar sua pergunta.`,
      followUps: ["Ver detalhes", "Trocar tabela"],
    });
  }

  function getLastAssistantMessageWithFollowUps(msgs) {
    for (let i = msgs.length - 1; i >= 0; i--) {
      if (msgs[i]?.role === "assistant" && Array.isArray(msgs[i]?.followUps) && msgs[i].followUps.length) {
        return msgs[i];
      }
    }
    return null;
  }

  function tryMatchTypedFollowUp(typedText) {
    const t = safeText(typedText);
    if (!t) return null;

    const lastWith = getLastAssistantMessageWithFollowUps(messages);
    if (!lastWith) return null;

    const found = lastWith.followUps.find((fu) => fu.toLowerCase() === t.toLowerCase());
    if (!found) return null;

    return { label: found, context: lastWith.context };
  }

  function handleFollowUpClick(label, context) {
    const ctxId = context?.selectedId;
    const effectiveId = ctxId || selectedTableId;

    // 1) Ações globais (funcionam em qualquer modo)
    if (label === "Trocar tabela") {
      setMode("catalog");
      setSelectedTableId(null);
      pushAssistant({
        text: "Beleza — vamos escolher outra tabela. Descreva o que você quer encontrar no catálogo.",
      });
      return;
    }

    // opcional: remover "Nova pergunta" (recomendado), mas se ficar:
    if (label === "Nova pergunta") {
      // no modo ask, só reforça o prompt
      if (mode === "ask") {
        pushAssistant({ text: "Pode mandar sua pergunta." });
      }
      return;
    }

    // 2) Detalhes
    if (label === "Ver detalhes") {
      if (!effectiveId) {
        pushAssistant({ text: "Não há tabela selecionada para mostrar detalhes." });
        return;
      }

      const doc = docs.find((d) => d.id === effectiveId);
      if (!doc) {
        pushAssistant({ text: "Não encontrei os detalhes dessa tabela." });
        return;
      }

      pushAssistant({
        text: formatDetails(doc),
        followUps: mode === "ask" ? ["Trocar tabela"] : ["Confirmar", "Trocar tabela"],
        context: { selectedId: effectiveId },
      });
      return;
    }

    // 3) Confirmar (alias de Selecionar)
    if (label === "Confirmar" || label === "Selecionar") {
      const idToUse = ctxId || effectiveId;
      if (!idToUse) return;
      continueWithSelected(idToUse);
      return;
    }

    // 4) Refinamentos (se ainda não implementou, no mínimo não entra em loop)
    if (label === "Refinar por ano") {
      pushAssistant({ text: "Diga o ano (ex.: 2024) ou escreva: Ano: 2024" });
      return;
    }
    if (label === "Refinar por categoria") {
      pushAssistant({ text: "Diga a categoria/tema (ex.: Fiscalização Ambiental, Biodiversidade...)" });
      return;
    }
    if (label === "Ver mais resultados") {
      pushAssistant({ text: "Ok — refine com mais termos (tema, ano, município/UF) para eu abrir mais opções." });
      return;
    }

    // fallback: se for um texto comum (raro em chip), manda como pergunta normal
    onSend(label);
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
          return [...base, makeAskErrorMessage(result.usedStrategy, result.error)];
        }

        if (result.data?.error) {
          return [...base, makeAskErrorMessage(result.usedStrategy, result.data.error)];
        }

        return [...base, makeAskSuccessMessage(result.data)];
      });
    } catch (e) {
      setMessages((prev) => [
        ...removeTrailingLoading(prev),
        makeAssistantMessage({ text: "Erro inesperado ao consultar. Tente novamente." }),
      ]);
    } finally {
      setSending(false);
    }
  }

  function onSend(text) {
    const q = safeText(text);
    if (!q) return;

    // se digitou exatamente o texto de um follow-up, executa como clique
    const match = tryMatchTypedFollowUp(q);
    if (match) {
      pushUser(q);
      handleFollowUpClick(match.label, match.context);
      return;
    }

    pushUser(q);

    if (loadingCatalog) {
      pushAssistant({ text: "Ainda estou carregando o catálogo… tenta de novo em instantes." });
      return;
    }
    if (catalogError) {
      pushAssistant({ text: `Não consegui carregar o catálogo: ${catalogError}` });
      return;
    }

    // comandos rápidos
    const cmd = parseQuickCommand(q);
    if (cmd.type === "SWITCH_TABLE") {
      setMode("catalog");
      setSelectedTableId(null);
      pushAssistant({ text: "Beleza — vamos escolher outra tabela. Descreva o que você quer encontrar no catálogo." });
      return;
    }

    if (mode === "ask") {
      if (cmd.type === "NEW_QUESTION") {
        pushAssistant({ text: "Pode mandar sua pergunta." });
        return;
      }
      handleAsk(q);
      return;
    }

    // modo catalog: tenta seleção por texto
    const { doc, directContinue, ambiguousDocs } = resolveTableByText({ query: q, docs, index });

    if (ambiguousDocs?.length) {
      pushAssistant({
        text: "Achei mais de uma tabela que pode ser isso. Qual delas você quer usar?",
        suggestions: ambiguousDocs.slice(0, 8).map((d) => ({
          id: d.id,
          title: d.title,
          path: d.path,
          year: d.year ?? null,
          source: d.source ?? null,
          reason: "nome/título parecido",
        })),
        followUps: ["Refinar por ano", "Refinar por categoria", "Trocar tabela"],
      });
      return;
    }

    if (doc) {
      onSelectTable(doc.id);
      if (directContinue) continueWithSelected(doc.id);
      return;
    }

    // busca local (MiniSearch)
    if (!index) {
      pushAssistant({ text: "Índice ainda não está pronto." });
      return;
    }

    const results = searchCatalog(index, q, 1000);
    const top = results.slice(0, 6);

    if (!top.length) {
      pushAssistant({
        text:
          "Não achei nada bem próximo. Me dá mais uma pista:\n" +
          "- tema (ex.: biodiversidade, UC, fiscalização...)\n" +
          "- ano\n" +
          "- município/UF\n",
        followUps: ["Biodiversidade", "Fiscalização", "Ano: 2022", "Ano: 2025"],
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

    const refinements = buildRefinementChips(top);

    pushAssistant({
      text: "Encontrei estas opções mais próximas. Você pode selecionar uma tabela, ou refinar:",
      suggestions,
      followUps: refinements.length
        ? refinements
        : ["Refinar por categoria", "Refinar por ano", "Ver mais resultados"],
    });
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
          onFollowUp={handleFollowUpClick}
          onTickScroll={scrollToBottom}
        />

        <ChatInputBar
          disabled={loadingCatalog}
          mode={mode}
          sending={sending}
          onSend={onSend}
          onReset={resetChat}
        />

        {catalogError ? <div className="chat-error">Erro: {catalogError}</div> : null}
      </div>
    </div>
  );
}
