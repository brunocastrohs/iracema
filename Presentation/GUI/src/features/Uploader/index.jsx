import { useState } from "react";
import "./styles.css";
import { uploadZip } from "./service";

// valores lidos do .env (com fallback)
const WS = import.meta.env.VITE_GEOSERVER_WORKSPACE || "zcm";
const DS = import.meta.env.VITE_GEOSERVER_DATASTORE || "zcm_ds";
const DEFAULT_SRID = Number(import.meta.env.VITE_DEFAULT_SRID || 4674);

export default function Uploader() {
  const [file, setFile] = useState(null);
  const [workspace] = useState(WS);
  const [datastore] = useState(DS);
  const [srid] = useState(DEFAULT_SRID);
  const [publishOnINDE, setPublishOnINDE] = useState(false);

  const [progress, setProgress] = useState(0);
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState("");
  const [result, setResult] = useState(null);

  function onPickFile(e) {
    const f = e.target.files?.[0];
    setResult(null);
    setErrorMsg("");
    setProgress(0);

    if (!f) {
      setFile(null);
      return;
    }
    const isZip = /\.zip$/i.test(f.name);
    if (!isZip) {
      setFile(null);
      setErrorMsg("Selecione um arquivo .zip contendo o shapefile.");
      return;
    }
    setFile(f);
  }

  async function onSubmit(e) {
    e.preventDefault();

    if (!file) {
      setErrorMsg("Selecione um arquivo .zip.");
      return;
    }

    try {
      setLoading(true);
      setErrorMsg("");
      setResult(null);

      const data = await uploadZip({
        file,
        workspace,
        datastore,
        srid,
        publishOnINDE,
        onProgress: setProgress,
      });

      setResult(data);
    } catch (err) {
      const msg =
        err?.message ||
        "Falha ao enviar arquivo.";
      setErrorMsg(msg);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="uploader-page">
      <h1 className="section-title">Publicar Shapefile</h1>

      <form className="uploader-form" onSubmit={onSubmit} noValidate>
        <div className="form-row-2">
          <div className="form-group">
            <label className="form-label">Arquivo (.zip)</label>
            <input
              type="file"
              accept=".zip"
              className="form-input"
              onChange={onPickFile}
            />
            {file && <small>Selecionado: {file.name}</small>}
          </div>

          <div className="form-group checkbox">
            <label htmlFor="publishOnINDE">
              <input
                id="publishOnINDE"
                type="checkbox"
                checked={publishOnINDE}
                onChange={(e) => setPublishOnINDE(e.target.checked)}
              />{" "}
              Publicar também no INDE
            </label>
          </div>
        </div>

        <div className="form-row-3">
          <div className="form-group">
            <label className="form-label">Workspace</label>
            <input className="form-input" value={workspace} readOnly />
          </div>

          <div className="form-group">
            <label className="form-label">Datastore</label>
            <input className="form-input" value={datastore} readOnly />
          </div>

          <div className="form-group">
            <label className="form-label">SRID</label>
            <input className="form-input" value={srid} readOnly />
          </div>
        </div>

        {progress > 0 && loading && (
          <div className="progress">
            <div className="bar" style={{ width: `${progress}%` }} />
            <span className="pct">{progress}%</span>
          </div>
        )}

        {errorMsg && <div className="layers-error">{errorMsg}</div>}

        <button className="btn btn-primary" type="submit" disabled={loading}>
          {loading ? "Publicando..." : "Publicar"}
        </button>
      </form>

      {/* Resultado bonito */}
      {result && (
        <div className="uploader-result">
          <h2 className="section-title" style={{ marginBottom: ".5rem" }}>
            Resultado
          </h2>

          <div className="result-grid">
            <div className="result-card">
              <h3>Principal</h3>
              <p><strong>Layer:</strong> {result?.geoserver?.main?.layer}</p>
              <p><strong>Style:</strong> {result?.geoserver?.main?.style}</p>
              <p><strong>SRID:</strong> {srid}</p>
              <p>
                <strong>Status:</strong>{" "}
                {result?.geoserver?.main?.http_status ?? "-"}
              </p>
              <p>
                <strong>SLD OK:</strong>{" "}
                {String(result?.geoserver?.main?.sld_ok)}
              </p>
            </div>

            {result?.geoserver?.inde && (
              <div className="result-card">
                <h3>INDE</h3>
                <p><strong>Layer:</strong> {result.geoserver.inde.layer}</p>
                <p><strong>Style:</strong> {result.geoserver.inde.style}</p>
                <p>
                  <strong>Status:</strong>{" "}
                  {result.geoserver.inde.http_status ?? "-"}
                </p>
                <p>
                  <strong>SLD OK:</strong>{" "}
                  {String(result.geoserver.inde.sld_ok)}
                </p>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
