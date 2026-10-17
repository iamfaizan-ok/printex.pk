import { PrintSettings } from './printSettings';

export type FileProcessingStatus = 'pending' | 'validating' | 'ready' | 'error';

export interface PrintFile {
  fileId: string;
  originalFileName: string;
  fileSize: number;
  pageCount: number; // 0 if pending or error
  processingStatus: FileProcessingStatus;
  printSettings: PrintSettings;
  file?: File; // in-memory browser reference
  objectUrl?: string; // in-memory preview URL, cleaned up when unmounted/removed
  errorMessage?: string;
  fileType?: 'pdf' | 'image';
  uploadedAt: string; // ISO date string
}

export interface FileValidationError {
  code: 'INVALID_TYPE' | 'CORRUPT_PDF' | 'PASSWORD_PROTECTED' | 'FILE_TOO_LARGE' | 'MAX_FILES_EXCEEDED' | 'READ_ERROR';
  message: string;
}
