export default function SuggestionsList({ suggestions, onSelectTable }) {
  if (!Array.isArray(suggestions) || !suggestions.length) return null;

  return (
    <div className="suggestions">
      {suggestions.map((s) => (
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
            {s.reason ? <span className="tag tag-outline">{s.reason}</span> : null}
          </div>

          <div className="suggestion-actions">
            <button
              onMouseDown={(e) => e.preventDefault()}
              className="btn-mini"
              onClick={() => onSelectTable?.(s.id)}
            >
              Selecionar
            </button>
          </div>
        </div>
      ))}
    </div>
  );
}
