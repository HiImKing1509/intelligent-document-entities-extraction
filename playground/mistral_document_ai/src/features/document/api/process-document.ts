import { createDataUrl } from "@/lib/file";
import { getApiKey, getMistralEndpoint, shouldUseMocks } from "@/lib/env";
import type { DocumentProcessPayload, ProcessedDocument } from "@/types/document";
import mockSample from "@/mocks/fixtures/super-ongoing-fee-consent-sample-1.json";

type DocumentApiPage = {
  page_number?: number;
  index?: number;
  image_base64?: string;
  images?: string[];
  markdown?: string;
  dimensions?: {
    dpi?: number;
    height?: number;
    width?: number;
  };
};

type DocumentApiResponse = Record<string, unknown> & {
  pages?: DocumentApiPage[];
  markdown?: string;
  duration_ms?: number;
};

function buildRequestBody(payload: DocumentProcessPayload) {
  return {
    model: "mistral-document-ai-2505",
    document: {
      type: "document_url",
      document_url: createDataUrl(payload.documentBase64, payload.mimeType),
    },
    include_image_base64: payload.includeImageBase64 ?? true,
  };
}

export async function processDocumentViaApi(
  payload: DocumentProcessPayload,
): Promise<ProcessedDocument> {
  const requestBody = buildRequestBody(payload);
  const useMocks = shouldUseMocks();

  if (useMocks) {
    return buildMockProcessedDocument(payload, mockSample);
  }

  const endpoint = getMistralEndpoint();

  const headers: HeadersInit = {
    "Content-Type": "application/json",
  };

  const apiKey = getApiKey();
  if (!useMocks && apiKey) {
    headers.Authorization = `Bearer ${apiKey}`;
  }

  const startedAt = performance.now();
  const response = await fetch(endpoint, {
    method: "POST",
    headers,
    body: JSON.stringify(requestBody),
  });

  if (!response.ok) {
    const message = await response.text();
    throw new Error(`Processing failed (${response.status}): ${message}`);
  }

  const json = await response.json();
  console.info("[processDocumentViaApi] raw response:", json);

  const apiResponse = (json ?? {}) as DocumentApiResponse;
  const pagesFromResponse = Array.isArray(apiResponse.pages) ? apiResponse.pages : [];

  const processedPages = pagesFromResponse
    .map((page, index) => ({
      id: crypto.randomUUID(),
      pageNumber: page?.page_number ?? page?.index ?? index + 1,
      base64: page?.image_base64 ?? page?.images?.[0] ?? "",
    }))
    .filter((page) => Boolean(page.base64));

  const fallbackMarkdown = pagesFromResponse
    .map((page) => page?.markdown?.trim())
    .filter((value): value is string => Boolean(value))
    .join("\n\n---\n\n");

  const normalizedMarkdown =
    typeof apiResponse.markdown === "string" ? apiResponse.markdown.trim() : "";

  const resolvedMarkdown =
    normalizedMarkdown.length > 0 ? normalizedMarkdown : fallbackMarkdown;

  const structuredJson: Record<string, unknown> = { ...apiResponse };

  const durationFromResponse =
    typeof apiResponse.duration_ms === "number"
      ? apiResponse.duration_ms
      : performance.now() - startedAt;

  const finalMarkdown =
    resolvedMarkdown.length > 0 ? resolvedMarkdown : "_No markdown content returned._";

  return {
    id: crypto.randomUUID(),
    fileName: payload.fileName,
    uploadedAt: new Date().toISOString(),
    extraction: {
      markdown: finalMarkdown,
      json: structuredJson,
      pages: processedPages,
    },
    durationMs: Math.round(durationFromResponse),
    documentDataUrl: createDataUrl(payload.documentBase64, payload.mimeType),
  };
}

type MockResponse = typeof mockSample;

function buildMockProcessedDocument(
  payload: DocumentProcessPayload,
  mock: MockResponse,
): ProcessedDocument {
  const concatenatedMarkdown = mock.pages.map((page) => page.markdown.trim()).join("\n\n---\n\n");
  const pages =
    mock.pages
      ?.map((page, index) => ({
        id: crypto.randomUUID(),
        pageNumber: index + 1,
        base64: page.images?.[0] ?? "",
      }))
      .filter((page) => Boolean(page.base64)) ?? [];

  return {
    id: crypto.randomUUID(),
    fileName: payload.fileName,
    uploadedAt: new Date().toISOString(),
    extraction: {
      markdown: concatenatedMarkdown,
      json: mock,
      pages,
    },
    durationMs: Math.round(Math.random() * 500 + 900),
    documentDataUrl: createDataUrl(payload.documentBase64, payload.mimeType),
  };
}

export function createDocumentProcessPayload(file: File, base64: string): DocumentProcessPayload {
  return {
    documentBase64: base64,
    fileName: file.name,
    mimeType: file.type || "application/pdf",
    includeImageBase64: true,
  };
}
