// src/features/Chat/index.js
import { useEffect, useMemo, useRef, useState } from "react";
import { getCatalog, askChat } from "./service";
import {
  buildDocs,
  buildIndex,
  searchCatalog,
  buildReason,
  buildRefinementChips,
} from "./catalogEngine";
import "./styles.css";
import avatarIracema from "../../_assets/images/avatar_iracema.png";


import {
  now,
  safeText,
  formatDetails,
  resolveTableByText,
} from "./helpers";

export default function Chat() {
  const [loadingCatalog, setLoadingCatalog] = useState(true);
  const [catalogError, setCatalogError] = useState("");

  const [docs, setDocs] = useState([]);
  const [index, setIndex] = useState(null);

  const [mode, setMode] = useState("catalog"); // "catalog" | "ask"
  const [selectedTableId, setSelectedTableId] = useState(null);

  const didLoadCatalogRef = useRef(false);

  const [sending, setSending] = useState(false);

  const [typedDone, setTypedDone] = useState({});

  function markDone(id) {
    if (!id) return;
    setTypedDone((m) => (m[id] ? m : { ...m, [id]: true }));
  }

  const [messages, setMessages] = useState([
    {
      id: `m_${Date.now()}_${Math.random().toString(16).slice(2)}`,
      role: "assistant",
      ts: now(),
      text:
        "Olá! Fico feliz em lhe fornecer informações sobre a nossa base de dados. \n\n" +
        "Me diga o que você quer encontrar no catálogo (tema, palavra chave, ano, fonte). " +
        "Eu vou sugerir as fontes de dados mais próximas e explicar o porquê.\n\n" +
        "Dica: você também pode digitar o título ou o nome de uma camada da PEDEA para selecionar direto.",
      followUps: [
        "Ex.: uso do solo 2021",
        "Ex.: biodiversidade anfíbios",
        "Ex.: unidades de conservação",
      ],
    },
  ]);

  const lastAssistantId = useMemo(() => {
    for (let i = messages.length - 1; i >= 0; i--) {
      if (messages[i]?.role === "assistant" && !messages[i]?.isLoading) return messages[i].id;
    }
    return null;
  }, [messages]);

  const [input, setInput] = useState("");
  const bottomRef = useRef(null);

  const inputRef = useRef(null);

  function focusInput() {
    // pequeno timeout ajuda em casos onde um rerender ocorre logo após o click
    setTimeout(() => {
      inputRef.current?.focus();
    }, 0);
  }

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  useEffect(() => {
    (async () => {
      if (didLoadCatalogRef.current) return;
      didLoadCatalogRef.current = true;

      setLoadingCatalog(true);
      setCatalogError("");

      const { ok, data, error, meta } = await getCatalog();
      if (!ok) {
        setCatalogError(error || "Falha ao carregar catálogo.");
        setLoadingCatalog(false);
        return;
      }

      const builtDocs = buildDocs(data);
      const builtIndex = buildIndex(builtDocs);

      setDocs(builtDocs);
      setIndex(builtIndex);
      setLoadingCatalog(false);

      setMessages((m) => [
        ...m,
        {
          id: newMsgId(),
          role: "assistant",
          ts: now(),
          text: `Catálogo carregado: ${meta?.count ?? builtDocs.length} tabelas ativas. Pode perguntar!`,
        },
      ]);
    })();
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  function newMsgId() {
    return `m_${Date.now()}_${Math.random().toString(16).slice(2)}`;
  }

  function pushUser(text) {
    setMessages((m) => [...m, { id: newMsgId(), role: "user", ts: now(), text }]);
  }

  function pushAssistant(payload) {
    setMessages((m) => [...m, { id: newMsgId(), role: "assistant", ts: now(), ...payload }]);
  }

  function resetChat() {
    setMode("catalog");
    setSelectedTableId(null);
    setInput("");
    focusInput();
    setMessages([
      {
        id: newMsgId(),
        role: "assistant",
        ts: now(),
        text:
          "Recomeçando nossa conversa!\n\n" +
          "Descreva o que você procura no catálogo (tema, recorte, ano, fonte). " +
          "Eu vou sugerir as tabelas mais próximas e explicar o porquê.\n\n" +
          "Dica: você pode digitar o *título* ou o *identificador_tabela* para selecionar direto.",
        followUps: ["Ex.: uso do solo 2021", "Ex.: biodiversidade anfíbios", "Ex.: unidades de conservação"],
      },
      ...(loadingCatalog
        ? []
        : [
          {
            id: newMsgId(),
            role: "assistant",
            ts: now(),
            text: `Catálogo ainda está carregado (${docs.length} tabelas ativas). Pode perguntar!`,
          },
        ]),
    ]);
  }

  async function handleAskFlow(question) {
    setSending(true);
    focusInput();

    // 1) mostra 1 único bubble de loading
    pushAssistant({ text: "Consultando…", isLoading: true });

    try {
      if (!selectedTableId) {
        setMode("catalog");
        // remove o loading e informa
        setMessages((prev) => [
          ...removeTrailingLoading(prev),
          {
            id: newMsgId(),
            role: "assistant",
            ts: now(),
            text: "Você ainda não selecionou uma tabela. Primeiro escolha uma tabela do catálogo.",
          },
        ]);
        return;
      }

      const explain = localStorage.getItem("iracema_explain") === "true";
      const strategy = localStorage.getItem("iracema_strategy") || "ask/fc";

      const { ok, data, error } = await askChat({
        question,
        table_identifier: selectedTableId,
        top_k: 1000,
        explain,
        strategy,
      });

      setMessages((prev) => {
        const base = removeTrailingLoading(prev);

        if (!ok) {
          return [
            ...base,
            { id: newMsgId(), role: "assistant", ts: now(), text: `Erro: ${error || "falha no /chat/ask"}` },
          ];
        }

        if (data?.error) {
          return [
            ...base,
            { id: newMsgId(), role: "assistant", ts: now(), text: `Erro: ${data.error}` },
          ];
        }

        return [
          ...base,
          {
            id: newMsgId(),
            role: "assistant",
            ts: now(),
            text: safeText(data?.answer_text) || "Sem resposta textual.",
            preview: Array.isArray(data?.result_preview) ? data.result_preview : [],
            followUps: ["Nova pergunta", "Trocar tabela"],
          },
        ];
      });
    } catch (e) {
      setMessages((prev) => [
        ...removeTrailingLoading(prev),
        { id: newMsgId(), role: "assistant", ts: now(), text: "Erro inesperado ao consultar. Tente novamente." },
      ]);
    } finally {
      setSending(false);
      focusInput();
    }
  }

  function removeTrailingLoading(list) {
    const copy = [...list];
    while (copy.length) {
      const last = copy[copy.length - 1];
      if (last?.role === "assistant" && last?.isLoading) copy.pop();
      else break;
    }
    return copy;
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
        `\nQuer ver as colunas e a descrição completa, ou selecionar a camada para a consulta?`,
      followUps: ["Ver detalhes", "Selecionar"],
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

  function handleFollowUpClick(label, context) {
    focusInput();

    const ctxId = context?.selectedId;
    const effectiveId = ctxId || selectedTableId;

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
        followUps: mode === "ask" ? ["Nova pergunta", "Trocar tabela"] : ["Selecionar", "Trocar tabela"],
        context: { selectedId: effectiveId },
      });
      return;
    }

    if (label === "Selecionar") {
      if (!ctxId) return;
      continueWithSelected(ctxId);
      return;
    }

    onSend(label);
  }

  const scrollToBottom = () => {
    // garante que o DOM atualizou antes de scrollar
    requestAnimationFrame(() => {
      bottomRef.current?.scrollIntoView({ behavior: "smooth" });
    });
  };

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

    const lastWithFollowUps = getLastAssistantMessageWithFollowUps(messages);
    if (!lastWithFollowUps) return null;

    // match case-insensitive, mas mantém o label original
    const found = lastWithFollowUps.followUps.find((fu) => fu.toLowerCase() === t.toLowerCase());
    if (!found) return null;

    return { label: found, context: lastWithFollowUps.context };
  }

  function onSend(textFromChip) {
    const q = safeText(textFromChip ?? input);
    if (!q) return;

    const match = tryMatchTypedFollowUp(q);
    if (match && !textFromChip) {
      pushUser(q);
      setInput("");
      focusInput();
      handleFollowUpClick(match.label, match.context);
      return;
    }

    pushUser(q);
    setInput("");
    focusInput();

    if (loadingCatalog) {
      pushAssistant({ text: "Ainda estou carregando o catálogo… tenta de novo em instantes." });
      return;
    }
    if (catalogError) {
      pushAssistant({ text: `Não consegui carregar o catálogo: ${catalogError}` });
      return;
    }

    // comandos rápidos
    if (q.toLowerCase() === "trocar tabela") {
      setMode("catalog");
      setSelectedTableId(null);
      pushAssistant({
        text: "Beleza — vamos escolher outra tabela. Descreva o que você quer encontrar no catálogo.",
      });
      return;
    }

    // Se já está no modo ASK, manda para /chat/ask
    if (mode === "ask") {
      if (q.toLowerCase() === "nova pergunta") {
        pushAssistant({ text: "Pode mandar sua pergunta." });
        return;
      }
      handleAskFlow(q);
      return;
    }

    // Modo catalog: tenta seleção por texto (título/ID) + intenção ("usar/continuar com")
    const { doc, directContinue, ambiguousDocs } = resolveTableByText({ query: q, docs, index });

    if (ambiguousDocs?.length) {
      pushAssistant({
        text:
          "Achei mais de uma tabela que pode ser isso. Qual delas você quer usar?",
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
      // Seleciona sem clique
      onSelectTable(doc.id);

      // Se a frase foi explícita ("usar/continuar com"), já entra em ASK automaticamente
      if (directContinue) {
        continueWithSelected(doc.id);
      }
      return;
    }

    // Modo catalog: busca local (MiniSearch)
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
        <div className="chat-messages">
          {messages.map((msg, idx) => {
            const canShowExtras =
              msg.role !== "assistant" ||
              msg.isLoading ||
              typedDone[msg.id] ||
              msg.id !== lastAssistantId;

            return (
              <div
                key={msg.id ?? idx}
                className={`chat-row ${msg.role === "user" ? "is-user" : "is-assistant"}`}
              >
                {msg.role === "assistant" ? (
                  <div className="chat-avatar" title="Iracema">
                    <img src={avatarIracema} alt="Iracema" />
                  </div>
                ) : null}

                <div className={`chat-bubble ${msg.role === "user" ? "user" : "assistant"}`}>

                  <div className="chat-text">
                    {msg.role === "assistant" && !msg.isLoading ? (
                      <TypewriterText
                        text={msg.text}
                        animate={msg.id === lastAssistantId && !typedDone[msg.id]}
                        speed={10}
                        onTick={scrollToBottom}
                        onDone={() => {
                          markDone(msg.id);
                          scrollToBottom();
                        }}
                      />
                    ) : (
                      msg.text
                    )}
                  </div>

                  {msg.isLoading ? (
                    <div className="chat-loading-row">
                      <i className="pi pi-spin pi-spinner chat-loading-icon" />
                      <span>Processando…</span>
                    </div>
                  ) : null}

                  {canShowExtras && Array.isArray(msg.preview) && msg.preview.length ? (
                    <div className="result-preview">
                      <div className="result-preview-title">Prévia do resultado</div>

                      <div className="result-preview-table-wrap">
                        <table className="result-preview-table">
                          <thead>
                            <tr>
                              {Object.keys(msg.preview[0] || {}).map((k) => (
                                <th key={k}>{k}</th>
                              ))}
                            </tr>
                          </thead>
                          <tbody>
                            {msg.preview.map((row, i) => (
                              <tr key={i}>
                                {Object.keys(msg.preview[0] || {}).map((k) => (
                                  <td key={k}>{String(row?.[k] ?? "")}</td>
                                ))}
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  ) : null}

                  {canShowExtras && msg.suggestions?.length ? (
                    <div className="suggestions">
                      {msg.suggestions.map((s) => (
                        <div key={s.id} className="suggestion-card">
                          <div className="suggestion-title">{s.title}</div>
                          <div className="suggestion-path">{s.path}</div>
                          <div className="suggestion-meta">
                            {s.year ? <span className="tag">Ano: {s.year}</span> : null}
                            {s.source ? (
                              <span className="tag tag-long" title={s.source}>
                                Fonte: {s.source}
                              </span>
                            ) : null}
                            <span className="tag tag-outline">{s.reason}</span>
                          </div>

                          <div className="suggestion-actions">
                            <button onMouseDown={(e) => e.preventDefault()} className="btn-mini" onClick={() => { onSelectTable(s.id); focusInput(); }}>
                              Selecionar
                            </button>
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : null}

                  {canShowExtras && msg.followUps?.length ? (
                    <div className="followups">
                      {msg.followUps.map((f) => (
                        <button
                          onMouseDown={(e) => e.preventDefault()}
                          key={f}
                          className="chip"
                          onClick={() => handleFollowUpClick(f, msg.context)}
                        >
                          {f}
                        </button>
                      ))}
                    </div>
                  ) : null}
                </div>
              </div>
            )
          }
          )}

          {loadingCatalog ? (
            <div className="chat-row is-assistant">
              <div className="chat-avatar" title="Iracema">
                <img src={avatarIracema} alt="Iracema" />
              </div>

              <div className="chat-bubble assistant">
                <div className="chat-text">
                  <i className="pi pi-spin pi-spinner chat-loading-icon inline" />
                  Carregando catálogo…
                </div>
              </div>
            </div>
          ) : null}
          <div ref={bottomRef} />
        </div>

        <div className="chat-inputbar">


          {loadingCatalog && (
            <i className="pi pi-spin pi-spinner chat-loading-icon" />
          )}

          <input
            className="chat-input" ref={inputRef}

            placeholder={
              loadingCatalog
                ? "Carregando catálogo..."
                : mode === "ask"
                  ? "Digite sua pergunta sobre a tabela selecionada…"
                  : "Descreva o que você procura no catálogo…"
            }
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => (e.key === "Enter" ? onSend() : null)}
            disabled={loadingCatalog}
          />

          <button
            onMouseDown={(e) => e.preventDefault()}
            className="chat-reset"
            onClick={resetChat}
            disabled={loadingCatalog && !docs.length}
            title="Resetar conversa"
          >
            <i className="pi pi-refresh" /> Recomeçar
          </button>

          <button onMouseDown={(e) => e.preventDefault()} className="chat-send" onClick={() => onSend()} disabled={loadingCatalog || sending}>
            {sending ? (
              <i className="pi pi-spin pi-spinner" />
            ) : (
              <>
                <i className="pi pi-send" /> Enviar
              </>
            )}
          </button>
        </div>

        {catalogError ? <div className="chat-error">Erro: {catalogError}</div> : null}
      </div>
    </div>
  );
}

function TypewriterText({ text, animate, speed = 22, onDone, onTick }) {
  const [shown, setShown] = useState(animate ? "" : (text || ""));
  const rafRef = useRef(null);
  const lastAtRef = useRef(0);
  const iRef = useRef(0);
  const doneRef = useRef(false);

  // throttle de scroll/tick
  const lastTickRef = useRef(0);
  const TICK_EVERY_MS = 60;

  useEffect(() => {
    doneRef.current = false;
    iRef.current = 0;
    lastAtRef.current = 0;
    lastTickRef.current = 0;
    setShown(animate ? "" : (text || ""));

    if (!animate) {
      onDone?.();
      return;
    }

    const full = text || "";

    const tick = (t) => {
      if (doneRef.current) return;

      if (!lastAtRef.current) lastAtRef.current = t;
      const elapsed = t - lastAtRef.current;

      const step = Math.floor(elapsed / speed);

      if (step > 0) {
        // mantém resto de tempo (não perde precisão)
        lastAtRef.current = lastAtRef.current + step * speed;

        iRef.current = Math.min(full.length, iRef.current + step);
        setShown(full.slice(0, iRef.current));

        // chama onTick (throttled)
        if (onTick) {
          if (!lastTickRef.current) lastTickRef.current = t;
          if (t - lastTickRef.current >= TICK_EVERY_MS) {
            lastTickRef.current = t;
            onTick();
          }
        }

        if (iRef.current >= full.length) {
          doneRef.current = true;
          onDone?.();
          return;
        }
      }

      rafRef.current = requestAnimationFrame(tick);
    };

    rafRef.current = requestAnimationFrame(tick);
    return () => {
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
    };
  }, [text, animate, speed, onDone, onTick]);

  return <span>{shown}</span>;
}

