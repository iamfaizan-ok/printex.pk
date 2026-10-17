import React from 'react';
import { AlertCircle } from 'lucide-react';

export interface FileValidationMessageProps {
  message?: string;
  className?: string;
}

export const FileValidationMessage: React.FC<FileValidationMessageProps> = ({ message, className = '' }) => {
  if (!message) return null;

  return (
    <div className={`flex items-start gap-1.5 text-xs text-rose-600 bg-rose-50/80 p-2 rounded-lg border border-rose-200/60 ${className}`} role="alert">
      <AlertCircle className="w-3.5 h-3.5 flex-shrink-0 mt-0.5" />
      <span>{message}</span>
    </div>
  );
};
