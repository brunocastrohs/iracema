import { useEffect, useState } from "react";
import "./styles.css";

const STRATEGIES = [
  { value: "ask/fc", label: "Function Calling (ask/fc)" },
  { value: "ask/heuristic", label: "Heurística (ask/heuristic)" },
  { value: "ask/ai", label: "IA (ask/ai)" },
  { value: "ask", label: "Heurística+IA (ask/heuristic/ai)" },
];

function loadConfig() {
  const explainRaw = localStorage.getItem("iracema_explain");
  const strategyRaw = localStorage.getItem("iracema_strategy");

  return {
    explain: explainRaw === null ? false : explainRaw === "true",
    strategy: strategyRaw || "ask/fc",
  };
}

function saveConfig({ explain, strategy }) {
  localStorage.setItem("iracema_explain", String(Boolean(explain)));
  localStorage.setItem("iracema_strategy", String(strategy || "ask/fc"));
}

function Help({ children }) {
  return <div className="config-help">{children}</div>;
}

export default function Configuration() {
  const [explain, setExplain] = useState(false);
  const [strategy, setStrategy] = useState("ask/fc");
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    const cfg = loadConfig();
    setExplain(cfg.explain);
    setStrategy(cfg.strategy);
  }, []);

  function onSave() {
    saveConfig({ explain, strategy });
    setSaved(true);
    setTimeout(() => setSaved(false), 1200);
  }

  return (
    <div className="config-page">
      <div className="config-card">
        <div className="config-header">
          <div className="config-title">Configurações</div>
          <div className="config-subtitle">
            <b>Iracema</b> é a assistente inteligente da Plataforma Estadual de Dados Ambientais para explorar o catálogo de camadas e consultar dados.
            Aqui você controla o nível de explicação e a estratégia usada na API conversacional.
          </div>
        </div>

        <div className="config-section">
          <div className="config-label">Explain</div>
          <Help>
            <b>Explain</b> mostra detalhes do “raciocínio” do backend (plano/SQL/filtros).
            Use para depurar ou validar a resposta. Desligado = respostas mais limpas.
          </Help>
          <div className="config-row">
            <label className="switch">
              <input
                type="checkbox"
                checked={explain}
                onChange={(e) => setExplain(e.target.checked)}
              />
              <span className="slider" />
            </label>
            <div className="config-help">
              Quando ligado, o backend pode retornar mais detalhes do plano/SQL.
            </div>
          </div>
        </div>

        <div className="config-section">
          <div className="config-label">Estratégia de Resposta</div>
          <Help>
            <ul className="config-strategy-list">
              <li>
                <b>ask/fc</b> — Plano estruturado via geração de Function Calling Arguments.
                <br />
                <span>Mais confiável e determinístico; ideal para produção.</span>
              </li>

              <li>
                <b>ask/heuristic</b> — Regras e parsing por padrões.
                <br />
                <span>Rápido e previsível, porém menos flexível para linguagem natural.</span>
              </li>

              <li>
                <b>ask/ai</b> — IA com maior liberdade de interpretação.
                <br />
                <span>Mais flexível para perguntas abertas, mas com maior variabilidade.</span>
              </li>

              <li>
                <b>ask</b> — Estratégia híbrida (heurística + fallback IA).
                <br />
                <span>Equilíbrio entre previsibilidade e flexibilidade (recomendado).</span>
              </li>
            </ul>

          </Help>
          <select
            className="config-select"
            value={strategy}
            onChange={(e) => setStrategy(e.target.value)}
          >
            {STRATEGIES.map((s) => (
              <option key={s.value} value={s.value}>
                {s.label}
              </option>
            ))}
          </select>

          <div className="config-help">
            Define qual endpoint/estratégia será usada ao consultar: <b>{strategy}</b>
          </div>
        </div>

        <div className="config-actions">
          <button className="config-btn" onClick={onSave}>
            <i className="pi pi-save" /> Salvar
          </button>
          {saved ? <span className="config-saved">Salvo ✓</span> : null}
        </div>
      </div>
    </div>
  );
}
