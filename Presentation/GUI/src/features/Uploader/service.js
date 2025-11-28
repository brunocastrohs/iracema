import api from "../../_config/axios";

/**
 * Envia o ZIP para o backend em multipart/form-data.
 * @param {Object} args
 * @param {File} args.file
 * @param {string} args.workspace
 * @param {string} args.datastore
 * @param {number} args.srid
 * @param {boolean} args.publishOnINDE
 * @param {(pct:number)=>void} [args.onProgress]
 */
export async function uploadZip({
  file,
  workspace,
  datastore,
  srid,
  publishOnINDE,
  onProgress,
}) {
  const fd = new FormData();
  fd.append("file", file);
  fd.append("workspace", workspace);
  fd.append("datastore", datastore);
  fd.append("srid", String(srid));
  fd.append("publishOnINDE", publishOnINDE ? "true" : "false");

  const { data } = await api.post("/shapefiles/upload", fd, {
    headers: { "Content-Type": "multipart/form-data" },
    onUploadProgress: (e) => {
      if (!onProgress || !e.total) return;
      const pct = Math.round((e.loaded * 100) / e.total);
      onProgress(pct);
    },
  });

  return data;
}
