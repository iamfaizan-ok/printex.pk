import React, { useState, useEffect } from 'react';
import { useNavigate, useSearchParams, Link } from 'react-router-dom';
import { ArrowRight, ArrowLeft, CheckSquare, Square, Sparkles, Check, ChevronLeft, ChevronRight, Layers } from 'lucide-react';
import { usePrintDraft } from '../hooks/usePrintDraft';
import { PrintSettingsForm } from '../components/printing/PrintSettingsForm';
import { PDFPreview } from '../components/pdf/PDFPreview';
import { EmptyOrderState } from '../components/order/EmptyOrderState';
import { Button } from '../components/ui/Button';

export const PrintSettingsPage: React.FC = () => {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const { draft, updateFileSettings, updateMultipleFilesSettings, totals, canProceedToReview } = usePrintDraft();

  const validFiles = draft.files.filter((f) => f.processingStatus === 'ready');

  // Active file focused for preview
  const paramFileId = searchParams.get('fileId');
  const [activeFileId, setActiveFileId] = useState<string>(
    paramFileId && validFiles.some((f) => f.fileId === paramFileId)
      ? paramFileId
      : validFiles[0]?.fileId || ''
  );

  // Multi-selection state: array of fileIds currently selected
  const [selectedFileIds, setSelectedFileIds] = useState<string[]>(() => {
    return validFiles.map((f) => f.fileId); // Default to selecting all valid files for convenience
  });

  const [batchToastMessage, setBatchToastMessage] = useState<string | null>(null);

  useEffect(() => {
    if (paramFileId && validFiles.some((f) => f.fileId === paramFileId)) {
      setActiveFileId(paramFileId);
    } else if (validFiles.length > 0 && (!activeFileId || !validFiles.some((f) => f.fileId === activeFileId))) {
      setActiveFileId(validFiles[0].fileId);
    }
  }, [paramFileId, validFiles, activeFileId]);

  // Ensure selectedFileIds only contains valid existing IDs
  useEffect(() => {
    const validIdSet = new Set(validFiles.map((f) => f.fileId));
    setSelectedFileIds((prev) => {
      const filtered = prev.filter((id) => validIdSet.has(id));
      return filtered.length > 0 ? filtered : validFiles.length > 0 ? [validFiles[0].fileId] : [];
    });
  }, [draft.files]);

  const handleSelectFile = (fileId: string) => {
    setActiveFileId(fileId);
    setSearchParams({ fileId });
  };

  const handleToggleSelectDoc = (fileId: string, e?: React.MouseEvent) => {
    if (e) e.stopPropagation();
    setSelectedFileIds((prev) => {
      if (prev.includes(fileId)) {
        if (prev.length === 1) return prev; // Keep at least one selected
        return prev.filter((id) => id !== fileId);
      } else {
        return [...prev, fileId];
      }
    });
  };

  const handleSelectAll = () => {
    if (selectedFileIds.length === validFiles.length) {
      // If all selected, keep only active
      setSelectedFileIds([activeFileId]);
    } else {
      setSelectedFileIds(validFiles.map((f) => f.fileId));
    }
  };

  const handleApplyBatchPreset = (preset: {
    colourMode?: 'bw' | 'colour';
    sides?: 'single' | 'double';
    copies?: number;
    paperSize?: 'A4' | 'A3' | 'Letter' | 'Legal';
  }, label: string) => {
    const targets = selectedFileIds.length > 0 ? selectedFileIds : [activeFileId];
    updateMultipleFilesSettings(targets, preset);
    setBatchToastMessage(`Applied "${label}" to ${targets.length} document${targets.length === 1 ? '' : 's'}`);
    setTimeout(() => setBatchToastMessage(null), 3000);
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
  const isMultiSelected = selectedFileIds.length > 1;
  const isAllSelected = selectedFileIds.length === validFiles.length;

  const currentPreviewIndex = validFiles.findIndex((f) => f.fileId === activeFile.fileId);

  const handleNavigatePreview = (direction: 'prev' | 'next') => {
    if (validFiles.length <= 1) return;
    const nextIdx = direction === 'next'
      ? (currentPreviewIndex + 1) % validFiles.length
      : (currentPreviewIndex - 1 + validFiles.length) % validFiles.length;
    handleSelectFile(validFiles[nextIdx].fileId);
  };

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
              Select one or multiple documents to configure paper size, colour mode, duplex, and copies.
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

        {/* Multi-Document Selection Tabs Bar (if multiple files) */}
        {validFiles.length > 1 && (
          <div className="mb-6 bg-slate-50 border border-slate-200/90 rounded-2xl p-3.5 space-y-3">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={handleSelectAll}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-white border border-slate-200 text-slate-700 hover:bg-slate-100 transition-colors shadow-2xs"
                >
                  {isAllSelected ? (
                    <>
                      <CheckSquare className="w-3.5 h-3.5 text-blue-600" />
                      <span>Deselect Others</span>
                    </>
                  ) : (
                    <>
                      <Square className="w-3.5 h-3.5 text-slate-400" />
                      <span>Select All ({validFiles.length} Documents)</span>
                    </>
                  )}
                </button>

                <span className="text-xs font-medium text-slate-600">
                  <strong>{selectedFileIds.length}</strong> of <strong>{validFiles.length}</strong> selected
                </span>
              </div>

              {/* Batch Quick Presets when multiple are selected */}
              <div className="flex items-center gap-1.5 flex-wrap">
                <span className="text-[11px] text-slate-400 font-medium mr-1 flex items-center gap-1">
                  <Sparkles className="w-3 h-3 text-amber-500" /> Apply to Selected:
                </span>
                <button
                  type="button"
                  onClick={() => handleApplyBatchPreset({ colourMode: 'bw' }, 'All Black & White')}
                  className="px-2 py-1 rounded bg-white hover:bg-slate-100 border border-slate-200 text-[11px] font-medium text-slate-700 transition"
                >
                  Set B&W
                </button>
                <button
                  type="button"
                  onClick={() => handleApplyBatchPreset({ colourMode: 'colour' }, 'All Full Colour')}
                  className="px-2 py-1 rounded bg-white hover:bg-slate-100 border border-slate-200 text-[11px] font-medium text-slate-700 transition"
                >
                  Set Colour
                </button>
                <button
                  type="button"
                  onClick={() => handleApplyBatchPreset({ sides: 'double' }, 'All Double-Sided')}
                  className="px-2 py-1 rounded bg-white hover:bg-slate-100 border border-slate-200 text-[11px] font-medium text-slate-700 transition"
                >
                  Set Duplex
                </button>
                <button
                  type="button"
                  onClick={() => handleApplyBatchPreset({ copies: 2 }, '2 Copies Each')}
                  className="px-2 py-1 rounded bg-white hover:bg-slate-100 border border-slate-200 text-[11px] font-medium text-slate-700 transition"
                >
                  2 Copies
                </button>
              </div>
            </div>

            {/* Document Selection Pills */}
            <div className="flex items-center gap-2 overflow-x-auto pb-1 scrollbar-thin">
              {validFiles.map((file, idx) => {
                const isSelected = selectedFileIds.includes(file.fileId);
                const isFocused = file.fileId === activeFile.fileId;
                return (
                  <div
                    key={file.fileId}
                    onClick={() => handleSelectFile(file.fileId)}
                    className={`flex items-center gap-2 px-3 py-1.5 rounded-xl text-xs font-semibold whitespace-nowrap transition-all border cursor-pointer select-none ${
                      isSelected
                        ? isFocused
                          ? 'bg-blue-600 text-white border-blue-600 shadow-sm ring-2 ring-blue-300'
                          : 'bg-blue-50 text-blue-900 border-blue-300 shadow-2xs'
                        : 'bg-white text-slate-600 border-slate-200 hover:border-slate-300 hover:bg-slate-50'
                    }`}
                  >
                    <button
                      type="button"
                      onClick={(e) => handleToggleSelectDoc(file.fileId, e)}
                      title={isSelected ? 'Unselect this file' : 'Select this file'}
                      className="p-0.5 rounded hover:bg-black/10 transition"
                    >
                      {isSelected ? (
                        <CheckSquare className={`w-3.5 h-3.5 ${isFocused ? 'text-white' : 'text-blue-600'}`} />
                      ) : (
                        <Square className="w-3.5 h-3.5 text-slate-400" />
                      )}
                    </button>
                    <span className="truncate max-w-[130px]">
                      {idx + 1}. {file.originalFileName}
                    </span>
                    <span
                      className={`px-1.5 py-0.5 rounded text-[10px] ${
                        isFocused
                          ? 'bg-blue-700 text-blue-100'
                          : isSelected
                          ? 'bg-blue-200/80 text-blue-900'
                          : 'bg-slate-100 text-slate-600'
                      }`}
                    >
                      {file.pageCount}p
                    </span>
                  </div>
                );
              })}
            </div>

            {/* Batch Status Notification Toast */}
            {batchToastMessage && (
              <div className="bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs px-3 py-1.5 rounded-lg flex items-center gap-2 animate-fade-in">
                <Check className="w-3.5 h-3.5 text-emerald-600" />
                <span>{batchToastMessage}</span>
              </div>
            )}
          </div>
        )}

        {/* Multi-Selection Alert Notice if > 1 selected */}
        {isMultiSelected && (
          <div className="mb-6 p-4 rounded-2xl bg-gradient-to-r from-blue-50 via-indigo-50/50 to-blue-50 border border-blue-200/80 shadow-subtle flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-xl bg-blue-600 text-white flex items-center justify-center flex-shrink-0 shadow-sm">
                <Layers className="w-5 h-5" />
              </div>
              <div>
                <strong className="text-sm text-blue-950 font-bold block">
                  Multi-Document Configuration Mode Active
                </strong>
                <p className="text-xs text-blue-700 mt-0.5">
                  You have selected <strong>{selectedFileIds.length} documents</strong>. Any changes you make below (copies, colour mode, duplex, paper size) will automatically apply to all selected documents simultaneously.
                </p>
              </div>
            </div>
            <button
              type="button"
              onClick={() => setSelectedFileIds([activeFile.fileId])}
              className="text-xs font-semibold text-blue-800 hover:text-blue-900 underline whitespace-nowrap self-start sm:self-center"
            >
              Configure "{activeFile.originalFileName.substring(0, 15)}..." only
            </button>
          </div>
        )}

        {/* Two-Column Workspace: Left = Form, Right = Live Preview */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start mb-12">
          {/* Settings Form Column */}
          <div className="lg:col-span-7 space-y-6">
            <PrintSettingsForm
              file={activeFile}
              onUpdateSettings={(newSettings) => {
                if (isMultiSelected) {
                  updateMultipleFilesSettings(selectedFileIds, newSettings);
                  setBatchToastMessage(`Updated settings for ${selectedFileIds.length} documents.`);
                  setTimeout(() => setBatchToastMessage(null), 2500);
                } else {
                  updateFileSettings(activeFile.fileId, newSettings);
                }
              }}
            />
          </div>

          {/* PDF Preview Column */}
          <div className="lg:col-span-5 bg-white p-5 rounded-2xl border border-slate-200/80 shadow-subtle sticky top-20">
            <div className="flex items-center justify-between pb-3 mb-3 border-b border-slate-100">
              <div className="min-w-0 pr-2">
                <div className="flex items-center gap-2">
                  <h3 className="text-sm font-bold text-slate-900">Document Preview</h3>
                  {validFiles.length > 1 && (
                    <span className="text-[10px] text-slate-500 font-medium">
                      ({currentPreviewIndex + 1} of {validFiles.length})
                    </span>
                  )}
                </div>
                <p className="text-[11px] text-slate-500 truncate" title={activeFile.originalFileName}>
                  {activeFile.originalFileName}
                </p>
              </div>

              <div className="flex items-center gap-1.5 flex-shrink-0">
                {validFiles.length > 1 && (
                  <div className="flex items-center gap-1 mr-1">
                    <button
                      type="button"
                      onClick={() => handleNavigatePreview('prev')}
                      className="p-1 rounded-md text-slate-500 hover:bg-slate-100 hover:text-slate-700 transition"
                      title="Preview previous document"
                    >
                      <ChevronLeft className="w-4 h-4" />
                    </button>
                    <button
                      type="button"
                      onClick={() => handleNavigatePreview('next')}
                      className="p-1 rounded-md text-slate-500 hover:bg-slate-100 hover:text-slate-700 transition"
                      title="Preview next document"
                    >
                      <ChevronRight className="w-4 h-4" />
                    </button>
                  </div>
                )}
                <span className="badge-blue text-[11px]">
                  {activeFile.pageCount} Pages
                </span>
              </div>
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
