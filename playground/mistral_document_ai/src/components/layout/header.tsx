import { BookOpen, Github } from "lucide-react";
import { Button } from "@/components/ui/button";

const DOCS_URL =
  "https://learn.microsoft.com/en-us/azure/ai-services/document-intelligence/overview";
const REPO_URL = "https://github.com/your-org/intelligent-document-entities-extraction";

export function Header() {
  return (
    <header className="flex items-center justify-between border-b border-neutral-900/80 bg-neutral-950/80 px-6 py-4 backdrop-blur">
      <div>
        <p className="text-xs uppercase tracking-wide text-neutral-500">Mistral Playground</p>
        <h1 className="text-xl font-semibold text-neutral-100">
          Agentic Document Extraction
        </h1>
      </div>
      <div className="flex items-center gap-3">
        <Button asChild variant="ghost" size="sm" className="hidden sm:inline-flex">
          <a href={REPO_URL} target="_blank" rel="noreferrer">
            <Github className="mr-2 h-4 w-4" />
            GitHub
          </a>
        </Button>
        <Button asChild variant="outline" size="sm">
          <a href={DOCS_URL} target="_blank" rel="noreferrer">
            <BookOpen className="mr-2 h-4 w-4" />
            API Docs
          </a>
        </Button>
      </div>
    </header>
  );
}
