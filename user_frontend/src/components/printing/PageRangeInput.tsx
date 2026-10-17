import React, { useState, useEffect } from 'react';
import { parsePageRange } from '../../utils/pageRange';
import { Input } from '../ui/Input';

export interface PageRangeInputProps {
  value: string;
  totalPages: number;
  onChange: (range: string) => void;
  disabled?: boolean;
}

export const PageRangeInput: React.FC<PageRangeInputProps> = ({
  value,
  totalPages,
  onChange,
  disabled = false,
}) => {
  const isCustomMode = value !== 'all';
  const [customRangeText, setCustomRangeText] = useState<string>(
    value === 'all' ? '' : value
  );

  useEffect(() => {
    if (value !== 'all') {
      setCustomRangeText(value);
    }
  }, [value]);

  const rangeValidation = parsePageRange(value, totalPages);

  const handleModeChange = (mode: 'all' | 'custom') => {
    if (mode === 'all') {
      onChange('all');
      setCustomRangeText('');
    } else {
      const initialCustom = customRangeText.trim() || `1-${Math.min(totalPages, 5)}`;
      onChange(initialCustom);
      setCustomRangeText(initialCustom);
    }
  };

  const handleCustomTextChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const text = e.target.value;
    setCustomRangeText(text);
    onChange(text);
  };

  return (
    <div>
      <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-2">
        Pages to Print
      </label>

      {/* Mode Buttons */}
      <div className="grid grid-cols-2 gap-2 mb-3">
        <button
          type="button"
          disabled={disabled}
          onClick={() => handleModeChange('all')}
          className={`py-2 px-3 rounded-lg text-xs font-semibold border transition-all focus:outline-none focus:ring-2 focus:ring-blue-600 ${
            !isCustomMode
              ? 'border-blue-600 bg-blue-50 text-blue-900 ring-1 ring-blue-600'
              : 'border-slate-200 hover:border-slate-300 bg-white text-slate-700'
          }`}
        >
          All Pages ({totalPages} total)
        </button>

        <button
          type="button"
          disabled={disabled}
          onClick={() => handleModeChange('custom')}
          className={`py-2 px-3 rounded-lg text-xs font-semibold border transition-all focus:outline-none focus:ring-2 focus:ring-blue-600 ${
            isCustomMode
              ? 'border-blue-600 bg-blue-50 text-blue-900 ring-1 ring-blue-600'
              : 'border-slate-200 hover:border-slate-300 bg-white text-slate-700'
          }`}
        >
          Custom Range
        </button>
      </div>

      {/* Custom Range Text Input */}
      {isCustomMode && (
        <div className="space-y-1.5 animate-in fade-in">
          <Input
            placeholder="e.g. 1-3, 5, 8-10"
            value={customRangeText}
            onChange={handleCustomTextChange}
            error={!rangeValidation.isValid ? rangeValidation.errorMessage : undefined}
            disabled={disabled}
            helperText="Enter individual pages and/or comma-separated ranges."
          />

          {rangeValidation.isValid && (
            <div className="text-xs text-blue-600 font-medium">
              ✓ {rangeValidation.count} of {totalPages} pages selected
            </div>
          )}
        </div>
      )}
    </div>
  );
};
