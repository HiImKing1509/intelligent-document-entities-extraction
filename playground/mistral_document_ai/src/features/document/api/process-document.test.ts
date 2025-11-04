import { describe, expect, it } from "vitest";
import { createDocumentProcessPayload, processDocumentViaApi } from "./process-document";

function createSamplePdf() {
  const pdfBytes = new Uint8Array([37, 80, 68, 70, 45, 49, 46, 55]); // %PDF-1.7
  const file = new File([pdfBytes], "sample.pdf", { type: "application/pdf" });
  const base64 = Buffer.from(pdfBytes).toString("base64");
  return { file, base64 };
}

describe("processDocumentViaApi", () => {
  it("builds the expected payload", () => {
    const { file, base64 } = createSamplePdf();
    const payload = createDocumentProcessPayload(file, base64);

    expect(payload.fileName).toBe("sample.pdf");
    expect(payload.mimeType).toBe("application/pdf");
    expect(payload.documentBase64).toBe(base64);
  });

  it("returns processed document with mock response", async () => {
    const { file, base64 } = createSamplePdf();
    const payload = createDocumentProcessPayload(file, base64);
    const result = await processDocumentViaApi(payload);

    expect(result.fileName).toBe("sample.pdf");
    expect(result.extraction.markdown).toContain("Superannuation");
    expect(result.extraction.pages?.length ?? 0).toBe(0);
    expect(result.documentDataUrl?.startsWith("data:application/pdf;base64,")).toBe(true);
  });
});
