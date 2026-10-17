import * as pdfjsLib from 'pdfjs-dist';

// Configure the PDF.js worker using local public asset (no external CDN dependency)
if (typeof window !== 'undefined') {
  pdfjsLib.GlobalWorkerOptions.workerSrc = '/pdf.worker.min.js';
}

export interface PDFInspectionResult {
  isSuccess: boolean;
  pageCount: number;
  errorMessage?: string;
  isPasswordProtected?: boolean;
}

export interface PDFRenderTaskHandle {
  promise: Promise<void>;
  cancel: () => void;
}

export const pdfService = {
  /**
   * Loads and inspects a PDF file in-browser to determine total page count
   * and verify document integrity.
   */
  async inspectPdf(file: File): Promise<PDFInspectionResult> {
    try {
      const buffer = await file.arrayBuffer();

      // Load document without eval execution
      const loadingTask = pdfjsLib.getDocument({
        data: new Uint8Array(buffer),
        isEvalSupported: false,
        useSystemFonts: true,
      });

      const pdfDoc = await loadingTask.promise;
      const pageCount = pdfDoc.numPages;

      // Clean up document instance after inspection
      await pdfDoc.destroy();

      if (pageCount < 1) {
        return {
          isSuccess: false,
          pageCount: 0,
          errorMessage: 'The document appears to contain 0 pages.',
        };
      }

      return {
        isSuccess: true,
        pageCount,
      };
    } catch (err: unknown) {
      const error = err as { name?: string; message?: string };

      if (error?.name === 'PasswordException') {
        return {
          isSuccess: false,
          pageCount: 0,
          isPasswordProtected: true,
          errorMessage: 'This PDF is password-protected. Please remove the password and try again.',
        };
      }

      if (error?.name === 'InvalidPDFException') {
        return {
          isSuccess: false,
          pageCount: 0,
          errorMessage: 'The document is corrupted or not a valid PDF file.',
        };
      }

      return {
        isSuccess: false,
        pageCount: 0,
        errorMessage: error?.message || 'Failed to inspect PDF document.',
      };
    }
  },

  /**
   * Loads a PDFDocumentProxy for interactive preview rendering.
   */
  async loadDocument(file: File | string): Promise<pdfjsLib.PDFDocumentProxy> {
    let source: { data: Uint8Array } | { url: string };

    if (typeof file === 'string') {
      source = { url: file };
    } else {
      const buffer = await file.arrayBuffer();
      source = { data: new Uint8Array(buffer) };
    }

    const loadingTask = pdfjsLib.getDocument({
      ...source,
      isEvalSupported: false,
      useSystemFonts: true,
    });

    return loadingTask.promise;
  },

  /**
   * Renders a specific page onto an HTML5 canvas with HiDPI support and cancellation.
   */
  renderPageToCanvas(
    doc: pdfjsLib.PDFDocumentProxy,
    pageNumber: number,
    canvas: HTMLCanvasElement,
    targetWidth: number = 600
  ): PDFRenderTaskHandle {
    let isCancelled = false;
    let currentRenderTask: pdfjsLib.RenderTask | null = null;

    const renderPromise = (async () => {
      const page = await doc.getPage(pageNumber);
      if (isCancelled) return;

      const unscaledViewport = page.getViewport({ scale: 1.0 });
      const scale = targetWidth / unscaledViewport.width;
      const viewport = page.getViewport({ scale });

      const ctx = canvas.getContext('2d');
      if (!ctx) {
        throw new Error('Canvas 2D context is not available.');
      }

      const pixelRatio = window.devicePixelRatio || 1;
      canvas.width = Math.floor(viewport.width * pixelRatio);
      canvas.height = Math.floor(viewport.height * pixelRatio);
      canvas.style.width = `${Math.floor(viewport.width)}px`;
      canvas.style.height = `${Math.floor(viewport.height)}px`;

      ctx.save();
      ctx.scale(pixelRatio, pixelRatio);

      const renderContext = {
        canvasContext: ctx,
        viewport,
      };

      currentRenderTask = page.render(renderContext);
      await currentRenderTask.promise;
      ctx.restore();
    })();

    return {
      promise: renderPromise,
      cancel: () => {
        isCancelled = true;
        if (currentRenderTask) {
          try {
            currentRenderTask.cancel();
          } catch {
            // Task might have already completed
          }
        }
      },
    };
  },
};
