import { createBrowserRouter, createRoutesFromElements, Route } from "react-router-dom";
import { AppLayout } from "@/routes/app-layout";
import { DocumentPlaygroundPage } from "@/routes/document-playground-page";
import { NotFoundPage } from "@/routes/not-found-page";

const router = createBrowserRouter(
  createRoutesFromElements(
    <Route path="/" element={<AppLayout />} errorElement={<NotFoundPage />}>
      <Route index element={<DocumentPlaygroundPage />} />
      <Route path="*" element={<NotFoundPage />} />
    </Route>
  ),
  {
    basename: import.meta.env.BASE_URL
  }
);

export default router;
