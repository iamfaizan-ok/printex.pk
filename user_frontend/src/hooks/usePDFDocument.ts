import { useState, useEffect } from 'react';
import * as pdfjsLib from 'pdfjs-dist';
import { pdfService } from '../services/pdfService';

interface UsePDFDocumentResult {
  doc: pdfjsLib.PDFDocumentProxy | null;
  numPages: number;
  isLoading: boolean;
  error: string | null;
}

/**
 * Loads and manages a PDF.js PDFDocumentProxy instance with automatic cleanup
 * and destruction on unmount.
 */
export function usePDFDocument(fileOrUrl: File | string | null | undefined): UsePDFDocumentResult {
  const [doc, setDoc] = useState<pdfjsLib.PDFDocumentProxy | null>(null);
  const [numPages, setNumPages] = useState<number>(0);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let isCancelled = false;
    let loadedDoc: pdfjsLib.PDFDocumentProxy | null = null;

    if (!fileOrUrl) {
      setDoc(null);
      setNumPages(0);
      setIsLoading(false);
      setError(null);
      return;
    }

    setIsLoading(true);
    setError(null);

    pdfService
      .loadDocument(fileOrUrl)
      .then((pdf) => {
        if (isCancelled) {
          pdf.destroy();
          return;
        }
        loadedDoc = pdf;
        setDoc(pdf);
        setNumPages(pdf.numPages);
        setIsLoading(false);
      })
      .catch((err: unknown) => {
        if (isCancelled) return;
        const e = err as { message?: string };
        setError(e?.message || 'Failed to render PDF preview.');
        setDoc(null);
        setNumPages(0);
        setIsLoading(false);
      });

    return () => {
      isCancelled = true;
      if (loadedDoc) {
        try {
          loadedDoc.destroy();
        } catch {
          // ignore cleanup errors
        }
      }
    };
  }, [fileOrUrl]);

  return { doc, numPages, isLoading, error };
}
