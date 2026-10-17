import { PrintFile } from '../types/printFile';
import { PrintCalculationSummary } from '../types/printSettings';
import { parsePageRange } from './pageRange';

/**
 * Calculates page impressions and physical sheet estimates for a single PrintFile.
 */
export function calculateFileImpressions(file: PrintFile): PrintCalculationSummary {
  const pageCount = file.pageCount || 0;
  const copies = Math.max(1, Math.floor(file.printSettings.copies || 1));

  if (pageCount <= 0 || file.processingStatus !== 'ready') {
    return {
      originalPageCount: 0,
      selectedPageCount: 0,
      copies,
      totalPageImpressions: 0,
      estimatedSheets: 0,
    };
  }

  const rangeResult = parsePageRange(file.printSettings.pageRange, pageCount);
  const selectedPageCount = rangeResult.isValid ? rangeResult.count : 0;
  const totalPageImpressions = selectedPageCount * copies;

  // Sheet calculation:
  // If double-sided (duplex), each sheet holds 2 page impressions (rounded up).
  // If single-sided, each page impression takes 1 physical sheet.
  const isDoubleSided = file.printSettings.sides === 'double';
  const sheetsPerCopy = isDoubleSided
    ? Math.ceil(selectedPageCount / 2)
    : selectedPageCount;
  const estimatedSheets = sheetsPerCopy * copies;

  return {
    originalPageCount: pageCount,
    selectedPageCount,
    copies,
    totalPageImpressions,
    estimatedSheets,
  };
}

export interface OverallOrderCalculation {
  totalFiles: number;
  readyFilesCount: number;
  totalPageImpressions: number;
  totalEstimatedSheets: number;
  hasPendingOrProcessingFiles: boolean;
  hasErrors: boolean;
}

/**
 * Calculates total impressions and sheets for the entire draft.
 */
export function calculateDraftTotals(files: PrintFile[]): OverallOrderCalculation {
  let totalPageImpressions = 0;
  let totalEstimatedSheets = 0;
  let readyFilesCount = 0;
  let hasPendingOrProcessingFiles = false;
  let hasErrors = false;

  for (const file of files) {
    if (file.processingStatus === 'ready') {
      readyFilesCount++;
      const fileSummary = calculateFileImpressions(file);
      totalPageImpressions += fileSummary.totalPageImpressions;
      totalEstimatedSheets += fileSummary.estimatedSheets;
    } else if (file.processingStatus === 'error') {
      hasErrors = true;
    } else {
      hasPendingOrProcessingFiles = true;
    }
  }

  return {
    totalFiles: files.length,
    readyFilesCount,
    totalPageImpressions,
    totalEstimatedSheets,
    hasPendingOrProcessingFiles,
    hasErrors,
  };
}
