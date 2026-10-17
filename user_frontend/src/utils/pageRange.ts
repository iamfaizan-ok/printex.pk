export interface PageRangeResult {
  isValid: boolean;
  selectedPages: number[];
  count: number;
  errorMessage?: string;
}

/**
 * Parses and validates a page range string (e.g., 'all', '1', '1-5', '1, 3, 5-8')
 * against the document's total page count.
 */
export function parsePageRange(rangeStr: string, totalPages: number): PageRangeResult {
  if (!rangeStr || rangeStr.trim() === '' || rangeStr.trim().toLowerCase() === 'all') {
    if (totalPages <= 0) {
      return { isValid: true, selectedPages: [], count: 0 };
    }
    const allPages = Array.from({ length: totalPages }, (_, i) => i + 1);
    return {
      isValid: true,
      selectedPages: allPages,
      count: totalPages,
    };
  }

  if (totalPages <= 0) {
    return {
      isValid: false,
      selectedPages: [],
      count: 0,
      errorMessage: 'Document page count is unavailable or 0.',
    };
  }

  const clean = rangeStr.trim();
  const segments = clean.split(',').map((s) => s.trim()).filter(Boolean);

  if (segments.length === 0) {
    return {
      isValid: false,
      selectedPages: [],
      count: 0,
      errorMessage: 'Please enter a valid page number or range (e.g., 1-5, 8).',
    };
  }

  const selectedSet = new Set<number>();

  for (const segment of segments) {
    // Check if it's a range like "1-5"
    if (segment.includes('-')) {
      const parts = segment.split('-').map((p) => p.trim());
      if (parts.length !== 2) {
        return {
          isValid: false,
          selectedPages: [],
          count: 0,
          errorMessage: `Invalid range format: "${segment}". Format should be e.g. "1-5".`,
        };
      }

      const start = Number(parts[0]);
      const end = Number(parts[1]);

      if (isNaN(start) || isNaN(end) || !Number.isInteger(start) || !Number.isInteger(end)) {
        return {
          isValid: false,
          selectedPages: [],
          count: 0,
          errorMessage: `Invalid numbers in range: "${segment}".`,
        };
      }

      if (start < 1) {
        return {
          isValid: false,
          selectedPages: [],
          count: 0,
          errorMessage: `Page numbers must start from 1. Found ${start}.`,
        };
      }

      if (start > end) {
        return {
          isValid: false,
          selectedPages: [],
          count: 0,
          errorMessage: `Range start (${start}) cannot be greater than range end (${end}).`,
        };
      }

      if (end > totalPages) {
        return {
          isValid: false,
          selectedPages: [],
          count: 0,
          errorMessage: `Page ${end} is out of bounds. This document has ${totalPages} page${totalPages === 1 ? '' : 's'}.`,
        };
      }

      for (let p = start; p <= end; p++) {
        selectedSet.add(p);
      }
    } else {
      // Single page number
      const pageNum = Number(segment);
      if (isNaN(pageNum) || !Number.isInteger(pageNum)) {
        return {
          isValid: false,
          selectedPages: [],
          count: 0,
          errorMessage: `"${segment}" is not a valid page number.`,
        };
      }

      if (pageNum < 1) {
        return {
          isValid: false,
          selectedPages: [],
          count: 0,
          errorMessage: `Page numbers must start from 1. Found ${pageNum}.`,
        };
      }

      if (pageNum > totalPages) {
        return {
          isValid: false,
          selectedPages: [],
          count: 0,
          errorMessage: `Page ${pageNum} exceeds total document pages (${totalPages}).`,
        };
      }

      selectedSet.add(pageNum);
    }
  }

  const sortedPages = Array.from(selectedSet).sort((a, b) => a - b);

  if (sortedPages.length === 0) {
    return {
      isValid: false,
      selectedPages: [],
      count: 0,
      errorMessage: 'No valid pages selected.',
    };
  }

  return {
    isValid: true,
    selectedPages: sortedPages,
    count: sortedPages.length,
  };
}
