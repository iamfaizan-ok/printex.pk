import { APP_CONFIG } from '../config/appConfig';
import { PrintDraft } from '../types/printDraft';

const STORAGE_KEY = `${APP_CONFIG.storageKeyPrefix}_state`;

/**
 * Persists non-sensitive draft metadata to sessionStorage.
 * Note: Raw File objects and binary PDF contents are NEVER stored in sessionStorage/localStorage.
 */
export const storageService = {
  saveDraftMetadata(draft: PrintDraft): void {
    try {
      if (typeof window === 'undefined' || !window.sessionStorage) return;

      // Strip in-memory references (File, objectUrl) before serializing
      const serializableDraft = {
        ...draft,
        files: draft.files.map((f) => ({
          fileId: f.fileId,
          originalFileName: f.originalFileName,
          fileSize: f.fileSize,
          pageCount: f.pageCount,
          processingStatus: f.processingStatus,
          printSettings: f.printSettings,
          uploadedAt: f.uploadedAt,
          errorMessage: f.errorMessage,
        })),
      };

      sessionStorage.setItem(STORAGE_KEY, JSON.stringify(serializableDraft));
    } catch {
      // Gracefully handle storage quotas or privacy mode restrictions
      console.warn('Unable to persist draft metadata to sessionStorage.');
    }
  },

  getSavedDraftMetadata(): Partial<PrintDraft> | null {
    try {
      if (typeof window === 'undefined' || !window.sessionStorage) return null;
      const raw = sessionStorage.getItem(STORAGE_KEY);
      if (!raw) return null;
      return JSON.parse(raw);
    } catch {
      return null;
    }
  },

  clearDraftMetadata(): void {
    try {
      if (typeof window === 'undefined' || !window.sessionStorage) return;
      sessionStorage.removeItem(STORAGE_KEY);
    } catch {
      // Ignore
    }
  },
};
