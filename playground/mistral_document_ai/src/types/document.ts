export type DocumentProcessPayload = {
  documentBase64: string;
  fileName: string;
  mimeType: string;
  includeImageBase64?: boolean;
};

export type DocumentProcessRequest = {
  model: string;
  document: {
    type: "document_url";
    document_url: string;
  };
  include_image_base64: boolean;
};

export type DocumentPageImage = {
  id: string;
  pageNumber: number;
  base64: string;
};

export type DocumentExtraction = {
  markdown: string;
  json: Record<string, unknown>;
  pages?: DocumentPageImage[];
};

export type ProcessedDocument = {
  id: string;
  fileName: string;
  uploadedAt: string;
  extraction: DocumentExtraction;
  durationMs?: number;
  documentDataUrl?: string;
};
