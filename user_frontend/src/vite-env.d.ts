/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE_URL?: string;
  readonly VITE_MAX_FILE_SIZE_BYTES?: string;
  readonly VITE_MAX_FILES_COUNT?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
