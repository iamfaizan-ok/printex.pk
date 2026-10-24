import React, { createContext, useContext, useReducer, useEffect, useCallback, useMemo } from 'react';
import { PrintDraft, PrintDraftAction, WorkflowStep } from '../types/printDraft';
import { PrintFile } from '../types/printFile';
import { PrintSettings } from '../types/printSettings';
import { DEFAULT_PRINT_SETTINGS } from '../config/printDefaults';
import { APP_CONFIG } from '../config/appConfig';
import { generateId } from '../utils/generateId';
import { sanitizeFileName, validateBasicFile, validatePdfMagicBytes, getFileType } from '../utils/fileValidation';
import { pdfService } from '../services/pdfService';
import { storageService } from '../services/storageService';
import { calculateDraftTotals, OverallOrderCalculation } from '../utils/printCalculations';

const initialDraft: PrintDraft = {
  draftId: generateId('draft'),
  createdAt: new Date().toISOString(),
  updatedAt: new Date().toISOString(),
  currentStep: 'upload',
  files: [],
};

function printDraftReducer(state: PrintDraft, action: PrintDraftAction): PrintDraft {
  switch (action.type) {
    case 'SET_FILES':
      return {
        ...state,
        files: action.payload,
        updatedAt: new Date().toISOString(),
      };

    case 'ADD_FILES': {
      const remainingSlots = Math.max(0, APP_CONFIG.maxFilesCount - state.files.length);
      const filesToAdd = action.payload.slice(0, remainingSlots);
      return {
        ...state,
        files: [...state.files, ...filesToAdd],
        updatedAt: new Date().toISOString(),
      };
    }

    case 'UPDATE_FILE':
      return {
        ...state,
        files: state.files.map((file) =>
          file.fileId === action.payload.fileId
            ? { ...file, ...action.payload.updates }
            : file
        ),
        updatedAt: new Date().toISOString(),
      };

    case 'UPDATE_FILE_SETTINGS':
      return {
        ...state,
        files: state.files.map((file) =>
          file.fileId === action.payload.fileId
            ? {
                ...file,
                printSettings: {
                  ...file.printSettings,
                  ...action.payload.settings,
                },
              }
            : file
        ),
        updatedAt: new Date().toISOString(),
      };

    case 'UPDATE_MULTIPLE_FILES_SETTINGS': {
      const targetIdSet = new Set(action.payload.fileIds);
      return {
        ...state,
        files: state.files.map((file) =>
          targetIdSet.has(file.fileId)
            ? {
                ...file,
                printSettings: {
                  ...file.printSettings,
                  ...action.payload.settings,
                },
              }
            : file
        ),
        updatedAt: new Date().toISOString(),
      };
    }

    case 'REMOVE_FILE': {
      const fileToRemove = state.files.find((f) => f.fileId === action.payload.fileId);
      if (fileToRemove?.objectUrl) {
        URL.revokeObjectURL(fileToRemove.objectUrl);
      }
      return {
        ...state,
        files: state.files.filter((f) => f.fileId !== action.payload.fileId),
        updatedAt: new Date().toISOString(),
      };
    }

    case 'REORDER_FILES': {
      const { startIndex, endIndex } = action.payload;
      if (
        startIndex < 0 ||
        startIndex >= state.files.length ||
        endIndex < 0 ||
        endIndex >= state.files.length ||
        startIndex === endIndex
      ) {
        return state;
      }

      const updated = [...state.files];
      const [moved] = updated.splice(startIndex, 1);
      updated.splice(endIndex, 0, moved);

      return {
        ...state,
        files: updated,
        updatedAt: new Date().toISOString(),
      };
    }

    case 'REPLACE_FILE': {
      const { fileId, newFile } = action.payload;
      const existing = state.files.find((f) => f.fileId === fileId);
      if (existing?.objectUrl) {
        URL.revokeObjectURL(existing.objectUrl);
      }

      return {
        ...state,
        files: state.files.map((f) => (f.fileId === fileId ? newFile : f)),
        updatedAt: new Date().toISOString(),
      };
    }

    case 'CLEAR_DRAFT':
      // Clean up all object URLs to avoid memory leaks
      state.files.forEach((f) => {
        if (f.objectUrl) {
          URL.revokeObjectURL(f.objectUrl);
        }
      });
      return {
        draftId: generateId('draft'),
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
        currentStep: 'upload',
        files: [],
      };

    case 'SET_CURRENT_STEP':
      return {
        ...state,
        currentStep: action.payload,
        updatedAt: new Date().toISOString(),
      };

    case 'LOAD_DRAFT':
      return {
        ...action.payload,
        updatedAt: new Date().toISOString(),
      };

    default:
      return state;
  }
}

