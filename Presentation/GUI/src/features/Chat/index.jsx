// src/features/Chat/index.js
import { useEffect, useRef, useState } from "react";
import { getCatalog, askChat } from "./service";
import {
  buildDocs,
  buildIndex,
  searchCatalog,
  buildReason,
  buildRefinementChips,
} from "./catalogEngine";
import "./styles.css";

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

  const [messages, setMessages] = useState([
    {
      role: "assistant",
      ts: now(),
      text:
        "Me diga o que você quer encontrar no catálogo (tema, recorte, ano, fonte). " +
        "Eu vou sugerir as tabelas mais próximas e explicar o porquê.\n\n" +
        "Dica: você também pode digitar o título ou o nome de uma camada da PEDEA para selecionar direto.",
      followUps: [
        "Ex.: uso do solo 2021",
        "Ex.: biodiversidade anfíbios",
        "Ex.: unidades de conservação",
      ],
    },
  ]);

  const [input, setInput] = useState("");
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  useEffect(() => {
    (async () => {
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
          role: "assistant",
          ts: now(),
          text: `Catálogo carregado: ${meta?.count ?? builtDocs.length} tabelas ativas. Pode perguntar!`,
        },
      ]);
    })();
  }, []);

  function pushUser(text) {
    setMessages((m) => [...m, { role: "user", ts: now(), text }]);
  }

  function pushAssistant(payload) {
    setMessages((m) => [...m, { role: "assistant", ts: now(), ...payload }]);
  }

  function resetChat() {
    setMode("catalog");
    setSelectedTableId(null);
    setInput("");

    setMessages([
      {
        role: "assistant",
        ts: now(),
        text:
          "Chat resetado. Descreva o que você procura no catálogo (tema, recorte, ano, fonte). " +
          "Eu vou sugerir as tabelas mais próximas e explicar o porquê.\n\n" +
          "Dica: você pode digitar o *título* ou o *identificador_tabela* para selecionar direto.",
        followUps: ["Ex.: uso do solo 2021", "Ex.: biodiversidade anfíbios", "Ex.: unidades de conservação"],
      },
      ...(loadingCatalog
        ? []
        : [
            {
              role: "assistant",
              ts: now(),
              text: `Catálogo ainda está carregado (${docs.length} tabelas ativas). Pode perguntar!`,
            },
          ]),
    ]);
  }

  async function handleAskFlow(question) {
    if (!selectedTableId) {
      pushAssistant({
        text: "Você ainda não selecionou uma tabela. Primeiro escolha uma tabela do catálogo.",
      });
      setMode("catalog");
      return;
    }

    pushAssistant({ text: "Consultando…" });

    const { ok, data, error } = await askChat({
      question,
      table_identifier: selectedTableId,
      top_k: 1000,
    });

    setMessages((prev) => {
      const copy = [...prev];
      const last = copy[copy.length - 1];
      if (last?.role === "assistant" && last?.text === "Consultando…") copy.pop();

      if (!ok) {
        copy.push({
          role: "assistant",
          ts: now(),
          text: `Erro: ${error || "falha no /chat/ask"}`,
        });
      } else if (data?.error) {
        copy.push({ role: "assistant", ts: now(), text: `Erro: ${data.error}` });
      } else {
        copy.push({
          role: "assistant",
          ts: now(),
          text: safeText(data?.answer_text) || "Sem resposta textual.",
          preview: Array.isArray(data?.result_preview) ? data.result_preview : [],
          followUps: ["Nova pergunta", "Trocar tabela"],
        });
      }

      return copy;
    });
  }

  function onSelectTable(id) {
    const doc = docs.find((d) => d.id === id);
    if (!doc) {
      pushAssistant({ text: "Não encontrei os detalhes dessa tabela no índice." });
      return;
    }

    pushAssistant({
      text:
        `Tabela selecionada:\n` +
        `• ${doc.title}\n` +
        `• ${doc.path}\n` +
        (doc.year ? `• Ano: ${doc.year}\n` : "") +
        (doc.source ? `• Fonte: ${doc.source}\n` : "") +
        `\nQuer ver as colunas e a descrição completa, ou seguir para a consulta?`,
      followUps: ["Ver detalhes", "Continuar"],
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
        `Ok. A partir de agora vou responder usando a tabela:\n` +
        `• ${doc?.title ?? selectedId}\n` +
        `• identificador_tabela: ${selectedId}\n\n` +
        `Pode mandar sua pergunta.`,
      followUps: ["Trocar tabela"],
    });
  }

  function handleFollowUpClick(label, context) {
    const selectedId = context?.selectedId;

    if (label === "Ver detalhes") {
      if (!selectedId) return;
      const doc = docs.find((d) => d.id === selectedId);
      if (!doc) {
        pushAssistant({ text: "Não encontrei os detalhes dessa tabela." });
        return;
      }
      pushAssistant({
        text: formatDetails(doc),
        followUps: ["Continuar", "Trocar tabela"],
        context: { selectedId },
      });
      return;
    }

    if (label === "Continuar") {
      if (!selectedId) return;
      continueWithSelected(selectedId);
      return;
    }

    onSend(label);
  }

  function onSend(textFromChip) {
    const q = safeText(textFromChip ?? input);
    if (!q) return;

    pushUser(q);
    setInput("");

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
          {messages.map((msg, idx) => (
            <div
              key={idx}
              className={`chat-bubble-row ${msg.role === "user" ? "is-user" : "is-assistant"}`}
            >
              <div className={`chat-bubble ${msg.role === "user" ? "user" : "assistant"}`}>
                <div className="chat-text">{msg.text}</div>

                {Array.isArray(msg.preview) && msg.preview.length ? (
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

                {msg.suggestions?.length ? (
                  <div className="suggestions">
                    {msg.suggestions.map((s) => (
                      <div key={s.id} className="suggestion-card">
                        <div className="suggestion-title">{s.title}</div>
                        <div className="suggestion-path">{s.path}</div>
                        <div className="suggestion-meta">
                          {s.year ? <span className="tag">Ano: {s.year}</span> : null}
                          {s.source ? <span className="tag tag-long">Fonte: {s.source}</span> : null}
                          <span className="tag tag-outline">{s.reason}</span>
                        </div>

                        <div className="suggestion-actions">
                          <button className="btn-mini" onClick={() => onSelectTable(s.id)}>
                            Selecionar
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : null}

                {msg.followUps?.length ? (
                  <div className="followups">
                    {msg.followUps.map((f) => (
                      <button
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
          ))}
          <div ref={bottomRef} />
        </div>

        <div className="chat-inputbar">
          <input
            className="chat-input"
            placeholder={
              loadingCatalog
                ? "Carregando catálogo..."
                : mode === "ask"
                ? "Digite sua pergunta sobre a tabela selecionada…"
                : "Descreva o que você procura no catálogo… (ou digite o título/ID para selecionar direto)"
            }
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => (e.key === "Enter" ? onSend() : null)}
            disabled={loadingCatalog}
          />

          <button
            className="chat-reset"
            onClick={resetChat}
            disabled={loadingCatalog && !docs.length}
            title="Resetar conversa"
          >
            Recomeçar
          </button>

          <button className="chat-send" onClick={() => onSend()} disabled={loadingCatalog}>
            Enviar
          </button>
        </div>

        {catalogError ? <div className="chat-error">Erro: {catalogError}</div> : null}
      </div>
    </div>
  );
}
