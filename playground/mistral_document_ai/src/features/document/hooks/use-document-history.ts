import { useCallback, useEffect, useMemo, useState } from "react";
import type { ProcessedDocument } from "@/types/document";

const STORAGE_KEY = "mistral-document-history";
const HISTORY_LIMIT = 6;

function isBrowser() {
  return typeof window !== "undefined";
}

function loadHistory(): ProcessedDocument[] {
  if (!isBrowser()) {
    return [];
  }

  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) {
      return [];
    }
    const parsed = JSON.parse(raw) as ProcessedDocument[];
    return parsed ?? [];
  } catch {
    return [];
  }
}

export function useDocumentHistory() {
  const [history, setHistory] = useState<ProcessedDocument[]>(() => loadHistory());

  useEffect(() => {
    if (!isBrowser()) {
      return;
    }
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(history));
  }, [history]);

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
      clearHistory
    }),
    [history, addDocument, clearHistory]
  );
}
