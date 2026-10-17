import React from 'react';
import { Smartphone, Monitor } from 'lucide-react';
import { Orientation } from '../../types/printSettings';
import { ORIENTATION_OPTIONS } from '../../config/printDefaults';

export interface OrientationSelectProps {
  value: Orientation;
  onChange: (orientation: Orientation) => void;
  disabled?: boolean;
}

export const OrientationSelect: React.FC<OrientationSelectProps> = ({
  value,
  onChange,
  disabled = false,
}) => {
  return (
    <div>
      <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-2">
        Orientation
      </label>
      <div className="grid grid-cols-2 gap-2.5">
        {ORIENTATION_OPTIONS.map((opt) => {
          const isSelected = value === opt.value;
          return (
            <button
              key={opt.value}
              type="button"
              disabled={disabled}
              onClick={() => onChange(opt.value)}
              className={`p-3 rounded-xl border text-left flex items-center gap-2.5 transition-all focus:outline-none focus:ring-2 focus:ring-blue-600 ${
                isSelected
                  ? 'border-blue-600 bg-blue-50/50 text-blue-900 shadow-sm ring-1 ring-blue-600'
                  : 'border-slate-200 hover:border-slate-300 bg-white text-slate-700'
              }`}
            >
              <div
                className={`p-1.5 rounded-lg ${
                  isSelected ? 'bg-blue-600 text-white' : 'bg-slate-100 text-slate-600'
                }`}
              >
                {opt.value === 'portrait' ? (
                  <Smartphone className="w-4 h-4" />
                ) : (
                  <Monitor className="w-4 h-4" />
                )}
              </div>
              <span className="font-semibold text-sm text-slate-900">{opt.label}</span>
            </button>
          );
        })}
      </div>
    </div>
  );
};
