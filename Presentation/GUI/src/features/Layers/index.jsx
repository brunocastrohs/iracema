import { useEffect, useMemo, useState } from "react";
import { getLayers } from "./service";
import "./styles.css";

export default function Layers() {
  const [layers, setLayers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [query, setQuery] = useState("");

  useEffect(() => {
    async function loadLayers() {
      try {
        setLoading(true);
        const data = await getLayers();
        setLayers(data || []);
      } catch (err) {
        setError("Falha ao carregar as camadas.");
      } finally {
        setLoading(false);
      }
    }
    loadLayers();
  }, []);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return layers;
    return layers.filter((item) =>
      Object.values(item).some((val) =>
        String(val ?? "").toLowerCase().includes(q)
      )
    );
  }, [layers, query]);

  return (
    <div className="layers-page">
      <header className="layers-header">
        <h1 className="section-title">Camadas Publicadas</h1>

        <div className="layers-search">
          <input
            type="text"
            placeholder="Pesquisar por nome, schema, tipo, SRID..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            aria-label="Pesquisar camadas"
          />
          {query && (
            <button
              type="button"
              className="clear-btn"
              onClick={() => setQuery("")}
              aria-label="Limpar busca"
              title="Limpar"
            >
              ×
            </button>
          )}
        </div>
      </header>

      {loading && <div className="layers-loading">Carregando...</div>}
      {error && <div className="layers-error">{error}</div>}

      {!loading && !error && (
        <>
          <div className="layers-meta">
            {filtered.length} {filtered.length === 1 ? "camada" : "camadas"}
            {query ? ` (filtradas por "${query}")` : null}
          </div>

          <div className="layers-table-container">
            {filtered.length === 0 ? (
              <p className="layers-empty">Nenhuma camada encontrada.</p>
            ) : (
              <table className="layers-table">
                <thead>
                  <tr>
                    <th>Nome</th>
                    <th>Schema</th>
                    <th>Tipo Geometria</th>
                    <th>SRID</th>
                  </tr>
                </thead>
                <tbody>
                  {filtered.map((layer, idx) => (
                    <tr key={`${layer.f_table_schema}.${layer.f_table_name}-${idx}`}>
                      <td>{layer.f_table_name}</td>
                      <td>{layer.f_table_schema}</td>
                      <td>{layer.type}</td>
                      <td>{layer.srid}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </>
      )}
    </div>
  );
}
