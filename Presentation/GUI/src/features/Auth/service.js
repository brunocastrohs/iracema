import api from "../../_config/axios";

/**
 * Autentica o usuário e retorna status de sucesso se um JWT for obtido.
 * @param {Object} credentials - { email, password }
 * @returns {Promise<{ ok: boolean, data?: Object, error?: string }>}
 */
export async function login({ email, password }) {
  try {
    const { data } = await api.post("/auth/login", { email, password });

    if (!data || !data.access_token) {
      return {
        ok: false,
        error: "Resposta sem access_token. Login falhou.",
      };
    }

    return { ok: true, data };
  } catch (error) {
    const msg =
      error.response?.data?.detail ||
      error.response?.data?.message ||
      "Erro ao autenticar usuário.";
    return { ok: false, error: msg };
  }
}
