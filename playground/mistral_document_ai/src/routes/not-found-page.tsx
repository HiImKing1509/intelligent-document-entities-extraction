import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";

export function NotFoundPage() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-6 bg-neutral-950 text-neutral-100">
      <div className="text-center">
        <h1 className="text-6xl font-bold tracking-tight text-primary/80">404</h1>
        <p className="mt-4 text-xl font-semibold">Page not found</p>
        <p className="mt-2 max-w-md text-sm text-neutral-400">
          The page you are looking for does not exist or has been moved. Head back to the playground
          to keep exploring the API.
        </p>
      </div>
      <Button asChild variant="outline">
        <Link to="/">Return to playground</Link>
      </Button>
    </div>
  );
}
