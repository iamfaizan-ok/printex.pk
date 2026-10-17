import React from 'react';
import { Link } from 'react-router-dom';
import { FileText, Edit2 } from 'lucide-react';
import { PrintFile } from '../../types/printFile';
import { calculateFileImpressions } from '../../utils/printCalculations';
import { formatFileSize } from '../../utils/formatFileSize';

export interface OrderFileSummaryProps {
  file: PrintFile;
  index: number;
}

export const OrderFileSummary: React.FC<OrderFileSummaryProps> = ({ file, index }) => {
  const calc = calculateFileImpressions(file);
  const { printSettings } = file;

  return (
    <div className="card-base p-5 bg-white space-y-4">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-slate-100">
        <div className="flex items-start gap-3 min-w-0">
          <div className="w-10 h-10 rounded-xl bg-blue-50 text-blue-600 flex items-center justify-center flex-shrink-0 mt-0.5">
            <FileText className="w-5 h-5" />
          </div>
          <div className="min-w-0">
            <h4 className="text-sm font-bold text-slate-900 truncate max-w-xs sm:max-w-md" title={file.originalFileName}>
              {file.originalFileName}
            </h4>
            <div className="flex items-center gap-2 text-xs text-slate-500 mt-0.5">
              <span>Doc #{index + 1}</span>
              <span>•</span>
              <span>{formatFileSize(file.fileSize)}</span>
              <span>•</span>
              <span>{file.pageCount} total pages</span>
            </div>
          </div>
        </div>

        <Link
          to={`/print-settings?fileId=${file.fileId}`}
          className="inline-flex items-center gap-1.5 text-xs font-semibold text-blue-600 hover:text-blue-700 p-1 rounded focus:outline-none focus:ring-2 focus:ring-blue-600 self-start sm:self-center"
        >
          <Edit2 className="w-3.5 h-3.5" />
          <span>Edit Settings</span>
        </Link>
      </div>

      {/* Settings Tags Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs">
        <div className="p-2.5 rounded-lg bg-slate-50 border border-slate-100">
          <span className="text-slate-400 block text-[10px] uppercase font-semibold">Paper</span>
          <span className="font-semibold text-slate-800">{printSettings.paperSize}</span>
        </div>
        <div className="p-2.5 rounded-lg bg-slate-50 border border-slate-100">
          <span className="text-slate-400 block text-[10px] uppercase font-semibold">Color</span>
          <span className="font-semibold text-slate-800">
            {printSettings.colourMode === 'colour' ? 'Full Colour' : 'Black & White'}
          </span>
        </div>
        <div className="p-2.5 rounded-lg bg-slate-50 border border-slate-100">
          <span className="text-slate-400 block text-[10px] uppercase font-semibold">Sides</span>
          <span className="font-semibold text-slate-800">
            {printSettings.sides === 'double' ? 'Double-Sided' : 'Single-Sided'}
          </span>
        </div>
        <div className="p-2.5 rounded-lg bg-slate-50 border border-slate-100">
          <span className="text-slate-400 block text-[10px] uppercase font-semibold">Orientation</span>
          <span className="font-semibold text-slate-800 capitalize">{printSettings.orientation}</span>
        </div>
      </div>

      {/* Impressions Calculation Row */}
      <div className="bg-blue-50/50 rounded-xl p-3 border border-blue-100 flex flex-wrap items-center justify-between text-xs gap-2">
        <div className="text-slate-600">
          <span className="font-semibold text-slate-900">{calc.selectedPageCount}</span> pages selected
          {printSettings.pageRange !== 'all' ? ` (Range: ${printSettings.pageRange})` : ' (All pages)'}{' '}
          × <span className="font-semibold text-slate-900">{calc.copies}</span> cop{calc.copies === 1 ? 'y' : 'ies'}
        </div>
        <div className="font-bold text-blue-900">
          = {calc.totalPageImpressions} Page Impressions (~{calc.estimatedSheets} sheet{calc.estimatedSheets === 1 ? '' : 's'})
        </div>
      </div>
    </div>
  );
};
