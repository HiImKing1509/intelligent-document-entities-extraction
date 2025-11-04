import { http, HttpResponse } from "msw";
import superOngoingFeeConsent from "@/mocks/fixtures/super-ongoing-fee-consent-sample-1.json";

export const handlers = [
  http.post("/api/document/process", async ({ request }) => {
    const body = await request.json();
    const filename =
      typeof body?.document?.document_url === "string"
        ? body.document.document_url
        : "uploaded.pdf";

    const concatenatedMarkdown = superOngoingFeeConsent.pages
      .map((page) => page.markdown.trim())
      .join("\n\n---\n\n");

    const pages = superOngoingFeeConsent.pages.map((page) => ({
      page_number: page.index + 1,
      image_base64: page.images?.[0] ?? undefined,
    }));

    return HttpResponse.json({
      result: {
        markdown: concatenatedMarkdown,
        json: superOngoingFeeConsent,
        pages,
        file_name: filename,
        duration_ms: 1200,
      },
    });
  }),
];
