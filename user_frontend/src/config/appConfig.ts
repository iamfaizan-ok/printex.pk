function resolveDefaultApiBaseUrl(): string {
  if (typeof window !== 'undefined' && window.location) {
    const { hostname } = window.location;
    if (hostname.endsWith('.onrender.com')) {
      return 'https://printx-backend.onrender.com/api/v1';
    }
    // In browser, relative URL '/api/v1' routes requests to the same origin (port 3000)
    // where Vite dev server reliably proxies them to Django at http://127.0.0.1:8000.
    // This completely eliminates cross-origin issues, firewall blocks, and IP mismatches on PC & mobile.
    return '/api/v1';
  }
  const envUrl = import.meta.env.VITE_API_BASE_URL;
  return envUrl && envUrl.trim().length > 0 ? envUrl.trim() : 'http://127.0.0.1:8000/api/v1';
}

export const APP_CONFIG = {
  appName: 'PrintX',
  tagline: 'Professional Document Printing Made Effortless',
  maxFileSizeBytes: Number(import.meta.env.VITE_MAX_FILE_SIZE_BYTES) || 50 * 1024 * 1024, // 50MB default
  maxFilesCount: Number(import.meta.env.VITE_MAX_FILES_COUNT) || 10,
  maxCopiesPerDocument: 100,
  minCopiesPerDocument: 1,
  apiBaseUrl: resolveDefaultApiBaseUrl(),
  storageKeyPrefix: 'printx_draft_meta_v1',
  supportEmail: 'support@printx.pk',
  cspWorkerSrc: 'blob: "self"',
} as const;
