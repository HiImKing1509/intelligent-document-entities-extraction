import { useCallback, useEffect, useRef, useState } from "react";
import { zodResolver } from "@hookform/resolvers/zod";
import { FileStack, Loader2, Wand2 } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { useForm } from "react-hook-form";
import { z } from "zod";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Badge } from "@/components/ui/badge";
import { cn, prettyDate } from "@/lib/utils";
import {
  createFileObjectUrl,
  dataUrlToObjectUrl,
  isPdf,
  readFileAsBase64,
  revokeFileObjectUrl
} from "@/lib/file";
import { createDocumentProcessPayload } from "@/features/document/api/process-document";
import { useProcessDocument } from "@/features/document/hooks/use-process-document";
import { useDocumentHistory } from "@/features/document/hooks/use-document-history";
import type { ProcessedDocument } from "@/types/document";

const MAX_FILE_SIZE_MB = 12;
const PREVIEW_HEIGHT_PX = 760;
const documentFormSchema = z.object({
  document: z
    .custom<FileList>()
    .refine((files) => files instanceof FileList && files.length > 0, "Select a PDF file.")
    .refine(
      (files) => {
        const file = files?.item(0);
        return file ? isPdf(file) : false;
      },
      {
        message: "Only PDF files are supported."
      }
    )
    .refine(
      (files) => {
        const file = files?.item(0);
        if (!file) {
          return false;
        }
        const sizeInMb = file.size / (1024 * 1024);
        return sizeInMb <= MAX_FILE_SIZE_MB;
      },
      {
        message: `File size must be under ${MAX_FILE_SIZE_MB} MB.`
      }
    )
});

type DocumentFormValues = z.infer<typeof documentFormSchema>;

export function DocumentPlaygroundPage() {
  const { history, addDocument, clearHistory } = useDocumentHistory();
  const [activeDocument, setActiveDocument] = useState<ProcessedDocument | null>(
    history[0] ?? null
  );
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors },
    setValue,
    trigger,
    reset,
    resetField
  } = useForm<DocumentFormValues>({
    resolver: zodResolver(documentFormSchema),
    mode: "onSubmit"
  });
  const documentField = register("document");

  const {
    mutateAsync: processDocument,
    isPending: isProcessing
  } = useProcessDocument({
    onSuccess: (doc) => {
      addDocument(doc);
      setActiveDocument(doc);
      reset();
      setSelectedFile(null);
      setPreviewUrl(null);
      resetField("document");
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    }
  });

  useEffect(() => {
    if (!activeDocument && history.length > 0) {
      setActiveDocument(history[0]);
    }
  }, [history, activeDocument]);

  useEffect(() => {
    if (!selectedFile) {
      setPreviewUrl(null);
      return;
    }

    const objectUrl = createFileObjectUrl(selectedFile);
    setPreviewUrl(objectUrl);
    return () => revokeFileObjectUrl(objectUrl);
  }, [selectedFile]);

  const handleFileSelection = useCallback(
    (fileList: FileList | null) => {
      if (!fileList || fileList.length === 0) {
        setSelectedFile(null);
        resetField("document");
        if (fileInputRef.current) {
          fileInputRef.current.value = "";
        }
        return;
      }

      const file = fileList.item(0);
      if (!file) {
        return;
      }

      setValue("document", fileList, { shouldValidate: true, shouldDirty: true });
      setSelectedFile(isPdf(file) ? file : null);
      void trigger("document");

      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    },
    [fileInputRef, isPdf, resetField, setSelectedFile, setValue, trigger]
  );

  const onSubmit = handleSubmit(async (values) => {
    const file = selectedFile ?? values.document.item(0);
    if (!file) {
      return;
    }

    const base64 = await readFileAsBase64(file);
    const payload = createDocumentProcessPayload(file, base64);
    await processDocument(payload);
  });

  return (
    <div className="space-y-6 p-6">
      <Card className="border-neutral-900/80 bg-neutral-950/80">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-lg">
            <Wand2 className="h-5 w-5 text-primary" />
            Parse a PDF document
          </CardTitle>
          <CardDescription className="text-neutral-400">
            Upload a PDF to run it through the Mistral Document AI endpoint. The file stays local in
            your browser—only the encoded content is sent to the API.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={onSubmit} className="space-y-4">
            <input
              id="file-input"
              type="file"
              accept="application/pdf"
              className="hidden"
              {...documentField}
              ref={(node) => {
                documentField.ref(node);
                fileInputRef.current = node;
              }}
              onChange={(event) => {
                documentField.onChange(event);
                handleFileSelection((event.target as HTMLInputElement).files);
              }}
            />
            <DropArea
              onBrowse={() => fileInputRef.current?.click()}
              onDropFiles={handleFileSelection}
              activeFile={selectedFile}
              isProcessing={isProcessing}
            />
            {errors.document ? (
              <p className="text-sm text-destructive">{errors.document.message}</p>
            ) : (
              selectedFile && (
                <p className="text-sm text-neutral-400">
                  Ready to upload <strong>{selectedFile.name}</strong> (
                  {(selectedFile.size / (1024 * 1024)).toFixed(2)} MB)
                </p>
              )
            )}
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <p className="text-xs text-neutral-500">
                The request automatically includes base64 snapshots to align with the API defaults.
              </p>
              <Button
                type="submit"
                disabled={isProcessing || !selectedFile}
                className="w-full sm:w-auto"
              >
                {isProcessing ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Processing…
                  </>
                ) : (
                  <>
                    <Wand2 className="mr-2 h-4 w-4" />
                    Extract document
                  </>
                )}
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 items-stretch gap-6 xl:grid-cols-[minmax(0,1.1fr)_minmax(0,1fr)]">
        <DocumentPreviewCard previewUrl={previewUrl} document={activeDocument} />
        <ExtractionResultsCard document={activeDocument} />
      </div>

      <HistoryPanel
        history={history}
        activeDocumentId={activeDocument?.id ?? null}
        onSelect={setActiveDocument}
        onClear={clearHistory}
      />
    </div>
  );
}

