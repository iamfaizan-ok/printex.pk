import React from 'react';
import { ChevronLeft, ChevronRight, ZoomIn, ZoomOut, RotateCcw } from 'lucide-react';

export interface PDFPageNavigationProps {
  currentPage: number;
  totalPages: number;
  zoomScale: number;
  onPageChange: (newPage: number) => void;
  onZoomChange: (newZoom: number) => void;
  onZoomReset: () => void;
}

export const PDFPageNavigation: React.FC<PDFPageNavigationProps> = ({
  currentPage,
  totalPages,
  zoomScale,
  onPageChange,
  onZoomChange,
  onZoomReset,
}) => {
  return (
    <div className="flex flex-wrap items-center justify-between gap-3 p-3 bg-white border border-slate-200/80 rounded-xl shadow-subtle text-xs text-slate-700">
      {/* Page Navigation */}
      <div className="flex items-center gap-2">
        <button
          type="button"
          disabled={currentPage <= 1}
          onClick={() => onPageChange(currentPage - 1)}
          className="p-1.5 rounded-lg border border-slate-200 hover:bg-slate-50 disabled:opacity-30 disabled:cursor-not-allowed focus:outline-none focus:ring-2 focus:ring-blue-600 transition-colors"
          title="Previous Page"
          aria-label="Previous Page"
        >
          <ChevronLeft className="w-4 h-4" />
        </button>

        <span className="font-medium px-2">
          Page <span className="font-bold text-slate-900">{currentPage}</span> of{' '}
          <span className="font-bold text-slate-900">{totalPages}</span>
        </span>

        <button
          type="button"
          disabled={currentPage >= totalPages}
          onClick={() => onPageChange(currentPage + 1)}
          className="p-1.5 rounded-lg border border-slate-200 hover:bg-slate-50 disabled:opacity-30 disabled:cursor-not-allowed focus:outline-none focus:ring-2 focus:ring-blue-600 transition-colors"
          title="Next Page"
          aria-label="Next Page"
        >
          <ChevronRight className="w-4 h-4" />
        </button>
      </div>

      {/* Zoom Controls */}
      <div className="flex items-center gap-1.5">
        <button
          type="button"
          disabled={zoomScale <= 0.6}
          onClick={() => onZoomChange(Math.max(0.5, zoomScale - 0.2))}
          className="p-1.5 rounded-lg border border-slate-200 hover:bg-slate-50 disabled:opacity-30 disabled:cursor-not-allowed focus:outline-none focus:ring-2 focus:ring-blue-600 transition-colors"
          title="Zoom Out"
          aria-label="Zoom Out"
        >
          <ZoomOut className="w-4 h-4" />
        </button>

        <span className="w-12 text-center font-medium">{Math.round(zoomScale * 100)}%</span>

        <button
          type="button"
          disabled={zoomScale >= 2.0}
          onClick={() => onZoomChange(Math.min(2.5, zoomScale + 0.2))}
          className="p-1.5 rounded-lg border border-slate-200 hover:bg-slate-50 disabled:opacity-30 disabled:cursor-not-allowed focus:outline-none focus:ring-2 focus:ring-blue-600 transition-colors"
          title="Zoom In"
          aria-label="Zoom In"
        >
          <ZoomIn className="w-4 h-4" />
        </button>

        <button
          type="button"
          onClick={onZoomReset}
          className="p-1.5 rounded-lg border border-slate-200 hover:bg-slate-50 focus:outline-none focus:ring-2 focus:ring-blue-600 transition-colors ml-1 text-slate-500 hover:text-slate-800"
          title="Reset Zoom (100%)"
          aria-label="Reset Zoom"
        >
          <RotateCcw className="w-3.5 h-3.5" />
        </button>
      </div>
    </div>
  );
};
