import { z } from "zod";
import { createDataUrl } from "@/lib/file";
import { getApiKey, getMistralEndpoint, shouldUseMocks } from "@/lib/env";
import type { DocumentProcessPayload, ProcessedDocument } from "@/types/document";
import mockSample from "@/mocks/fixtures/super-ongoing-fee-consent-sample-1.json";

const pageSchema = z
  .object({
    page_number: z.number().optional(),
    index: z.number().optional(),
    image_base64: z.string().optional(),
    images: z.array(z.string()).optional(),
    markdown: z.string().optional(),
    dimensions: z
      .object({
        dpi: z.number().optional(),
        height: z.number().optional(),
        width: z.number().optional(),
      })
      .optional(),
  })
  .passthrough();

const pagesSchema = z.array(pageSchema).optional();

const documentResponseSchema = z
  .object({
    markdown: z.string().optional(),
    json: z.union([z.record(z.any()), z.array(z.any()), z.null()]).optional(),
    pages: pagesSchema,
    duration_ms: z.number().optional(),
  })
  .passthrough();

const responseSchema = documentResponseSchema
  .extend({
    result: z.unknown().optional(),
    data: z.unknown().optional(),
    response_json: z.unknown().optional(),
    model: z.string().optional(),
    document_annotation: z.unknown().optional(),
    usage_info: z
      .object({
        pages_processed: z.number().optional(),
        doc_size_bytes: z.number().optional(),
        pages_processed_annotation: z.number().optional(),
      })
      .optional(),
  })
  .passthrough();

type DocumentResponse = z.infer<typeof documentResponseSchema>;
type ApiResponse = z.infer<typeof responseSchema>;

function resolveDocumentPayload(apiResponse: ApiResponse): DocumentResponse {
  const candidates = [
    apiResponse.response_json,
    apiResponse.result,
    apiResponse.data,
    apiResponse,
  ];

  for (const candidate of candidates) {
    const parsedCandidate = documentResponseSchema.safeParse(candidate);
    if (parsedCandidate.success) {
      return parsedCandidate.data;
    }
  }

  return documentResponseSchema.parse({});
}

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

  const parsed = responseSchema.safeParse(json);

  if (!parsed.success) {
    throw new Error("Received an unexpected response from the API");
  }

  const apiResponse = parsed.data;
  const responseJsonPayload = documentResponseSchema.safeParse(apiResponse.response_json ?? null);
  // Emit the structured payload so we can trace Mistral's answer in the command prompt.
  console.info(
    "[processDocumentViaApi] response_json:",
    responseJsonPayload.success ? responseJsonPayload.data : apiResponse.response_json ?? null,
  );

  const payloadResult = resolveDocumentPayload(apiResponse);

  const pagesFromPayload = Array.isArray(payloadResult.pages) ? payloadResult.pages : [];
  const fallbackPages = Array.isArray(apiResponse.pages) ? apiResponse.pages : [];

  const pagesSource = pagesFromPayload.length > 0 ? pagesFromPayload : fallbackPages;

  const pages = pagesSource.map((page, index) => ({
    id: crypto.randomUUID(),
    pageNumber: page?.page_number ?? page?.index ?? index + 1,
    base64: page?.image_base64 ?? page?.images?.[0] ?? "",
  }));

  const structuredJson = (() => {
    if (payloadResult.json == null) {
      return {};
    }

    if (Array.isArray(payloadResult.json)) {
      return { data: payloadResult.json };
    }

    return payloadResult.json as Record<string, unknown>;
  })();

  const durationFromResponse =
    payloadResult.duration_ms ?? apiResponse.duration_ms ?? performance.now() - startedAt;

  const fallbackMarkdown = pagesSource
    .map((page) => page?.markdown?.trim())
    .filter((value): value is string => Boolean(value))
    .join("\n\n---\n\n");

  const resolvedMarkdown =
    payloadResult.markdown ?? (fallbackMarkdown.length > 0 ? fallbackMarkdown : undefined);

  return {
    id: crypto.randomUUID(),
    fileName: payload.fileName,
    uploadedAt: new Date().toISOString(),
    extraction: {
      markdown: resolvedMarkdown ?? "_No markdown content returned._",
      json: structuredJson,
      pages: pages.filter((page) => Boolean(page.base64)),
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
