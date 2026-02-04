import { useRef, useState } from "react";

export default function ChatInputBar({ disabled, mode, onSend, onReset, sending }) {
  const [input, setInput] = useState("");
  const inputRef = useRef(null);

  function sendNow(textFromChip) {
    const q = String(textFromChip ?? input ?? "").trim();
    if (!q) return;
    onSend?.(q);
    setInput("");
    setTimeout(() => inputRef.current?.focus(), 0);
  }

  return (
    <div className="chat-inputbar">
      <input
        className="chat-input"
        ref={inputRef}
        placeholder={
          disabled
            ? "Carregando catálogo..."
            : mode === "ask"
            ? "Digite sua pergunta sobre a tabela selecionada…"
            : "Descreva o que você procura no catálogo…"
        }
        value={input}
        onChange={(e) => setInput(e.target.value)}
        onKeyDown={(e) => (e.key === "Enter" ? sendNow() : null)}
        disabled={disabled}
      />

      <button
        onMouseDown={(e) => e.preventDefault()}
        className="chat-reset"
        onClick={onReset}
        disabled={disabled}
        title="Resetar conversa"
      >
        <i className="pi pi-refresh" /> Recomeçar
      </button>

      <button
        onMouseDown={(e) => e.preventDefault()}
        className="chat-send"
        onClick={() => sendNow()}
        disabled={disabled || sending}
      >
        {sending ? <i className="pi pi-spin pi-spinner" /> : <><i className="pi pi-send" /> Enviar</>}
      </button>
    </div>
  );
}
