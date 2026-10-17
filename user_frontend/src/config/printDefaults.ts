import { PrintSettings, PaperSize, ColourMode, Orientation, PrintSides } from '../types/printSettings';

export const DEFAULT_PRINT_SETTINGS: Readonly<PrintSettings> = {
  copies: 1,
  paperSize: 'A4',
  colourMode: 'bw',
  orientation: 'portrait',
  sides: 'double',
  pageRange: 'all',
};

export const PAPER_SIZE_OPTIONS: { value: PaperSize; label: string; dimensions: string }[] = [
  { value: 'A4', label: 'A4', dimensions: '210 × 297 mm (Standard)' },
  { value: 'A3', label: 'A3', dimensions: '297 × 420 mm (Large)' },
  { value: 'Letter', label: 'Letter', dimensions: '8.5 × 11 in (US Standard)' },
  { value: 'Legal', label: 'Legal', dimensions: '8.5 × 14 in' },
];

export const COLOUR_MODE_OPTIONS: { value: ColourMode; label: string; description: string }[] = [
  { value: 'bw', label: 'Black & White', description: 'Standard grayscale for text & essays' },
  { value: 'colour', label: 'Full Colour', description: 'Vibrant CMYK for charts, photos & presentations' },
];

export const ORIENTATION_OPTIONS: { value: Orientation; label: string }[] = [
  { value: 'portrait', label: 'Portrait' },
  { value: 'landscape', label: 'Landscape' },
];

export const SIDES_OPTIONS: { value: PrintSides; label: string; description: string }[] = [
  { value: 'double', label: 'Double-Sided (Duplex)', description: 'Prints on both sides (Eco-friendly)' },
  { value: 'single', label: 'Single-Sided', description: 'Prints on one side of each sheet' },
];