type DropAreaProps = {
  onBrowse: () => void;
  onDropFiles: (files: FileList | null) => void;
  activeFile: File | null;
  isProcessing: boolean;
};

function DropArea({ onBrowse, onDropFiles, activeFile, isProcessing }: DropAreaProps) {
  const [dragOver, setDragOver] = useState(false);

  return (
    <div
      onClick={onBrowse}
      onDragOver={(event) => {
        event.preventDefault();
        setDragOver(true);
      }}
      onDragLeave={() => setDragOver(false)}
      onDrop={(event) => {
        event.preventDefault();
        setDragOver(false);
        onDropFiles(event.dataTransfer?.files ?? null);
      }}
      onKeyDown={(event) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          onBrowse();
        }
      }}
      role="button"
      tabIndex={0}
      aria-disabled={isProcessing}
      className={cn(
        "flex cursor-pointer flex-col items-center justify-center rounded-xl border border-dashed border-neutral-800 bg-neutral-900/40 px-6 py-12 text-center transition hover:border-primary/60 hover:bg-neutral-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 focus-visible:ring-offset-neutral-950",
        dragOver && "border-primary/80 bg-neutral-900/60",
        isProcessing && "pointer-events-none opacity-50"
      )}
    >
      <FileStack className="mb-4 h-10 w-10 text-primary" />
      <p className="text-base font-medium text-neutral-100">
        {activeFile ? "Replace the current PDF" : "Drop a PDF document here"}
      </p>
      <p className="mt-2 text-sm text-neutral-400">
        {activeFile
          ? activeFile.name
          : "Click to browse or drag & drop. PDF up to 12 MB supported."}
      </p>
      <Badge className="mt-4 bg-primary/20 text-primary-foreground">PDF only</Badge>
    </div>
  );
}

type DocumentPreviewProps = {
  previewUrl: string | null;
  document: ProcessedDocument | null;
};

