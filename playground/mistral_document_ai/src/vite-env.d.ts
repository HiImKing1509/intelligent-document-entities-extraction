/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_MISTRAL_API_KEY?: string;
  readonly VITE_MISTRAL_API_BASE_URL: string;
  readonly VITE_USE_MOCKS?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
