import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowRight, FileText } from 'lucide-react';
import { usePrintDraft } from '../hooks/usePrintDraft';
import { FileDropzone } from '../components/upload/FileDropzone';
import { FileList } from '../components/upload/FileList';
import { Button } from '../components/ui/Button';
import { Modal } from '../components/ui/Modal';
import { PDFPreview } from '../components/pdf/PDFPreview';
import { PrintFile } from '../types/printFile';
import { Alert } from '../components/ui/Alert';

export const UploadPage: React.FC = () => {
  const navigate = useNavigate();
  const {
    draft,
    addRawFiles,
    removeFile,
    reorderFiles,
    replaceRawFile,
    clearDraft,
    canProceedToSettings,
  } = usePrintDraft();

  const [previewModalFile, setPreviewModalFile] = useState<PrintFile | null>(null);

  const hasFiles = draft.files.length > 0;
  const hasErrors = draft.files.some((f) => f.processingStatus === 'error');
  const isValidatingAny = draft.files.some((f) => f.processingStatus === 'validating');
  const validFilesCount = draft.files.filter((f) => f.processingStatus === 'ready').length;

  const handleContinue = () => {
    if (canProceedToSettings) {
      navigate('/print-settings');
    }
  };

  return (
    <div className="flex-1 py-8 sm:py-12">
      <div className="max-w-4xl mx-auto px-4 sm:px-6">
        {/* Page Title & Intro */}
        <div className="mb-8 text-center sm:text-left">
          <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight">
            Step 1: Upload Your Documents
          </h1>
          <p className="text-sm text-slate-500 mt-1">
            Upload PDF files to print. You can configure individual print settings on the next step.
          </p>
        </div>

        {/* Upload Dropzone */}
        <div className="mb-8">
          <FileDropzone
            onFilesDropped={addRawFiles}
            currentCount={draft.files.length}
            disabled={isValidatingAny}
          />
        </div>

        {/* Global Warnings if any files failed */}
        {hasErrors && (
          <div className="mb-6">
            <Alert type="warning" title="Some files require attention">
              One or more documents could not be verified. You can replace or remove the affected files below. Valid documents can still be printed.
            </Alert>
          </div>
        )}

        {/* Uploaded File List */}
        {hasFiles && (
          <div className="mb-8">
            <FileList
              files={draft.files}
              onRemove={removeFile}
              onReplace={replaceRawFile}
              onMoveUp={(idx) => reorderFiles(idx, idx - 1)}
              onMoveDown={(idx) => reorderFiles(idx, idx + 1)}
              onClearAll={clearDraft}
              onPreview={(file) => setPreviewModalFile(file)}
            />
          </div>
        )}

        {/* Bottom Actions Bar */}
        {hasFiles && (
          <div className="sticky bottom-4 z-20 bg-white/95 backdrop-blur-md rounded-2xl border border-slate-200/90 p-4 shadow-elevated flex flex-col sm:flex-row items-center justify-between gap-4 mt-8">
            <div className="flex items-center gap-2 text-xs text-slate-600">
              <FileText className="w-4 h-4 text-blue-600" />
              <span>
                <strong>{validFilesCount}</strong> valid document{validFilesCount === 1 ? '' : 's'} ready
                {hasErrors && ' (issues found in remaining files)'}
              </span>
            </div>

            <div className="flex items-center gap-3 w-full sm:w-auto justify-end">
              <Button
                type="button"
                variant="primary"
                size="md"
                disabled={!canProceedToSettings}
                onClick={handleContinue}
                icon={<ArrowRight className="w-4 h-4" />}
                className="w-full sm:w-auto"
              >
                {isValidatingAny ? 'Verifying Files...' : 'Continue to Print Settings'}
              </Button>
            </div>
          </div>
        )}

        {/* Quick PDF Preview Modal */}
        {previewModalFile && (
          <Modal
            isOpen={Boolean(previewModalFile)}
            onClose={() => setPreviewModalFile(null)}
            title={`Preview: ${previewModalFile.originalFileName}`}
            description="Client-side vector rendering with page controls."
            maxWidth="2xl"
          >
            <div className="mt-2">
              <PDFPreview file={previewModalFile} />
            </div>
            <div className="mt-4 flex justify-end">
              <Button variant="secondary" size="sm" onClick={() => setPreviewModalFile(null)}>
                Close Preview
              </Button>
            </div>
          </Modal>
        )}
      </div>
    </div>
  );
};
