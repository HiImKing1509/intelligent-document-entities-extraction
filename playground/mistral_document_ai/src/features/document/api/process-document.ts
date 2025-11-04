import { z } from "zod";
import { createDataUrl } from "@/lib/file";
import { getApiKey, getMistralEndpoint, shouldUseMocks } from "@/lib/env";
import type { DocumentProcessPayload, ProcessedDocument } from "@/types/document";
import mockSample from "@/mocks/fixtures/super-ongoing-fee-consent-sample-1.json";

const documentResponseSchema = z
  .object({
    markdown: z.string().optional(),
    json: z.union([z.record(z.any()), z.array(z.any())]).optional(),
    pages: z
      .array(
        z
          .object({
            page_number: z.number().optional(),
            image_base64: z.string().optional()
          })
          .passthrough()
      )
      .optional(),
    duration_ms: z.number().optional()
  })
  .passthrough();

const responseSchema = z
  .object({
    result: documentResponseSchema.optional(),
    data: documentResponseSchema.optional()
  })
  .passthrough();

function buildRequestBody(payload: DocumentProcessPayload) {
  return {
    model: "mistral-document-ai-2505",
    document: {
      type: "document_url",
      document_url: createDataUrl(payload.documentBase64, payload.mimeType)
    },
    include_image_base64: payload.includeImageBase64 ?? true
  };
}

export async function processDocumentViaApi(
  payload: DocumentProcessPayload
): Promise<ProcessedDocument> {
  const requestBody = buildRequestBody(payload);
  const useMocks = shouldUseMocks();

  if (useMocks) {
    return buildMockProcessedDocument(payload, mockSample);
  }

  const endpoint = getMistralEndpoint();

  const headers: HeadersInit = {
    "Content-Type": "application/json"
  };

  const apiKey = getApiKey();
  if (!useMocks && apiKey) {
    headers.Authorization = `Bearer ${apiKey}`;
  }

  const startedAt = performance.now();
  const response = await fetch(endpoint, {
    method: "POST",
    headers,
    body: JSON.stringify(requestBody)
  });

  if (!response.ok) {
    const message = await response.text();
    throw new Error(`Processing failed (${response.status}): ${message}`);
  }

  const json = await response.json();
  const parsed = responseSchema.safeParse(json);

  if (!parsed.success) {
    throw new Error("Received an unexpected response from the API");
  }

  const payloadResult = parsed.data.result ?? parsed.data.data ?? (json as Record<string, unknown>);

  const pages =
    payloadResult.pages?.map((page, index) => ({
      id: crypto.randomUUID(),
      pageNumber: page.page_number ?? index + 1,
      base64: page.image_base64 ?? ""
    })) ?? [];

  return {
    id: crypto.randomUUID(),
    fileName: payload.fileName,
    uploadedAt: new Date().toISOString(),
    extraction: {
      markdown: payloadResult.markdown ?? "_No markdown content returned._",
      json: (payloadResult.json as Record<string, unknown>) ?? {},
      pages: pages.filter((page) => Boolean(page.base64))
    },
    durationMs: Math.round(performance.now() - startedAt),
    documentDataUrl: createDataUrl(payload.documentBase64, payload.mimeType)
  };
}

type MockResponse = typeof mockSample;

function buildMockProcessedDocument(
  payload: DocumentProcessPayload,
  mock: MockResponse
): ProcessedDocument {
  const concatenatedMarkdown = mock.pages.map((page) => page.markdown.trim()).join("\n\n---\n\n");
  const pages =
    mock.pages
      ?.map((page, index) => ({
        id: crypto.randomUUID(),
        pageNumber: index + 1,
        base64: page.images?.[0] ?? ""
      }))
      .filter((page) => Boolean(page.base64)) ?? [];

  return {
    id: crypto.randomUUID(),
    fileName: payload.fileName,
    uploadedAt: new Date().toISOString(),
    extraction: {
      markdown: concatenatedMarkdown,
      json: mock,
      pages
    },
    durationMs: Math.round(Math.random() * 500 + 900),
    documentDataUrl: createDataUrl(payload.documentBase64, payload.mimeType)
  };
}

export function createDocumentProcessPayload(file: File, base64: string): DocumentProcessPayload {
  return {
    documentBase64: base64,
    fileName: file.name,
    mimeType: file.type || "application/pdf",
    includeImageBase64: true
  };
}
