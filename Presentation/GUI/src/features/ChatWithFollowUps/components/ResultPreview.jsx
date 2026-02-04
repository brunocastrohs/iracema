export default function ResultPreview({ preview }) {
  if (!Array.isArray(preview) || !preview.length) return null;

  const keys = Object.keys(preview[0] || {});
  if (!keys.length) return null;

  return (
    <div className="result-preview">
      <div className="result-preview-title">Prévia do resultado</div>

      <div className="result-preview-table-wrap">
        <table className="result-preview-table">
          <thead>
            <tr>
              {keys.map((k) => (
                <th key={k}>{k}</th>
              ))}
            </tr>
          </thead>

          <tbody>
            {preview.map((row, i) => (
              <tr key={i}>
                {keys.map((k) => (
                  <td key={k}>{String(row?.[k] ?? "")}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
