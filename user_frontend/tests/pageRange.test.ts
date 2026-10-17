import { describe, it, expect } from 'vitest';
import { parsePageRange } from '../src/utils/pageRange';

describe('pageRange utility', () => {
  it('handles "all" correctly for a 10-page document', () => {
    const result = parsePageRange('all', 10);
    expect(result.isValid).toBe(true);
    expect(result.count).toBe(10);
    expect(result.selectedPages).toEqual([1, 2, 3, 4, 5, 6, 7, 8, 9, 10]);
  });

  it('handles empty string as all pages', () => {
    const result = parsePageRange('', 5);
    expect(result.isValid).toBe(true);
    expect(result.count).toBe(5);
  });

  it('parses comma-separated single pages', () => {
    const result = parsePageRange('1, 3, 5', 10);
    expect(result.isValid).toBe(true);
    expect(result.count).toBe(3);
    expect(result.selectedPages).toEqual([1, 3, 5]);
  });

  it('parses ranges and individual pages together', () => {
    const result = parsePageRange('1-3, 5, 8-10', 10);
    expect(result.isValid).toBe(true);
    expect(result.count).toBe(7); // 1, 2, 3, 5, 8, 9, 10
    expect(result.selectedPages).toEqual([1, 2, 3, 5, 8, 9, 10]);
  });

  it('deduplicates overlapping pages', () => {
    const result = parsePageRange('1-3, 2-4, 3', 10);
    expect(result.isValid).toBe(true);
    expect(result.count).toBe(4); // 1, 2, 3, 4
    expect(result.selectedPages).toEqual([1, 2, 3, 4]);
  });

  it('rejects out of bounds page numbers', () => {
    const result = parsePageRange('12', 10);
    expect(result.isValid).toBe(false);
    expect(result.errorMessage).toContain('exceeds total document pages');
  });

  it('rejects range where start > end', () => {
    const result = parsePageRange('5-2', 10);
    expect(result.isValid).toBe(false);
    expect(result.errorMessage).toContain('cannot be greater than');
  });

  it('rejects page 0 or negative numbers', () => {
    const result = parsePageRange('0-5', 10);
    expect(result.isValid).toBe(false);
    expect(result.errorMessage).toContain('must start from 1');
  });

  it('rejects non-numeric characters', () => {
    const result = parsePageRange('abc', 10);
    expect(result.isValid).toBe(false);
  });
});
