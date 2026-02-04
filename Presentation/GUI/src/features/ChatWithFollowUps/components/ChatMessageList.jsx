import avatarIracema from "../../../_assets/images/avatar_iracema.png";
import ChatMessageItem from "./ChatMessageItem";

export default function ChatMessageList({
  messages,
  typedDone,
  lastAssistantId,
  markDone,
  bottomRef,
  loadingCatalog,
  onSelectTable,
  onFollowUp,
  onTickScroll,
}) {
  return (

    <div className="chat-messages">
      {messages.map((msg) => (
        <ChatMessageItem
          key={msg.id}
          msg={msg}
          typedDone={typedDone}
          lastAssistantId={lastAssistantId}
          markDone={markDone}
          avatarSrc={avatarIracema}
          onSelectTable={onSelectTable}
          onFollowUp={onFollowUp}
          onTickScroll={onTickScroll}
        />
      ))}

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

  );
}
