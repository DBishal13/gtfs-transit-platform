/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** Base URL of the backend service (service/), e.g. "https://api.example.com". Unset
   * in the GitHub Pages static build (see .github/workflows/deploy.yml) — apiClient.ts's
   * isBackendConfigured() is false there, so dispatch/auth UI never renders. */
  readonly VITE_API_BASE_URL?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
