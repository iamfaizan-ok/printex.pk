import { describe, it, expect } from 'vitest';
import {
  calculateFileImpressions,
  calculateDraftTotals,
} from '../src/utils/printCalculations';
import { PrintFile } from '../src/types/printFile';
import { DEFAULT_PRINT_SETTINGS } from '../src/config/printDefaults';

describe('printCalculations utility', () => {
  const createMockFile = (
    id: string,
    pageCount: number,
    copies: number,
    sides: 'single' | 'double' = 'double',
    pageRange: string = 'all'
  ): PrintFile => ({
    fileId: id,
    originalFileName: `doc_${id}.pdf`,
    fileSize: 1024 * 100,
    pageCount,
    processingStatus: 'ready',
    printSettings: {
      ...DEFAULT_PRINT_SETTINGS,
      copies,
      sides,
      pageRange,
    },
    uploadedAt: new Date().toISOString(),
  });

  describe('calculateFileImpressions', () => {
    it('calculates 10 pages x 2 copies = 20 impressions', () => {
      const file = createMockFile('a', 10, 2, 'single', 'all');
      const calc = calculateFileImpressions(file);
      expect(calc.selectedPageCount).toBe(10);
      expect(calc.copies).toBe(2);
      expect(calc.totalPageImpressions).toBe(20);
      expect(calc.estimatedSheets).toBe(20); // 10 sheets per copy for single-sided
    });

    it('calculates duplex sheets correctly (ceil(pages / 2) * copies)', () => {
      // 5 pages double-sided -> ceil(5 / 2) = 3 physical sheets per copy
      const file = createMockFile('b', 5, 3, 'double', 'all');
      const calc = calculateFileImpressions(file);
      expect(calc.selectedPageCount).toBe(5);
      expect(calc.copies).toBe(3);
      expect(calc.totalPageImpressions).toBe(15);
      expect(calc.estimatedSheets).toBe(9); // 3 sheets * 3 copies = 9 sheets
    });

    it('respects custom page ranges', () => {
      // 10 page document, range '1-3, 5' -> 4 pages
      const file = createMockFile('c', 10, 2, 'single', '1-3, 5');
      const calc = calculateFileImpressions(file);
      expect(calc.selectedPageCount).toBe(4);
      expect(calc.copies).toBe(2);
      expect(calc.totalPageImpressions).toBe(8);
      expect(calc.estimatedSheets).toBe(8);
    });

    it('returns zero for files that are not ready or have zero pages', () => {
      const pendingFile: PrintFile = {
        ...createMockFile('d', 0, 1),
        processingStatus: 'validating',
      };
      const calc = calculateFileImpressions(pendingFile);
      expect(calc.totalPageImpressions).toBe(0);
      expect(calc.estimatedSheets).toBe(0);
    });
  });

  describe('calculateDraftTotals', () => {
    it('calculates grand totals correctly matching the prompt scenario (Document A: 20 + Document B: 15 = 35 impressions)', () => {
      const docA = createMockFile('a', 10, 2, 'double'); // 20 impressions, 5 sheets * 2 = 10 sheets
      const docB = createMockFile('b', 5, 3, 'double'); // 15 impressions, 3 sheets * 3 = 9 sheets

      const totals = calculateDraftTotals([docA, docB]);
      expect(totals.totalFiles).toBe(2);
      expect(totals.readyFilesCount).toBe(2);
      expect(totals.totalPageImpressions).toBe(35);
      expect(totals.totalEstimatedSheets).toBe(19);
      expect(totals.hasPendingOrProcessingFiles).toBe(false);
      expect(totals.hasErrors).toBe(false);
    });
  });
});
