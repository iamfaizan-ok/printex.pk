export const APP_CONFIG = {
  appName: 'PrintX',
  tagline: 'Professional Document Printing Made Effortless',
  maxFileSizeBytes: Number(import.meta.env.VITE_MAX_FILE_SIZE_BYTES) || 50 * 1024 * 1024, // 50MB default
  maxFilesCount: Number(import.meta.env.VITE_MAX_FILES_COUNT) || 10,
  maxCopiesPerDocument: 100,
  minCopiesPerDocument: 1,
  apiBaseUrl: import.meta.env.VITE_API_BASE_URL || '',
  storageKeyPrefix: 'printx_draft_meta_v1',
  supportEmail: 'support@printx.pk',
  cspWorkerSrc: 'blob: "self"',
} as const;
