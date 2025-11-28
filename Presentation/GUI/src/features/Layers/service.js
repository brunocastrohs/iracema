import api from "../../_config/axios";

/**
 * Obtém as layers disponíveis no schema atual (workspace do GeoServer).
 */
export async function getLayers() {
  try {
    const { data } = await api.get("/shapefiles/layers");
    return data;
  } catch (error) {
    console.error("Erro ao buscar layers:", error);
    throw error;
  }
}
