import React from 'react';
import { PrintFile } from '../../types/printFile';
import { PrintSettings } from '../../types/printSettings';
import { CopiesInput } from './CopiesInput';
import { PaperSizeSelect } from './PaperSizeSelect';
import { ColourModeSelect } from './ColourModeSelect';
import { OrientationSelect } from './OrientationSelect';
import { SidesSelect } from './SidesSelect';
import { PageRangeInput } from './PageRangeInput';
import { calculateFileImpressions } from '../../utils/printCalculations';

export interface PrintSettingsFormProps {
  file: PrintFile;
  onUpdateSettings: (settings: Partial<PrintSettings>) => void;
  disabled?: boolean;
}

export const PrintSettingsForm: React.FC<PrintSettingsFormProps> = ({
  file,
  onUpdateSettings,
  disabled = false,
}) => {
  const { printSettings, pageCount } = file;
  const impressionsSummary = calculateFileImpressions(file);

  return (
    <div className="space-y-6 bg-white p-6 rounded-2xl border border-slate-200/80 shadow-subtle">
      {/* Document Header */}
      <div className="pb-4 border-b border-slate-100 flex flex-wrap items-center justify-between gap-2">
        <div>
          <h3 className="text-base font-bold text-slate-900 truncate max-w-md" title={file.originalFileName}>
            {file.originalFileName}
          </h3>
          <p className="text-xs text-slate-500 mt-0.5">
            Configure independent print preferences for this document.
          </p>
        </div>

        {/* Live File Calculation Pill */}
        <div className="flex items-center gap-2 bg-blue-50/80 border border-blue-200/60 px-3 py-1.5 rounded-xl text-xs text-blue-900">
          <span className="font-semibold">{impressionsSummary.totalPageImpressions} impressions</span>
          <span className="text-blue-300">•</span>
          <span>~{impressionsSummary.estimatedSheets} sheet{impressionsSummary.estimatedSheets === 1 ? '' : 's'}</span>
        </div>
      </div>

      {/* Copies */}
      <CopiesInput
        value={printSettings.copies}
        onChange={(copies) => onUpdateSettings({ copies })}
        disabled={disabled}
      />

      {/* Paper Size */}
      <PaperSizeSelect
        value={printSettings.paperSize}
        onChange={(paperSize) => onUpdateSettings({ paperSize })}
        disabled={disabled}
      />

      {/* Colour Mode */}
      <ColourModeSelect
        value={printSettings.colourMode}
        onChange={(colourMode) => onUpdateSettings({ colourMode })}
        disabled={disabled}
      />

      {/* Sides & Duplex */}
      <SidesSelect
        value={printSettings.sides}
        onChange={(sides) => onUpdateSettings({ sides })}
        disabled={disabled}
      />

      {/* Orientation */}
      <OrientationSelect
        value={printSettings.orientation}
        onChange={(orientation) => onUpdateSettings({ orientation })}
        disabled={disabled}
      />

      {/* Page Range */}
      <PageRangeInput
        value={printSettings.pageRange}
        totalPages={pageCount}
        onChange={(pageRange) => onUpdateSettings({ pageRange })}
        disabled={disabled}
      />

      <div className="text-[11px] text-slate-400 border-t border-slate-100 pt-3">
        * Preferences are applied per file. Changing options here does not alter other documents in your order.
      </div>
    </div>
  );
};
