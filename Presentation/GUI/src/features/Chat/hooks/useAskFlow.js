import { askChat } from "../service";
import { computeFallbackStrategy } from "../domain/chatIntents";

export function useAskFlow() {
  async function runAskWithFallback({ question, table_identifier }) {
    const explain = localStorage.getItem("iracema_explain") === "true";
    const preferred = localStorage.getItem("iracema_strategy") || "ask/fc/args";
    const fallback = computeFallbackStrategy(preferred);

    async function tryAsk(strategy) {
      const res = await askChat({
        question,
        table_identifier,
        top_k: 1000,
        explain,
        strategy,
      });

      const failed = !res?.ok || Boolean(res?.data?.error);
      return { ...res, failed, usedStrategy: strategy };
    }

    let result = await tryAsk(preferred);

    if (result.failed && fallback !== preferred) {
      result = await tryAsk(fallback);
    }

    return result;
  }

  return { runAskWithFallback };
}
