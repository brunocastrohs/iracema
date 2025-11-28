import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { login } from "./service";          
import "./styles.css";                      

import logo_fauno from "../../_assets/images/logo_fauno.png";
import hero from "../../_assets/images/hero.png";

export default function Auth() {
  const navigate = useNavigate();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [remember, setRemember] = useState(true);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const heroStyle = {
    backgroundImage: `url(${hero})`,
    backgroundSize: "cover",
    backgroundPosition: "center",
  };

  async function onSubmit(e) {
    e.preventDefault();
    e.stopPropagation();
    setError("");
    setLoading(true);

    try {
      const { ok, data, error: errMsg } = await login({ email, password });

      if (!ok || !data?.access_token) {
        setError(errMsg.message || "Credenciais inválidas.");
        return;
      }

      const storage = remember ? localStorage : sessionStorage;
      storage.setItem("fauno_token", data.access_token);
      storage.setItem(
        "fauno_token_bearer",
        `${data.token_type || "Bearer"} ${data.access_token}`
      );

      const other = remember ? sessionStorage : localStorage;
      other.removeItem("fauno_token");
      other.removeItem("fauno_token_bearer");

      navigate("/layers", { replace: true }); 
    } catch (ex) {
      setError("Erro inesperado. Tente novamente mais tarde.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="auth-page">
      {/* Coluna da imagem (esquerda) */}
      <div className="auth-hero" style={heroStyle} />

      {/* Coluna do formulário (direita) */}
      <div className="auth-panel">
        <div className="auth-card">
          <div className="auth-logo-fauno">
            {logo_fauno && <img src={logo_fauno} alt="FAUNO" />}
          </div>

          {error && <div className="error-box">{error}</div>}

          <form onSubmit={onSubmit}>
            <div className="form-group">
              <label className="form-label" htmlFor="email">
                Usuário
              </label>
              <input
                id="email"
                type="email"
                className="form-input"
                placeholder="Digite seu e-mail"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                autoFocus
                required
              />
            </div>

            <div className="form-group">
              <label className="form-label" htmlFor="password">
                Senha
              </label>
              <input
                id="password"
                type="password"
                className="form-input"
                placeholder="Digite sua senha"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
            </div>

            <div className="form-row">
              <input
                id="remember"
                type="checkbox"
                checked={remember}
                onChange={(e) => setRemember(e.target.checked)}
              />
              <label htmlFor="remember">Lembrar-me neste dispositivo</label>
            </div>

            <button
              className="btn btn-primary"
              type="submit"
              disabled={loading}
            >
              {loading ? "Acessando..." : "Acessar"}
            </button>

            <span className="helper">Versão 0.1.0</span>
          </form>
        </div>
      </div>
    </div>
  );
}
