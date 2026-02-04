import TypewriterText from "./TypewriterText";
import ResultPreview from "./ResultPreview";
import SuggestionsList from "./SuggestionsList";
import PromptSuggestions from "./PromptSuggestions";

export default function ChatMessageItem({
  msg,
  typedDone,
  lastAssistantId,
  markDone,
  avatarSrc,
  onSelectTable,
  onSuggestPrompt,
  onTickScroll,
}) {
  const canShowExtras =
    msg.role !== "assistant" ||
    msg.isLoading ||
    typedDone[msg.id] ||
    msg.id !== lastAssistantId;

  return (
    <div className={`chat-row ${msg.role === "user" ? "is-user" : "is-assistant"}`}>
      {msg.role === "assistant" ? (
        <div className="chat-avatar" title="Iracema">
          <img src={avatarSrc} alt="Iracema" />
        </div>
      ) : null}

      <div className={`chat-bubble ${msg.role === "user" ? "user" : "assistant"}`}>
        <div className="chat-text">
          {msg.role === "assistant" && !msg.isLoading ? (
            <TypewriterText
              text={msg.text || ""}
              animate={msg.id === lastAssistantId && !typedDone[msg.id]}
              speed={10}
              onTick={onTickScroll}
              onDone={() => {
                markDone(msg.id);
                onTickScroll?.();
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

        {canShowExtras ? (
          <>
            <ResultPreview preview={msg.preview} />
            <SuggestionsList suggestions={msg.suggestions} onSelectTable={onSelectTable} />
            <PromptSuggestions prompts={msg.suggestedPrompts} onPick={onSuggestPrompt} />
          </>
        ) : null}
      </div>
    </div>
  );
}
