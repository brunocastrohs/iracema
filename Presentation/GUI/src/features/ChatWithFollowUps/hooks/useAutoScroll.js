import { useCallback, useRef } from "react";

export function useAutoScroll() {
  const bottomRef = useRef(null);

  const scrollToBottom = useCallback(() => {
    requestAnimationFrame(() => {
      bottomRef.current?.scrollIntoView({ behavior: "smooth" });
    });
  }, []);

  return { bottomRef, scrollToBottom };
}
