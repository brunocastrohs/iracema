import { useMemo, useState } from "react";
import { now } from "../helpers";
import {
  makeAssistantMessage,
  makeUserMessage,
  makeCatalogLoadedMessage,
  removeTrailingLoading,
} from "../domain/messageFactories";

export function useChatMessages({ initialAssistantText }) {
  const [typedDone, setTypedDone] = useState({});
  const [messages, setMessages] = useState([
    makeAssistantMessage({
      ts: now(),
      text: initialAssistantText,
      followUps: [],
    }),
  ]);

  function markDone(id) {
    if (!id) return;
    setTypedDone((m) => (m[id] ? m : { ...m, [id]: true }));
  }

  function pushUser(text) {
    setMessages((m) => [...m, makeUserMessage(text)]);
  }

  function pushAssistant(payload) {
    setMessages((m) => [...m, makeAssistantMessage(payload)]);
  }

  function pushCatalogLoaded(count) {
    setMessages((m) => [...m, makeCatalogLoadedMessage(count)]);
  }

  function replaceRemoveTrailingLoadingAndAppend(msg) {
    setMessages((prev) => [...removeTrailingLoading(prev), msg]);
  }

  const lastAssistantId = useMemo(() => {
    for (let i = messages.length - 1; i >= 0; i--) {
      if (messages[i]?.role === "assistant" && !messages[i]?.isLoading) return messages[i].id;
    }
    return null;
  }, [messages]);

  return {
    messages,
    setMessages,
    typedDone,
    markDone,
    lastAssistantId,
    pushUser,
    pushAssistant,
    pushCatalogLoaded,
    replaceRemoveTrailingLoadingAndAppend,
  };
}
