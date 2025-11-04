import "@/index.css";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ReactQueryDevtools } from "@tanstack/react-query-devtools";
import { RouterProvider } from "react-router-dom";
import router from "@/router";
import { Toaster } from "@/components/ui/sonner";

async function enableMocking() {
  if (import.meta.env.VITE_USE_MOCKS === "false") {
    return;
  }

  if (import.meta.env.DEV) {
    try {
      const { worker } = await import("@/mocks/browser");
      await worker.start({
        onUnhandledRequest: "bypass",
        serviceWorker: {
          url: "/mockServiceWorker.js"
        }
      });
    } catch (error) {
      console.warn("MSW failed to start. Falling back to inline mocks.", error);
    }
  }
}

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
      staleTime: 1000 * 30
    }
  }
});

enableMocking().finally(() => {
  const rootElement = document.getElementById("root");
  if (!rootElement) {
    throw new Error("Root element not found");
  }

  createRoot(rootElement).render(
    <StrictMode>
      <QueryClientProvider client={queryClient}>
        <RouterProvider router={router} />
        <ReactQueryDevtools initialIsOpen={false} />
        <Toaster richColors position="bottom-right" />
      </QueryClientProvider>
    </StrictMode>
  );
});
