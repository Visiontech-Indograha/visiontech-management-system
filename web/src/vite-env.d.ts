/// <reference types="vite/client" />
interface ImportMetaEnv {
  readonly VITE_API_BASE_URL?: string;
  readonly VITE_MOCK_ROLE?: string;
}
/** Versi aplikasi (SemVer), diisi Vite dari web/package.json. */
declare const __APP_VERSION__: string;
interface ImportMeta {
  readonly env: ImportMetaEnv;
}
