import React from 'react';
import { PaperSize } from '../../types/printSettings';
import { PAPER_SIZE_OPTIONS } from '../../config/printDefaults';

export interface PaperSizeSelectProps {
  value: PaperSize;
  onChange: (size: PaperSize) => void;
  disabled?: boolean;
}

export const PaperSizeSelect: React.FC<PaperSizeSelectProps> = ({
  value,
  onChange,
  disabled = false,
}) => {
  return (
    <div>
      <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-2">
        Paper Size
      </label>
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
        {PAPER_SIZE_OPTIONS.map((opt) => {
          const isSelected = value === opt.value;
          return (
            <button
              key={opt.value}
              type="button"
              disabled={disabled}
              onClick={() => onChange(opt.value)}
              className={`p-3 rounded-xl border text-left transition-all focus:outline-none focus:ring-2 focus:ring-blue-600 ${
                isSelected
                  ? 'border-blue-600 bg-blue-50/50 text-blue-900 shadow-sm ring-1 ring-blue-600'
                  : 'border-slate-200 hover:border-slate-300 bg-white text-slate-700'
              }`}
            >
              <div className="font-bold text-sm text-slate-900">{opt.label}</div>
              <div className="text-[11px] text-slate-500 mt-0.5 leading-tight">{opt.dimensions}</div>
            </button>
          );
        })}
      </div>
    </div>
  );
};
