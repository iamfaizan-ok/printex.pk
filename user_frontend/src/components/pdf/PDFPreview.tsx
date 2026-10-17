import React, { useState, useEffect, useRef } from 'react';
import { AlertCircle } from 'lucide-react';
import { PrintFile } from '../../types/printFile';
import { usePDFDocument } from '../../hooks/usePDFDocument';
import { pdfService, PDFRenderTaskHandle } from '../../services/pdfService';
import { PDFPageNavigation } from './PDFPageNavigation';
import { PDFLoadingState } from './PDFLoadingState';

export interface PDFPreviewProps {
  file: PrintFile;
  className?: string;
}

export const PDFPreview: React.FC<PDFPreviewProps> = ({ file, className = '' }) => {
  const isImage = file.fileType === 'image' || Boolean(file.originalFileName.match(/\.(png|jpe?g|webp|svg|bmp)$/i));
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [zoomScale, setZoomScale] = useState<number>(1.0);
  const [isRenderingPage, setIsRenderingPage] = useState<boolean>(false);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const renderHandleRef = useRef<PDFRenderTaskHandle | null>(null);

  // Load PDF document only if it is a PDF file
  const { doc, numPages, isLoading: isDocLoading, error: docError } = usePDFDocument(
    isImage ? null : file.file || file.objectUrl
  );

  // Reset page when document changes
  useEffect(() => {
    setCurrentPage(1);
    setZoomScale(1.0);
  }, [file.fileId]);

  // Render currently selected page onto canvas
  useEffect(() => {
    if (!doc || !canvasRef.current || currentPage < 1) return;

    // Cancel any previous in-flight render task to avoid race conditions
    if (renderHandleRef.current) {
      renderHandleRef.current.cancel();
      renderHandleRef.current = null;
    }

    setIsRenderingPage(true);

    const baseWidth = 560; // crisp baseline width
    const targetWidth = baseWidth * zoomScale;

    const handle = pdfService.renderPageToCanvas(
      doc,
      currentPage,
      canvasRef.current,
      targetWidth
    );
    renderHandleRef.current = handle;

    handle.promise
      .then(() => {
        setIsRenderingPage(false);
      })
      .catch((err: unknown) => {
        // PDF.js throws a cancel exception if render was cancelled - ignore that
        const e = err as { name?: string };
        if (e?.name !== 'RenderingCancelledException') {
          console.error('Error rendering page:', err);
          setIsRenderingPage(false);
        }
      });

    return () => {
      if (renderHandleRef.current) {
        renderHandleRef.current.cancel();
      }
    };
  }, [doc, currentPage, zoomScale]);

  if (isDocLoading) {
    return <PDFLoadingState message={`Loading ${file.originalFileName}...`} />;
  }

  if (docError) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[300px] p-6 text-center bg-rose-50/50 rounded-xl border border-rose-200">
        <AlertCircle className="w-8 h-8 text-rose-500 mb-2" />
        <h4 className="text-sm font-semibold text-rose-900 mb-1">Preview Unavailable</h4>
        <p className="text-xs text-rose-700 max-w-sm">{docError}</p>
      </div>
    );
  }

  if (isImage) {
    return (
      <div className={`flex flex-col gap-3 ${className}`}>
        <PDFPageNavigation
          currentPage={1}
          totalPages={1}
          zoomScale={zoomScale}
          onPageChange={() => {}}
          onZoomChange={(zoom) => setZoomScale(zoom)}
          onZoomReset={() => setZoomScale(1.0)}
        />
        <div className="relative flex items-center justify-center min-h-[400px] max-h-[580px] overflow-auto bg-slate-100 rounded-xl border border-slate-200 p-4">
          <img
            src={file.objectUrl}
            alt={file.originalFileName}
            style={{ transform: `scale(${zoomScale})`, transformOrigin: 'center center' }}
            className="shadow-card rounded max-w-full max-h-[500px] object-contain transition-transform duration-150"
          />
        </div>
      </div>
    );
  }

  return (
    <div className={`flex flex-col gap-3 ${className}`}>
      {numPages > 0 && (
        <PDFPageNavigation
          currentPage={currentPage}
          totalPages={numPages}
          zoomScale={zoomScale}
          onPageChange={(page) => setCurrentPage(page)}
          onZoomChange={(zoom) => setZoomScale(zoom)}
          onZoomReset={() => setZoomScale(1.0)}
        />
      )}

      {/* Canvas Viewport */}
      <div className="relative flex items-center justify-center min-h-[400px] max-h-[580px] overflow-auto bg-slate-100 rounded-xl border border-slate-200 p-4">
        {isRenderingPage && (
          <div className="absolute inset-0 bg-white/60 backdrop-blur-[1px] flex items-center justify-center z-10 transition-opacity">
            <span className="text-xs font-semibold text-slate-600 bg-white px-3 py-1.5 rounded-full shadow-sm border border-slate-200">
              Rendering Page {currentPage}...
            </span>
          </div>
        )}

        <canvas
          ref={canvasRef}
          className="shadow-card rounded bg-white max-w-full transition-transform duration-150"
        />
      </div>
    </div>
  );
};
