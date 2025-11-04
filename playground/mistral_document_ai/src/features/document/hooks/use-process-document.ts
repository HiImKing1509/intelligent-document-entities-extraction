import { useMutation } from "@tanstack/react-query";
import { toast } from "@/components/ui/sonner";
import { processDocumentViaApi } from "@/features/document/api/process-document";
import type { DocumentProcessPayload, ProcessedDocument } from "@/types/document";

type Options = {
  onSuccess?: (document: ProcessedDocument) => void;
};

export function useProcessDocument(options?: Options) {
  return useMutation({
    mutationFn: (payload: DocumentProcessPayload) => processDocumentViaApi(payload),
    onSuccess: (data) => {
      toast.success("Document processed", {
        description: `${data.fileName} finished in ${data.durationMs ?? 0} ms`
      });
      options?.onSuccess?.(data);
    },
    onError: (error: unknown) => {
      const message = error instanceof Error ? error.message : "Unknown error";
      toast.error("Processing failed", {
        description: message
      });
    }
  });
}
