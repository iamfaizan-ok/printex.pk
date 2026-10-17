import {
  FileText,
  Image as ImageIcon,
  Trash2,
  RefreshCw,
  ArrowUp,
  ArrowDown,
  Eye,
  CheckCircle2,
  AlertTriangle,
} from 'lucide-react';
import { PrintFile } from '../../types/printFile';
import { formatFileSize } from '../../utils/formatFileSize';
import { FilePicker } from './FilePicker';
import { FileValidationMessage } from './FileValidationMessage';
import { Spinner } from '../ui/Spinner';

export interface UploadedFileCardProps {
  file: PrintFile;
  index: number;
  totalFiles: number;
  onRemove: (fileId: string) => void;
  onReplace: (fileId: string, newFile: File) => void;
  onMoveUp: (index: number) => void;
  onMoveDown: (index: number) => void;
  onPreview?: (file: PrintFile) => void;
}

export const UploadedFileCard: React.FC<UploadedFileCardProps> = ({
  file,
  index,
  totalFiles,
  onRemove,
  onReplace,
  onMoveUp,
  onMoveDown,
  onPreview,
}) => {
  const isReady = file.processingStatus === 'ready';
  const isValidating = file.processingStatus === 'validating';
  const isError = file.processingStatus === 'error';
  const isImage = file.fileType === 'image' || Boolean(file.originalFileName.match(/\.(png|jpe?g|webp|svg|bmp)$/i));

  return (
    <div
      className={`card-base p-4 transition-all ${
        isError ? 'border-rose-300 bg-rose-50/20' : 'bg-white'
      }`}
    >
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        {/* Left: Icon and file info */}
        <div className="flex items-start gap-3.5 min-w-0 flex-1">
          {isImage && file.objectUrl && !isError ? (
            <img
              src={file.objectUrl}
              alt=""
              className="w-11 h-11 rounded-xl object-cover border border-slate-200 flex-shrink-0 mt-0.5 shadow-sm"
            />
          ) : (
            <div
              className={`w-11 h-11 rounded-xl flex items-center justify-center flex-shrink-0 mt-0.5 ${
                isError
                  ? 'bg-rose-100 text-rose-600'
                  : isReady
                  ? 'bg-blue-50 text-blue-600'
                  : 'bg-slate-100 text-slate-500'
              }`}
            >
              {isImage ? <ImageIcon className="w-5 h-5" /> : <FileText className="w-5 h-5" />}
            </div>
          )}

          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2 flex-wrap">
              <h4
                className="text-sm font-semibold text-slate-900 truncate max-w-xs sm:max-w-md"
                title={file.originalFileName}
              >
                {file.originalFileName}
              </h4>

              {/* Status Badges */}
              {isReady && (
                <span className="badge-green gap-1">
                  <CheckCircle2 className="w-3 h-3 text-emerald-600" />
                  {file.pageCount} page{file.pageCount === 1 ? '' : 's'}
                </span>
              )}

              {isValidating && (
                <span className="badge-blue gap-1">
                  <Spinner size="sm" />
                  Verifying...
                </span>
              )}

              {isError && (
                <span className="badge-red gap-1">
                  <AlertTriangle className="w-3 h-3 text-rose-600" />
                  Verification Failed
                </span>
              )}
            </div>

            <div className="flex items-center gap-3 mt-1 text-xs text-slate-500">
              <span>{formatFileSize(file.fileSize)}</span>
              <span>•</span>
              <span>Doc #{index + 1}</span>
            </div>

            {/* Error Message if any */}
            {isError && file.errorMessage && (
              <div className="mt-2.5">
                <FileValidationMessage message={file.errorMessage} />
              </div>
            )}
          </div>
        </div>

        {/* Right: Actions */}
        <div className="flex items-center gap-1.5 self-end sm:self-center border-t sm:border-t-0 pt-2 sm:pt-0 w-full sm:w-auto justify-end">
          {/* Preview button */}
          {isReady && onPreview && (
            <button
              type="button"
              onClick={() => onPreview(file)}
              className="p-1.5 rounded-lg text-slate-500 hover:text-blue-600 hover:bg-blue-50 focus:outline-none focus:ring-2 focus:ring-blue-600 transition-colors"
              title="Preview PDF"
              aria-label={`Preview ${file.originalFileName}`}
            >
              <Eye className="w-4 h-4" />
            </button>
          )}

          {/* Reorder Up */}
          <button
            type="button"
            disabled={index === 0}
            onClick={() => onMoveUp(index)}
            className="p-1.5 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-100 disabled:opacity-25 disabled:cursor-not-allowed focus:outline-none focus:ring-2 focus:ring-slate-400 transition-colors"
            title="Move document up"
            aria-label="Move document up"
          >
            <ArrowUp className="w-4 h-4" />
          </button>

          {/* Reorder Down */}
          <button
            type="button"
            disabled={index === totalFiles - 1}
            onClick={() => onMoveDown(index)}
            className="p-1.5 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-100 disabled:opacity-25 disabled:cursor-not-allowed focus:outline-none focus:ring-2 focus:ring-slate-400 transition-colors"
            title="Move document down"
            aria-label="Move document down"
          >
            <ArrowDown className="w-4 h-4" />
          </button>

          {/* Replace file */}
          <FilePicker
            multiple={false}
            onFilesSelected={(files) => {
              if (files[0]) onReplace(file.fileId, files[0]);
            }}
          >
            {(openReplacePicker) => (
              <button
                type="button"
                onClick={openReplacePicker}
                className="p-1.5 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-100 focus:outline-none focus:ring-2 focus:ring-slate-400 transition-colors"
                title="Replace with another PDF"
                aria-label={`Replace ${file.originalFileName}`}
              >
                <RefreshCw className="w-4 h-4" />
              </button>
            )}
          </FilePicker>

          {/* Remove file */}
          <button
            type="button"
            onClick={() => onRemove(file.fileId)}
            className="p-1.5 rounded-lg text-slate-400 hover:text-rose-600 hover:bg-rose-50 focus:outline-none focus:ring-2 focus:ring-rose-500 transition-colors"
            title="Remove document"
            aria-label={`Remove ${file.originalFileName}`}
          >
            <Trash2 className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
};
