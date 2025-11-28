import axios from "axios";

const baseURL =
  import.meta.env.VITE_API_BASE_URL ||
  'fauno-api/v1';

const api = axios.create({
  baseURL,
  timeout: 120000, // 2 min
  headers: {
    "Content-Type": "application/json",
    Accept: "application/json",
  },
});

// ================================
// Interceptores
// ================================

// Adiciona JWT automaticamente se existir no localStorage
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem("fauno_token");
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Trata respostas e erros
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response) {
      // Caso o token tenha expirado
      if (error.response.status === 401) {
        console.warn("Sessão expirada. Redirecionando para login...");
        localStorage.removeItem("fauno_token");
      }

      // Mensagens customizadas de erro
      const message =
        error.response.data?.message ||
        error.response.data?.detail ||
        "Erro desconhecido ao processar requisição.";
      console.error("Erro Axios:", message);
    } else {
      console.error("Erro de rede ou servidor indisponível.");
    }

    return Promise.reject(error);
  }
);

export default api;
