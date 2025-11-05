import { useCallback, useMemo, useState } from "react";
import type { ProcessedDocument } from "@/types/document";

const HISTORY_LIMIT = 6;

export function useDocumentHistory() {
  const [history, setHistory] = useState<ProcessedDocument[]>([]);

  const addDocument = useCallback((doc: ProcessedDocument) => {
    setHistory((prev) => {
      const filtered = prev.filter((item) => item.id !== doc.id);
      return [doc, ...filtered].slice(0, HISTORY_LIMIT);
    });
  }, []);

  const clearHistory = useCallback(() => {
    setHistory([]);
  }, []);

  return useMemo(
    () => ({
      history,
      addDocument,
      clearHistory,
    }),
    [history, addDocument, clearHistory],
  );
}
