import { APP_CONFIG } from '../config/appConfig';

export interface ValidationResult {
  isValid: boolean;
  errorCode?: 'EMPTY_FILE' | 'INVALID_TYPE' | 'INVALID_MAGIC_BYTES' | 'FILE_TOO_LARGE' | 'NAME_TOO_LONG' | 'READ_ERROR';
  errorMessage?: string;
}

/**
 * Sanitizes a filename to prevent path traversal, control character exploits, or display issues.
 */
export function sanitizeFileName(fileName: string): string {
  if (!fileName) return 'unnamed_document.pdf';

  // Extract base filename (strip any path components)
  const baseName = fileName.replace(/^.*[\\/]/, '');

  // Strip dangerous control characters (0x00 - 0x1F, 0x7F)
  let clean = baseName.replace(/[\x00-\x1f\x7f]/g, '');

  // Replace potentially problematic characters with safe underscores
  clean = clean.replace(/[<>:"/\\|?*]/g, '_').trim();

  // Limit length while preserving file extension
  if (clean.length > 100) {
    const dotIndex = clean.lastIndexOf('.');
    const ext = dotIndex !== -1 ? clean.substring(dotIndex) : '';
    clean = clean.substring(0, Math.max(10, 100 - ext.length)) + ext;
  }

  return clean || 'document';
}

/**
 * Determines file category from filename extension or MIME type.
 */
export function getFileType(file: File): 'pdf' | 'image' | 'unsupported' {
  if (!file) return 'unsupported';
  const name = file.name.toLowerCase();
  const type = file.type.toLowerCase();

  if (name.endsWith('.pdf') || type === 'application/pdf') {
    return 'pdf';
  }

  const imageExtensions = ['.jpg', '.jpeg', '.png', '.webp', '.bmp', '.svg'];
  const isImageExt = imageExtensions.some((ext) => name.endsWith(ext));
  if (isImageExt || type.startsWith('image/')) {
    return 'image';
  }

  return 'unsupported';
}

/**
 * Checks basic file attributes: existence, non-empty size, maximum size, and supported format (PDF or Image).
 */
export function validateBasicFile(
  file: File,
  maxSizeBytes: number = APP_CONFIG.maxFileSizeBytes
): ValidationResult {
  if (!file) {
    return {
      isValid: false,
      errorCode: 'EMPTY_FILE',
      errorMessage: 'No file was provided.',
    };
  }

  // Check for 0 byte empty file
  if (file.size === 0) {
    return {
      isValid: false,
      errorCode: 'EMPTY_FILE',
      errorMessage: 'The selected file is empty (0 bytes). Please upload a valid document or image.',
    };
  }

  // Check file size limit
  if (file.size > maxSizeBytes) {
    const limitMB = Math.round(maxSizeBytes / (1024 * 1024));
    return {
      isValid: false,
      errorCode: 'FILE_TOO_LARGE',
      errorMessage: `File exceeds the maximum upload limit of ${limitMB} MB.`,
    };
  }

  // Check file type (PDF or Image)
  const category = getFileType(file);
  if (category === 'unsupported') {
    return {
      isValid: false,
      errorCode: 'INVALID_TYPE',
      errorMessage: 'Unsupported file format. Please upload PDF documents or images (.jpg, .png, .webp, .svg).',
    };
  }

  return { isValid: true };
}

/**
 * Validates the file signature / magic bytes asynchronously.
 * Real PDF files must begin with `%PDF-` (0x25, 0x50, 0x44, 0x46, 0x2D).
 */
export async function validatePdfMagicBytes(file: File): Promise<ValidationResult> {
  try {
    let arrayBuffer: ArrayBuffer;

    if (typeof file.arrayBuffer === 'function') {
      try {
        const slice = file.slice ? file.slice(0, 5) : file;
        if (typeof slice.arrayBuffer === 'function') {
          arrayBuffer = await slice.arrayBuffer();
        } else {
          arrayBuffer = await file.arrayBuffer();
        }
      } catch {
        arrayBuffer = await file.arrayBuffer();
      }
    } else if (typeof FileReader !== 'undefined') {
      arrayBuffer = await new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => resolve(reader.result as ArrayBuffer);
        reader.onerror = () => reject(new Error('FileReader failed'));
        reader.readAsArrayBuffer(file.slice ? file.slice(0, 5) : file);
      });
    } else {
      return {
        isValid: false,
        errorCode: 'READ_ERROR',
        errorMessage: 'File reading API is not available.',
      };
    }

    const bytes = new Uint8Array(arrayBuffer);

    // %PDF- magic bytes: 0x25, 0x50, 0x44, 0x46, 0x2D
    const magicHeader = [0x25, 0x50, 0x44, 0x46, 0x2d];

    if (bytes.length < 5) {
      return {
        isValid: false,
        errorCode: 'INVALID_MAGIC_BYTES',
        errorMessage: 'File header is too short to be a valid PDF document.',
      };
    }

    for (let i = 0; i < 5; i++) {
      if (bytes[i] !== magicHeader[i]) {
        return {
          isValid: false,
          errorCode: 'INVALID_MAGIC_BYTES',
          errorMessage: 'Invalid file signature. The file does not have a genuine PDF header.',
        };
      }
    }

    return { isValid: true };
  } catch {
    return {
      isValid: false,
      errorCode: 'READ_ERROR',
      errorMessage: 'Failed to read file contents for signature verification.',
    };
  }
}
