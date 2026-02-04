import { useEffect, useRef, useState } from "react";
import { getCatalog } from "../service";
import { buildDocs, buildIndex } from "../catalogEngine";

export function useCatalog() {
  const [loadingCatalog, setLoadingCatalog] = useState(true);
  const [catalogError, setCatalogError] = useState("");
  const [docs, setDocs] = useState([]);
  const [index, setIndex] = useState(null);

  const didLoadRef = useRef(false);

  useEffect(() => {
    (async () => {
      if (didLoadRef.current) return;
      didLoadRef.current = true;

      setLoadingCatalog(true);
      setCatalogError("");

      const { ok, data, error, meta } = await getCatalog();
      if (!ok) {
        setCatalogError(error || "Falha ao carregar catálogo.");
        setLoadingCatalog(false);
        return;
      }

      const builtDocs = buildDocs(data);
      const builtIndex = buildIndex(builtDocs);

      setDocs(builtDocs);
      setIndex(builtIndex);
      setLoadingCatalog(false);

      // meta count é útil pra mensagem “Catálogo carregado”
      // devolvemos meta via return? Não precisa: quem usa hook pode ler docs.length também.
      // Se você quiser usar o count real do backend: guarde aqui.
      // (mantive simples: count = meta?.count ?? builtDocs.length)
      // opcional: setMetaCount(meta?.count ?? builtDocs.length);
    })();
  }, []);

  return {
    loadingCatalog,
    catalogError,
    docs,
    index,
  };
}
