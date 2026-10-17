import { describe, it, expect } from 'vitest';
import {
  validateBasicFile,
  validatePdfMagicBytes,
  sanitizeFileName,
} from '../src/utils/fileValidation';

describe('fileValidation utility', () => {
  describe('sanitizeFileName', () => {
    it('strips path traversal and dangerous characters', () => {
      const malicious = '../../etc/passwd/test:file<name>*.pdf';
      const clean = sanitizeFileName(malicious);
      expect(clean).not.toContain('..');
      expect(clean).not.toContain('/');
      expect(clean).not.toContain(':');
      expect(clean).not.toContain('<');
      expect(clean).not.toContain('>');
      expect(clean.endsWith('.pdf')).toBe(true);
    });

    it('returns default document.pdf when given empty string', () => {
      expect(sanitizeFileName('')).toBe('unnamed_document.pdf');
    });
  });

  describe('validateBasicFile', () => {
    it('rejects 0-byte empty files', () => {
      const emptyFile = new File([], 'empty.pdf', { type: 'application/pdf' });
      const result = validateBasicFile(emptyFile);
      expect(result.isValid).toBe(false);
      expect(result.errorCode).toBe('EMPTY_FILE');
    });

    it('rejects unsupported files like .txt or .exe', () => {
      const textFile = new File(['hello world'], 'document.txt', { type: 'text/plain' });
      const result = validateBasicFile(textFile);
      expect(result.isValid).toBe(false);
      expect(result.errorCode).toBe('INVALID_TYPE');
    });

    it('accepts valid PDF file within size limit', () => {
      const content = new Uint8Array(100);
      const file = new File([content], 'test.pdf', { type: 'application/pdf' });
      const result = validateBasicFile(file, 1000);
      expect(result.isValid).toBe(true);
    });

    it('accepts valid image file within size limit', () => {
      const content = new Uint8Array(100);
      const file = new File([content], 'photo.png', { type: 'image/png' });
      const result = validateBasicFile(file, 1000);
      expect(result.isValid).toBe(true);
    });

    it('rejects oversized files', () => {
      const content = new Uint8Array(100);
      const file = new File([content], 'large.pdf', { type: 'application/pdf' });
      const result = validateBasicFile(file, 50); // limit to 50 bytes
      expect(result.isValid).toBe(false);
      expect(result.errorCode).toBe('FILE_TOO_LARGE');
    });
  });

  describe('validatePdfMagicBytes', () => {
    it('accepts genuine PDF header (%PDF-)', async () => {
      // 0x25, 0x50, 0x44, 0x46, 0x2D -> %PDF-
      const validHeader = new Uint8Array([0x25, 0x50, 0x44, 0x46, 0x2d, 0x31, 0x2e, 0x37]);
      const file = new File([validHeader], 'valid.pdf', { type: 'application/pdf' });
      const result = await validatePdfMagicBytes(file);
      expect(result.isValid).toBe(true);
    });

    it('rejects spoofed file with fake .pdf extension', async () => {
      // Fake text file disguised as PDF
      const fakeHeader = new TextEncoder().encode('GIF89a fake image file');
      const file = new File([fakeHeader], 'fake.pdf', { type: 'application/pdf' });
      const result = await validatePdfMagicBytes(file);
      expect(result.isValid).toBe(false);
      expect(result.errorCode).toBe('INVALID_MAGIC_BYTES');
    });
  });
});