export interface PrintDraftContextValue {
  draft: PrintDraft;
  totals: OverallOrderCalculation;
  canProceedToSettings: boolean;
  canProceedToReview: boolean;
  addRawFiles: (files: File[]) => Promise<void>;
  updateFileSettings: (fileId: string, settings: Partial<PrintSettings>) => void;
  updateMultipleFilesSettings: (fileIds: string[], settings: Partial<PrintSettings>) => void;
  removeFile: (fileId: string) => void;
  reorderFiles: (startIndex: number, endIndex: number) => void;
  replaceRawFile: (fileId: string, newFile: File) => Promise<void>;
  clearDraft: () => void;
  setCurrentStep: (step: WorkflowStep) => void;
  getFileById: (fileId: string) => PrintFile | undefined;
}

const PrintDraftContext = createContext<PrintDraftContextValue | null>(null);

export const PrintDraftProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [draft, dispatch] = useReducer(printDraftReducer, initialDraft);

  // Sync metadata to sessionStorage when draft updates
  useEffect(() => {
    storageService.saveDraftMetadata(draft);
  }, [draft]);

  // Clean up remaining object URLs on provider unmount
  useEffect(() => {
    return () => {
      draft.files.forEach((f) => {
        if (f.objectUrl) URL.revokeObjectURL(f.objectUrl);
      });
    };
  }, []);

  // Process a single file: validate basic attributes, magic bytes, and inspect PDF page count
  const processRawFile = useCallback(async (rawFile: File): Promise<PrintFile> => {
    const fileId = generateId('file');
    const safeName = sanitizeFileName(rawFile.name);

    // Initial placeholder item
    const printFile: PrintFile = {
      fileId,
      originalFileName: safeName,
      fileSize: rawFile.size,
      pageCount: 0,
      processingStatus: 'validating',
      printSettings: { ...DEFAULT_PRINT_SETTINGS },
      file: rawFile,
      uploadedAt: new Date().toISOString(),
    };

    // 1. Basic validation (size, extension/format)
    const basicCheck = validateBasicFile(rawFile);
    if (!basicCheck.isValid) {
      return {
        ...printFile,
        processingStatus: 'error',
        errorMessage: basicCheck.errorMessage || 'Invalid file.',
      };
    }

    const fileType = getFileType(rawFile);

    // If image (JPG, PNG, WEBP, etc.), prepare directly with 1 page count
    if (fileType === 'image') {
      const objectUrl = URL.createObjectURL(rawFile);
      return {
        ...printFile,
        fileType: 'image',
        pageCount: 1,
        processingStatus: 'ready',
        objectUrl,
      };
    }

    // For PDF documents:
    // 2. Magic byte validation (%PDF-)
    const magicCheck = await validatePdfMagicBytes(rawFile);
    if (!magicCheck.isValid) {
      return {
        ...printFile,
        fileType: 'pdf',
        processingStatus: 'error',
        errorMessage: magicCheck.errorMessage || 'File is not a valid PDF.',
      };
    }

    // 3. PDF.js inspection for page count and corruption check
    const inspection = await pdfService.inspectPdf(rawFile);
    if (!inspection.isSuccess) {
      return {
        ...printFile,
        fileType: 'pdf',
        processingStatus: 'error',
        errorMessage: inspection.errorMessage || 'Unable to parse PDF pages.',
      };
    }

    // Create safe object URL for preview
    const objectUrl = URL.createObjectURL(rawFile);

    return {
      ...printFile,
      fileType: 'pdf',
      pageCount: inspection.pageCount,
      processingStatus: 'ready',
      objectUrl,
    };
  }, []);

  // Add multiple files
  const addRawFiles = useCallback(
    async (rawFiles: File[]) => {
      if (!rawFiles || rawFiles.length === 0) return;

      const currentCount = draft.files.length;
      const allowedCount = Math.max(0, APP_CONFIG.maxFilesCount - currentCount);

      if (allowedCount <= 0) {
        alert(`Maximum ${APP_CONFIG.maxFilesCount} files allowed per draft.`);
        return;
      }

      const filesToProcess = rawFiles.slice(0, allowedCount);

      // Create placeholder entries with 'validating' status
      const initialPlaceholders: PrintFile[] = filesToProcess.map((f) => ({
        fileId: generateId('file'),
        originalFileName: sanitizeFileName(f.name),
        fileSize: f.size,
        pageCount: 0,
        processingStatus: 'validating',
        printSettings: { ...DEFAULT_PRINT_SETTINGS },
        file: f,
        uploadedAt: new Date().toISOString(),
      }));

      dispatch({ type: 'ADD_FILES', payload: initialPlaceholders });

      // Process each file concurrently without letting one failure break others
      await Promise.all(
        initialPlaceholders.map(async (placeholder, idx) => {
          const rawFile = filesToProcess[idx];
          try {
            const processed = await processRawFile(rawFile);
            dispatch({
              type: 'UPDATE_FILE',
              payload: {
                fileId: placeholder.fileId,
                updates: {
                  originalFileName: processed.originalFileName,
                  pageCount: processed.pageCount,
                  processingStatus: processed.processingStatus,
                  objectUrl: processed.objectUrl,
                  errorMessage: processed.errorMessage,
                },
              },
            });
          } catch (err: unknown) {
            const error = err as { message?: string };
            dispatch({
              type: 'UPDATE_FILE',
              payload: {
                fileId: placeholder.fileId,
                updates: {
                  processingStatus: 'error',
                  errorMessage: error?.message || 'Unexpected error processing file.',
                },
              },
            });
          }
        })
      );
    },
    [draft.files.length, processRawFile]
  );

  // Replace a specific file
  const replaceRawFile = useCallback(
    async (fileId: string, newRawFile: File) => {
      const processed = await processRawFile(newRawFile);
      dispatch({
        type: 'REPLACE_FILE',
        payload: {
          fileId,
          newFile: {
            ...processed,
            fileId, // retain same ID
          },
        },
      });
    },
    [processRawFile]
  );

  const updateFileSettings = useCallback((fileId: string, settings: Partial<PrintSettings>) => {
    dispatch({ type: 'UPDATE_FILE_SETTINGS', payload: { fileId, settings } });
  }, []);

  const updateMultipleFilesSettings = useCallback(
    (fileIds: string[], settings: Partial<PrintSettings>) => {
      dispatch({ type: 'UPDATE_MULTIPLE_FILES_SETTINGS', payload: { fileIds, settings } });
    },
    []
  );

  const removeFile = useCallback((fileId: string) => {
    dispatch({ type: 'REMOVE_FILE', payload: { fileId } });
  }, []);

  const reorderFiles = useCallback((startIndex: number, endIndex: number) => {
    dispatch({ type: 'REORDER_FILES', payload: { startIndex, endIndex } });
  }, []);

  const clearDraft = useCallback(() => {
    storageService.clearDraftMetadata();
    dispatch({ type: 'CLEAR_DRAFT' });
  }, []);

  const setCurrentStep = useCallback((step: WorkflowStep) => {
    dispatch({ type: 'SET_CURRENT_STEP', payload: step });
  }, []);

  const getFileById = useCallback(
    (fileId: string) => {
      return draft.files.find((f) => f.fileId === fileId);
    },
    [draft.files]
  );

  // Live order calculations
  const totals = useMemo(() => calculateDraftTotals(draft.files), [draft.files]);

  // Workflow navigation guards:
  // Must have at least one ready file with positive page count, and no pending validations
  const canProceedToSettings = useMemo(() => {
    return (
      draft.files.length > 0 &&
      draft.files.some((f) => f.processingStatus === 'ready' && f.pageCount > 0) &&
      !draft.files.some((f) => f.processingStatus === 'validating')
    );
  }, [draft.files]);

  const canProceedToReview = useMemo(() => {
    return (
      canProceedToSettings &&
      draft.files.filter((f) => f.processingStatus === 'ready').length > 0
    );
  }, [canProceedToSettings, draft.files]);

  const contextValue = useMemo(
    () => ({
      draft,
      totals,
      canProceedToSettings,
      canProceedToReview,
      addRawFiles,
      updateFileSettings,
      updateMultipleFilesSettings,
      removeFile,
      reorderFiles,
      replaceRawFile,
      clearDraft,
      setCurrentStep,
      getFileById,
    }),
    [
      draft,
      totals,
      canProceedToSettings,
      canProceedToReview,
      addRawFiles,
      updateFileSettings,
      updateMultipleFilesSettings,
      removeFile,
      reorderFiles,
      replaceRawFile,
      clearDraft,
      setCurrentStep,
      getFileById,
    ]
  );

  return <PrintDraftContext.Provider value={contextValue}>{children}</PrintDraftContext.Provider>;
};

export function usePrintDraftContext(): PrintDraftContextValue {
  const context = useContext(PrintDraftContext);
  if (!context) {
    throw new Error('usePrintDraftContext must be used within a PrintDraftProvider');
  }
  return context;
}
