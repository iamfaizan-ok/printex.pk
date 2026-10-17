import React from 'react';
import { Spinner } from '../ui/Spinner';

export interface PDFLoadingStateProps {
  message?: string;
}

export const PDFLoadingState: React.FC<PDFLoadingStateProps> = ({
  message = 'Loading document preview...',
}) => {
  return (
    <div className="flex flex-col items-center justify-center min-h-[320px] p-8 text-center bg-slate-50/50 rounded-xl border border-slate-200/60">
      <Spinner size="lg" />
      <p className="mt-4 text-sm font-medium text-slate-600">{message}</p>
      <p className="mt-1 text-xs text-slate-400">Rendering high-resolution vector preview...</p>
    </div>
  );
};