function DocumentPreviewCard({ previewUrl, document }: DocumentPreviewProps) {
  const [documentUrl, setDocumentUrl] = useState<string | null>(null);

  useEffect(() => {
    if (!document?.documentDataUrl) {
      setDocumentUrl(null);
      return;
    }

    const url = dataUrlToObjectUrl(document.documentDataUrl);
    setDocumentUrl(url);

    return () => {
      revokeFileObjectUrl(url);
    };
  }, [document?.documentDataUrl]);

  const sourceUrl = previewUrl ?? documentUrl ?? null;
  const thumbnails = document?.extraction.pages ?? [];
  const previewHeightStyle = {
    height: `clamp(360px, calc(100vh - 280px), ${PREVIEW_HEIGHT_PX}px)`
  };

  return (
    <Card className="flex flex-col border-neutral-900/80 bg-neutral-950/80">
      <CardHeader>
        <CardTitle className="text-lg">Original document</CardTitle>
        <CardDescription className="text-neutral-400">
          The uploaded PDF is rendered in-browser. No document is persisted on the server.
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        {sourceUrl ? (
          <>
            <div
              className="overflow-hidden rounded-lg border border-neutral-900 bg-neutral-900"
              style={previewHeightStyle}
            >
              <object title="PDF preview" data={sourceUrl} type="application/pdf" className="h-full w-full">
                <div className="flex h-full w-full items-center justify-center bg-neutral-900 text-sm text-neutral-400">
                  Unable to preview PDF.{" "}
                  <a className="ml-2 underline" href={sourceUrl} target="_blank" rel="noreferrer">
                    Download instead
                  </a>
                </div>
              </object>
            </div>
            {thumbnails.length > 0 && (
              <div>
                <h4 className="mb-2 text-sm font-semibold text-neutral-200">Page snapshots</h4>
                <div className="grid grid-cols-2 gap-3 lg:grid-cols-3">
                  {thumbnails.map((page) => (
                    <div
                      key={page.id}
                      className="overflow-hidden rounded border border-neutral-900 bg-neutral-900"
                    >
                      <img
                        src={`data:image/png;base64,${page.base64}`}
                        alt={`Page ${page.pageNumber}`}
                        className="w-full object-cover"
                      />
                      <div className="px-2 py-1 text-xs text-neutral-500">Page {page.pageNumber}</div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </>
        ) : (
          <div style={previewHeightStyle} className="flex items-center justify-center">
            <EmptyState
              title="Upload a PDF document to preview it here"
              description="You can also revisit previously processed documents from the history panel below."
              className="h-full w-full"
            />
          </div>
        )}
      </CardContent>
    </Card>
  );
}

type ExtractionResultsProps = {
  document: ProcessedDocument | null;
};

function ExtractionResultsCard({ document }: ExtractionResultsProps) {
  const previewHeightStyle = {
    height: `clamp(360px, calc(100vh - 280px), ${PREVIEW_HEIGHT_PX}px)`
  };

  return (
    <Card className="flex flex-col border-neutral-900/80 bg-neutral-950/80">
      <CardHeader>
        <CardTitle className="text-lg">Extraction results</CardTitle>
        <CardDescription className="text-neutral-400">
          Explore the markdown friendly output or inspect the raw JSON payload for downstream
          integrations.
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        {document ? (
          <Tabs defaultValue="markdown" className="flex flex-col gap-4">
            <TabsList>
              <TabsTrigger value="markdown">Markdown</TabsTrigger>
              <TabsTrigger value="json">JSON</TabsTrigger>
            </TabsList>
            <TabsContent value="markdown" className="h-full" style={previewHeightStyle}>
              <ScrollArea className="h-full">
                <article className="prose prose-invert max-w-none">
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>
                    {document.extraction.markdown}
                  </ReactMarkdown>
                </article>
              </ScrollArea>
            </TabsContent>
            <TabsContent value="json" className="h-full" style={previewHeightStyle}>
              <ScrollArea className="h-full">
                <pre className="whitespace-pre-wrap rounded-md bg-neutral-900/80 p-4 text-xs text-neutral-100">
                  {JSON.stringify(document.extraction.json, null, 2)}
                </pre>
              </ScrollArea>
            </TabsContent>
          </Tabs>
        ) : (
          <div style={previewHeightStyle} className="flex items-center justify-center">
            <EmptyState
              title="No results yet"
              description="Process a PDF document to view markdown and JSON outputs side by side."
              className="h-full w-full"
            />
          </div>
        )}
      </CardContent>
      {document && (
        <CardFooter className="flex flex-wrap justify-between gap-2 text-xs text-neutral-500">
          <span>{document.fileName}</span>
          <span>Processed {prettyDate(document.uploadedAt)}</span>
          {document.durationMs ? <span>{document.durationMs} ms</span> : null}
        </CardFooter>
      )}
    </Card>
  );
}

type HistoryPanelProps = {
  history: ProcessedDocument[];
  activeDocumentId: string | null;
  onSelect: (doc: ProcessedDocument) => void;
  onClear: () => void;
};

function HistoryPanel({ history, activeDocumentId, onSelect, onClear }: HistoryPanelProps) {
  return (
    <Card className="border-neutral-900/80 bg-neutral-950/80">
      <CardHeader className="flex flex-row items-center justify-between">
        <div>
          <CardTitle className="text-lg">Recent runs</CardTitle>
          <CardDescription className="text-neutral-400">
            Stored locally in your browser so you can revisit previous API responses.
          </CardDescription>
        </div>
        <Button
          type="button"
          variant="ghost"
          size="sm"
          onClick={onClear}
          disabled={history.length === 0}
        >
          Clear
        </Button>
      </CardHeader>
      <CardContent>
        {history.length === 0 ? (
          <EmptyState
            title="No history yet"
            description="Process a document and it appears here for quick recall."
          />
        ) : (
          <div className="space-y-3">
            {history.map((doc) => {
              const isActive = doc.id === activeDocumentId;
              return (
                <button
                  key={doc.id}
                  type="button"
                  onClick={() => onSelect(doc)}
                  className={cn(
                    "w-full rounded-lg border border-transparent bg-neutral-900/60 px-4 py-3 text-left transition hover:border-primary/40 hover:bg-neutral-900",
                    isActive && "border-primary/60 bg-primary/10"
                  )}
                >
                  <div className="flex items-center justify-between text-sm font-medium text-neutral-100">
                    <span className="truncate">{doc.fileName}</span>
                    {doc.durationMs ? <span>{doc.durationMs} ms</span> : null}
                  </div>
                  <div className="mt-1 text-xs text-neutral-500">{prettyDate(doc.uploadedAt)}</div>
                </button>
              );
            })}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

type EmptyStateProps = {
  title: string;
  description: string;
  className?: string;
};

function EmptyState({ title, description, className }: EmptyStateProps) {
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center rounded-lg border border-neutral-900/80 bg-neutral-900/40 px-6 py-12 text-center",
        className
      )}
    >
      <p className="text-base font-medium text-neutral-200">{title}</p>
      <p className="mt-2 max-w-xl text-sm text-neutral-400">{description}</p>
    </div>
  );
}
