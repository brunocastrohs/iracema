import axios from "axios";

const baseURL =
  import.meta.env.VITE_API_BASE_URL ||
  "iracema-api/v1";

const api = axios.create({
  baseURL,
  timeout: 120000,
  headers: {
    "Content-Type": "application/json",
    Accept: "application/json",
  },
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response) {
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