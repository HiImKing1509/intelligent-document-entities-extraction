const REQUIRED_ENV_VARS = ["VITE_MISTRAL_API_BASE_URL"] as const;

type EnvKey = (typeof REQUIRED_ENV_VARS)[number];

function readEnv(key: EnvKey): string {
  const value = import.meta.env[key];
  if (!value) {
    throw new Error(`Missing required environment variable: ${key}`);
  }
  return value;
}

export function getMistralEndpoint() {
  return readEnv("VITE_MISTRAL_API_BASE_URL");
}

export function getApiKey() {
  return import.meta.env.VITE_MISTRAL_API_KEY;
}

export function shouldUseMocks() {
  return import.meta.env.VITE_USE_MOCKS !== "false";
}
