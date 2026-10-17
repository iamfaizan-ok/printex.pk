import React from 'react';
import { Trash2 } from 'lucide-react';
import { PrintFile } from '../../types/printFile';
import { UploadedFileCard } from './UploadedFileCard';
import { Button } from '../ui/Button';

export interface FileListProps {
  files: PrintFile[];
  onRemove: (fileId: string) => void;
  onReplace: (fileId: string, newFile: File) => void;
  onMoveUp: (index: number) => void;
  onMoveDown: (index: number) => void;
  onClearAll: () => void;
  onPreview?: (file: PrintFile) => void;
}

export const FileList: React.FC<FileListProps> = ({
  files,
  onRemove,
  onReplace,
  onMoveUp,
  onMoveDown,
  onClearAll,
  onPreview,
}) => {
  if (files.length === 0) return null;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h4 className="text-sm font-semibold text-slate-800 uppercase tracking-wider">
          Selected Documents ({files.length})
        </h4>

        <Button
          type="button"
          variant="ghost"
          size="sm"
          icon={<Trash2 className="w-3.5 h-3.5 text-rose-500" />}
          onClick={() => {
            if (window.confirm('Are you sure you want to remove all files from this draft?')) {
              onClearAll();
            }
          }}
          className="text-xs text-rose-600 hover:text-rose-700 hover:bg-rose-50"
        >
          Clear All
        </Button>
      </div>

      <div className="space-y-2.5">
        {files.map((file, idx) => (
          <UploadedFileCard
            key={file.fileId}
            file={file}
            index={idx}
            totalFiles={files.length}
            onRemove={onRemove}
            onReplace={onReplace}
            onMoveUp={onMoveUp}
            onMoveDown={onMoveDown}
            onPreview={onPreview}
          />
        ))}
      </div>
    </div>
  );
};
