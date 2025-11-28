import { useState } from "react";
import { login } from "./service";

export function useAuth() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleLogin({ email, password, remember }) {
    setError("");
    setLoading(true);
    try {
      const data = await login({ email, password });
      const { access_token } = data || {};
      if (!access_token) throw new Error("Token não retornado pela API.");

      // Armazena token
      const storage = remember ? localStorage : sessionStorage;
      storage.setItem("fauno_token", access_token);

      return { ok: true, data };
    } catch (err) {
      const msg =
        err?.message ||
        "Falha ao autenticar. Verifique suas credenciais.";
      setError(msg);
      return { ok: false, error: msg };
    } finally {
      setLoading(false);
    }
  }

  return { loading, error, handleLogin };
}
