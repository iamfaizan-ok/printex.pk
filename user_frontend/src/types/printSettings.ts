export type PaperSize = 'A4' | 'A3' | 'Letter' | 'Legal';
export type ColourMode = 'colour' | 'bw';
export type Orientation = 'portrait' | 'landscape';
export type PrintSides = 'single' | 'double';

export interface PrintSettings {
  copies: number;
  paperSize: PaperSize;
  colourMode: ColourMode;
  orientation: Orientation;
  sides: PrintSides;
  pageRange: string; // 'all' or specific ranges like '1-5, 8'
}

export interface PrintCalculationSummary {
  originalPageCount: number;
  selectedPageCount: number;
  copies: number;
  totalPageImpressions: number;
  estimatedSheets: number; // for physical paper count based on single or double sided
}
