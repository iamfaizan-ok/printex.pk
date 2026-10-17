import React from 'react';
import { Copy, Layers } from 'lucide-react';
import { PrintSides } from '../../types/printSettings';
import { SIDES_OPTIONS } from '../../config/printDefaults';

export interface SidesSelectProps {
  value: PrintSides;
  onChange: (sides: PrintSides) => void;
  disabled?: boolean;
}

export const SidesSelect: React.FC<SidesSelectProps> = ({
  value,
  onChange,
  disabled = false,
}) => {
  return (
    <div>
      <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-2">
        Sides & Duplex
      </label>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
        {SIDES_OPTIONS.map((opt) => {
          const isSelected = value === opt.value;
          return (
            <button
              key={opt.value}
              type="button"
              disabled={disabled}
              onClick={() => onChange(opt.value)}
              className={`p-3.5 rounded-xl border text-left flex items-start gap-3 transition-all focus:outline-none focus:ring-2 focus:ring-blue-600 ${
                isSelected
                  ? 'border-blue-600 bg-blue-50/50 text-blue-900 shadow-sm ring-1 ring-blue-600'
                  : 'border-slate-200 hover:border-slate-300 bg-white text-slate-700'
              }`}
            >
              <div
                className={`p-2 rounded-lg mt-0.5 ${
                  isSelected ? 'bg-blue-600 text-white' : 'bg-slate-100 text-slate-600'
                }`}
              >
                {opt.value === 'double' ? (
                  <Layers className="w-4 h-4" />
                ) : (
                  <Copy className="w-4 h-4" />
                )}
              </div>
              <div className="flex-1 min-w-0">
                <div className="font-semibold text-sm text-slate-900">{opt.label}</div>
                <div className="text-xs text-slate-500 mt-0.5 leading-relaxed">{opt.description}</div>
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
};
