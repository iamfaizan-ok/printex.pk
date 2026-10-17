import React, { useState, useRef } from 'react';
import { UploadCloud, FileCheck, ShieldAlert } from 'lucide-react';
import { FilePicker } from './FilePicker';
import { Button } from '../ui/Button';
import { APP_CONFIG } from '../../config/appConfig';
import { formatFileSize } from '../../utils/formatFileSize';

export interface FileDropzoneProps {
  onFilesDropped: (files: File[]) => void;
  disabled?: boolean;
  currentCount?: number;
}

export const FileDropzone: React.FC<FileDropzoneProps> = ({
  onFilesDropped,
  disabled = false,
  currentCount = 0,
}) => {
  const [isDragging, setIsDragging] = useState(false);
  const dropzoneRef = useRef<HTMLDivElement>(null);

  const maxFiles = APP_CONFIG.maxFilesCount;
  const maxBytes = APP_CONFIG.maxFileSizeBytes;
  const isAtLimit = currentCount >= maxFiles;

  const handleDragEnter = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (disabled || isAtLimit) return;
    setIsDragging(true);
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (disabled || isAtLimit) return;
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.currentTarget.contains(e.relatedTarget as Node)) return;
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);

    if (disabled || isAtLimit) return;

    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      const droppedFiles = Array.from(e.dataTransfer.files);
      onFilesDropped(droppedFiles);
    }
  };

  return (
    <FilePicker onFilesSelected={onFilesDropped} disabled={disabled || isAtLimit}>
      {(openPicker) => (
        <div
          ref={dropzoneRef}
          onDragEnter={handleDragEnter}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          onClick={openPicker}
          role="button"
          tabIndex={disabled || isAtLimit ? -1 : 0}
          onKeyDown={(e) => {
            if (e.key === 'Enter' || e.key === ' ') {
              e.preventDefault();
              openPicker();
            }
          }}
          className={`relative border-2 border-dashed rounded-2xl p-8 sm:p-12 text-center transition-all cursor-pointer select-none focus:outline-none focus:ring-2 focus:ring-blue-600 focus:ring-offset-2 ${
            isDragging
              ? 'border-blue-600 bg-blue-50/60 scale-[1.008]'
              : isAtLimit
              ? 'border-slate-200 bg-slate-50 cursor-not-allowed opacity-75'
              : 'border-slate-300 hover:border-blue-500 bg-white hover:bg-slate-50/50 shadow-subtle'
          }`}
        >
          <div className="flex flex-col items-center justify-center max-w-md mx-auto">
            {isAtLimit ? (
              <div className="w-16 h-16 rounded-2xl bg-amber-50 text-amber-600 flex items-center justify-center mb-4">
                <ShieldAlert className="w-8 h-8" />
              </div>
            ) : isDragging ? (
              <div className="w-16 h-16 rounded-2xl bg-blue-100 text-blue-600 flex items-center justify-center mb-4 animate-bounce">
                <FileCheck className="w-8 h-8" />
              </div>
            ) : (
              <div className="w-16 h-16 rounded-2xl bg-blue-50 text-blue-600 flex items-center justify-center mb-4 group-hover:scale-110 transition-transform">
                <UploadCloud className="w-8 h-8" />
              </div>
            )}

            <h3 className="text-lg font-bold text-slate-900 mb-1">
              {isAtLimit
                ? `Draft limit reached (${maxFiles} files)`
                : isDragging
                ? 'Drop your documents or images here'
                : 'Click or drag & drop PDF files or images'}
            </h3>

            <p className="text-sm text-slate-500 mb-5 leading-relaxed">
              {isAtLimit
                ? 'Please remove or replace a document below to upload more.'
                : 'Upload one or multiple PDFs or photos to configure customized print options.'}
            </p>

            {!isAtLimit && (
              <Button
                type="button"
                variant="primary"
                onClick={(e) => {
                  e.stopPropagation();
                  openPicker();
                }}
              >
                Browse Files
              </Button>
            )}

            <div className="flex flex-wrap items-center justify-center gap-x-4 gap-y-1 mt-6 text-xs text-slate-400 border-t border-slate-100 pt-4 w-full">
              <span>PDF, JPG, PNG, WEBP formats</span>
              <span>•</span>
              <span>Max {formatFileSize(maxBytes)} per file</span>
              <span>•</span>
              <span>Up to {maxFiles} files ({currentCount}/{maxFiles} selected)</span>
            </div>
          </div>
        </div>
      )}
    </FilePicker>
  );
};
