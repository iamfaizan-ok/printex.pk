import React from 'react';
import { Plus, Minus } from 'lucide-react';
import { APP_CONFIG } from '../../config/appConfig';

export interface CopiesInputProps {
  value: number;
  onChange: (copies: number) => void;
  min?: number;
  max?: number;
  disabled?: boolean;
}

export const CopiesInput: React.FC<CopiesInputProps> = ({
  value,
  onChange,
  min = APP_CONFIG.minCopiesPerDocument,
  max = APP_CONFIG.maxCopiesPerDocument,
  disabled = false,
}) => {
  const handleDecrement = () => {
    if (value > min) {
      onChange(value - 1);
    }
  };

  const handleIncrement = () => {
    if (value < max) {
      onChange(value + 1);
    }
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const raw = e.target.value;
    if (raw === '') {
      onChange(min);
      return;
    }
    const parsed = parseInt(raw, 10);
    if (!isNaN(parsed)) {
      const clamped = Math.max(min, Math.min(max, parsed));
      onChange(clamped);
    }
  };

  return (
    <div>
      <label htmlFor="copies-input" className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1.5">
        Number of Copies
      </label>
      <div className="flex items-center gap-2">
        <div className="flex items-center border border-slate-300 rounded-lg overflow-hidden bg-white shadow-sm focus-within:ring-2 focus-within:ring-blue-600 focus-within:border-blue-600">
          <button
            type="button"
            onClick={handleDecrement}
            disabled={disabled || value <= min}
            className="p-2.5 text-slate-500 hover:text-slate-800 hover:bg-slate-50 disabled:opacity-30 disabled:cursor-not-allowed focus:outline-none transition-colors"
            title="Decrease copies"
            aria-label="Decrease copies"
          >
            <Minus className="w-3.5 h-3.5" />
          </button>

          <input
            id="copies-input"
            type="number"
            min={min}
            max={max}
            value={value}
            onChange={handleInputChange}
            disabled={disabled}
            className="w-16 text-center text-sm font-semibold text-slate-900 border-x border-slate-200 py-1.5 focus:outline-none [appearance:textfield] [&::-webkit-outer-spin-button]:appearance-none [&::-webkit-inner-spin-button]:appearance-none"
          />

          <button
            type="button"
            onClick={handleIncrement}
            disabled={disabled || value >= max}
            className="p-2.5 text-slate-500 hover:text-slate-800 hover:bg-slate-50 disabled:opacity-30 disabled:cursor-not-allowed focus:outline-none transition-colors"
            title="Increase copies"
            aria-label="Increase copies"
          >
            <Plus className="w-3.5 h-3.5" />
          </button>
        </div>

        <span className="text-xs text-slate-500">
          (Max: {max} copies)
        </span>
      </div>
    </div>
  );
};
