// src/features/Chat/components/PromptSuggestions.jsx
import { useState } from "react";

export default function PromptSuggestions({ prompts = [], onPick }) {
  if (!Array.isArray(prompts) || prompts.length === 0) return null;

  return (
    <div className="prompt-suggestions">
      <div className="prompt-suggestions-title">Sugestões do que você pode escrever:</div>

      <div className="prompt-suggestions-list">
        {prompts.slice(0, 6).map((p) => (
          <button
            key={p}
            type="button"
            className="prompt-suggestion"
            onMouseDown={(e) => e.preventDefault()}
            onClick={() => onPick?.(p)}
            title="Clique para preencher no input"
          >
            {p}
          </button>
        ))}
      </div>
    </div>
  );
}
