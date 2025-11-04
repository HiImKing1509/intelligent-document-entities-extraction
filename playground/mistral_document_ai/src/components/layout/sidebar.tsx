import { FolderOpenDot, Upload } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";

const EXAMPLE_FILES = [
  {
    name: "Invoice Sample.pdf",
    description: "Typical multi-page invoice layout"
  },
  {
    name: "Bank Statement.pdf",
    description: "Financial statement with tables"
  }
];

export function Sidebar() {
  return (
    <aside className="hidden w-[280px] border-r border-neutral-900/80 bg-neutral-950/90 text-sm lg:flex lg:flex-col">
      <div className="flex items-center gap-2 px-6 py-4">
        <FolderOpenDot className="h-5 w-5 text-primary" />
        <span className="text-sm font-medium uppercase tracking-wide text-neutral-400">
          Files
        </span>
      </div>
      <Separator />
      <div className="flex flex-1 flex-col justify-between overflow-y-auto">
        <div className="px-6 py-4">
          <p className="mb-4 text-xs text-neutral-400">
            Upload PDF documents to run through the Mistral Document AI endpoint. Results will be
            stored locally so you can revisit them later.
          </p>
          <Button
            variant="secondary"
            size="sm"
            className="w-full"
            onClick={() => {
              document.getElementById("file-input")?.click();
            }}
          >
            <Upload className="mr-2 h-4 w-4" />
            Upload PDF
          </Button>
        </div>
        <Separator />
        <div className="px-6 py-4">
          <h3 className="mb-3 text-xs font-semibold uppercase tracking-wide text-neutral-500">
            Example Files
          </h3>
          <ul className="space-y-3">
            {EXAMPLE_FILES.map((file) => (
              <li key={file.name}>
                <p className="font-medium text-neutral-200">{file.name}</p>
                <p className="text-xs text-neutral-500">{file.description}</p>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </aside>
  );
}
