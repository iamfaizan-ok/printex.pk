import React, { useState, useEffect } from 'react';
import { useNavigate, useSearchParams, Link } from 'react-router-dom';
import { ArrowRight, ArrowLeft, FileText } from 'lucide-react';
import { usePrintDraft } from '../hooks/usePrintDraft';
import { PrintSettingsForm } from '../components/printing/PrintSettingsForm';
import { PDFPreview } from '../components/pdf/PDFPreview';
import { EmptyOrderState } from '../components/order/EmptyOrderState';
import { Button } from '../components/ui/Button';

export const PrintSettingsPage: React.FC = () => {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const { draft, updateFileSettings, totals, canProceedToReview } = usePrintDraft();

  const validFiles = draft.files.filter((f) => f.processingStatus === 'ready');

  // Active file selection state
  const paramFileId = searchParams.get('fileId');
  const [activeFileId, setActiveFileId] = useState<string>(
    paramFileId && validFiles.some((f) => f.fileId === paramFileId)
      ? paramFileId
      : validFiles[0]?.fileId || ''
  );

  useEffect(() => {
    if (paramFileId && validFiles.some((f) => f.fileId === paramFileId)) {
      setActiveFileId(paramFileId);
    } else if (validFiles.length > 0 && (!activeFileId || !validFiles.some((f) => f.fileId === activeFileId))) {
      setActiveFileId(validFiles[0].fileId);
    }
  }, [paramFileId, validFiles, activeFileId]);

  const handleSelectFile = (fileId: string) => {
    setActiveFileId(fileId);
    setSearchParams({ fileId });
  };

  if (validFiles.length === 0) {
    return (
      <div className="flex-1 py-12 px-4 sm:px-6">
        <EmptyOrderState
          title="No verified documents ready for print settings"
          description="Please upload valid PDF files first so you can configure print preferences."
          actionText="Go to Upload Page"
          actionHref="/upload"
        />
      </div>
    );
  }

  const activeFile = validFiles.find((f) => f.fileId === activeFileId) || validFiles[0];

  return (
    <div className="flex-1 py-8 sm:py-12">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="mb-6 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight">
              Step 2: Configure Print Preferences
            </h1>
            <p className="text-sm text-slate-500 mt-1">
              Customize paper size, colour mode, duplex, and copies for each document independently.
            </p>
          </div>

          <div className="flex items-center gap-2 self-start sm:self-center">
            <Link to="/upload">
              <Button variant="outline" size="sm" icon={<ArrowLeft className="w-4 h-4" />}>
                Upload More Files
              </Button>
            </Link>
          </div>
        </div>

        {/* Document Selection Tabs (if multiple files) */}
        {validFiles.length > 1 && (
          <div className="mb-6 flex items-center gap-2 overflow-x-auto pb-2 scrollbar-thin">
            {validFiles.map((file, idx) => {
              const isSelected = file.fileId === activeFile.fileId;
              return (
                <button
                  key={file.fileId}
                  type="button"
                  onClick={() => handleSelectFile(file.fileId)}
                  className={`flex items-center gap-2 px-3.5 py-2 rounded-xl text-xs font-semibold whitespace-nowrap transition-all border focus:outline-none focus:ring-2 focus:ring-blue-600 ${
                    isSelected
                      ? 'bg-blue-600 text-white border-blue-600 shadow-sm'
                      : 'bg-white text-slate-700 border-slate-200 hover:border-slate-300 hover:bg-slate-50'
                  }`}
                >
                  <FileText className="w-3.5 h-3.5 flex-shrink-0" />
                  <span className="truncate max-w-[150px]">
                    {idx + 1}. {file.originalFileName}
                  </span>
                  <span
                    className={`px-1.5 py-0.5 rounded text-[10px] ${
                      isSelected ? 'bg-blue-700 text-blue-100' : 'bg-slate-100 text-slate-600'
                    }`}
                  >
                    {file.pageCount}p
                  </span>
                </button>
              );
            })}
          </div>
        )}

        {/* Two-Column Workspace: Left = Form, Right = Live Preview */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start mb-12">
          {/* Settings Form Column */}
          <div className="lg:col-span-7 space-y-6">
            <PrintSettingsForm
              file={activeFile}
              onUpdateSettings={(newSettings) =>
                updateFileSettings(activeFile.fileId, newSettings)
              }
            />
          </div>

          {/* PDF Preview Column */}
          <div className="lg:col-span-5 bg-white p-5 rounded-2xl border border-slate-200/80 shadow-subtle sticky top-20">
            <div className="flex items-center justify-between pb-3 mb-3 border-b border-slate-100">
              <div>
                <h3 className="text-sm font-bold text-slate-900">Document Preview</h3>
                <p className="text-[11px] text-slate-500 truncate max-w-[240px]">
                  {activeFile.originalFileName}
                </p>
              </div>
              <span className="badge-blue text-[11px]">
                {activeFile.pageCount} Total Pages
              </span>
            </div>

            <PDFPreview file={activeFile} />
          </div>
        </div>

        {/* Sticky Order Action Bar */}
        <div className="sticky bottom-4 z-20 bg-white/95 backdrop-blur-md rounded-2xl border border-slate-200/90 p-4 shadow-elevated flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-4 text-xs">
            <div>
              <span className="text-slate-400 block text-[10px] uppercase font-semibold">Total Documents</span>
              <span className="font-bold text-slate-800">{totals.readyFilesCount}</span>
            </div>
            <div className="h-6 w-px bg-slate-200" />
            <div>
              <span className="text-slate-400 block text-[10px] uppercase font-semibold">Requested Impressions</span>
              <span className="font-bold text-blue-600 text-sm">{totals.totalPageImpressions}</span>
            </div>
            <div className="h-6 w-px bg-slate-200" />
            <div>
              <span className="text-slate-400 block text-[10px] uppercase font-semibold">Estimated Paper</span>
              <span className="font-bold text-slate-800">~{totals.totalEstimatedSheets} sheets</span>
            </div>
          </div>

          <div className="flex items-center gap-3 w-full sm:w-auto justify-end">
            <Link to="/upload">
              <Button variant="ghost" size="md">
                Back to Upload
              </Button>
            </Link>

            <Button
              type="button"
              variant="primary"
              size="md"
              disabled={!canProceedToReview}
              onClick={() => navigate('/review-order')}
              icon={<ArrowRight className="w-4 h-4" />}
            >
              Review Order
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
};
