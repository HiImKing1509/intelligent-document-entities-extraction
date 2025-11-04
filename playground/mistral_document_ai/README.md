# Mistral Document AI Playground

A React + Vite playground for experimenting with the Mistral Document AI endpoint. Upload a PDF, inspect the extracted markdown and JSON, and keep a local history of previous runs.

## Features

- 📄 Drag-and-drop PDF upload with inline validation
- 🔁 Runs Mistral Document AI requests through TanStack Query with optimistic status
- 🪄 Dual-pane layout: original PDF preview alongside markdown/JSON results
- 💾 LocalStorage backed history so you can revisit prior API responses
- 🛠️ MSW-powered mock layer for offline and development workflows
- ✅ TypeScript strict mode, ESLint, Prettier, Vitest + Testing Library
- 🎨 Tailwind CSS with shadcn/ui primitives and lucide-react icons

## Getting Started

```bash
# 1. Move into the project
cd playground/mistral_document_ai

# 2. Install dependencies
npm install

# 3. Copy environment template and provide secrets
cp .env.example .env
# Set VITE_MISTRAL_API_KEY (when using the real API)
# Optionally override VITE_MISTRAL_API_BASE_URL or toggle VITE_USE_MOCKS=false

# 4. Start the dev server
npm run dev
```

The mock service worker is enabled by default in development so you can explore the UI instantly. Once you are ready to call the real Azure endpoint, set `VITE_USE_MOCKS=false` in your `.env` file and provide `VITE_MISTRAL_API_KEY`.

### Testing & Linting

```bash
# Run unit tests
npm test

# Lint and format code
npm run lint
npm run format
```

### Build & Preview

```bash
npm run build
npm run preview
```

## Project Structure

```
src/
├─ components/    # Reusable UI primitives and layout pieces
├─ features/      # Domain-specific logic (document processing hooks/API)
├─ mocks/         # MSW handlers for local development and tests
├─ routes/        # Router-aware pages and layouts
├─ test/          # Vitest setup
└─ lib/           # Utilities and helpers (env, file encoding, etc.)
```

## Environment Variables

| Variable                    | Required | Description                                                             |
| --------------------------- | -------- | ----------------------------------------------------------------------- |
| `VITE_MISTRAL_API_BASE_URL` | ✅       | Base URL of the Mistral Document AI endpoint (Azure-hosted by default). |
| `VITE_MISTRAL_API_KEY`      | ✅*      | Bearer token for authenticated requests. Required once mocks are off.   |
| `VITE_USE_MOCKS`            | optional | `true` (default) uses MSW mock API. Set to `false` for real requests.   |

> ℹ️ The application never stores uploaded PDFs on a backend. Files are converted to base64 and posted directly to the Mistral endpoint.

## Next Steps

- Wire the history list to allow renaming or tagging runs
- Add fine-grained error surfacing for Azure quota responses
- Extend UI with page-by-page diffing or side-by-side comparisons
