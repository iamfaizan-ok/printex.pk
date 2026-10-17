/**
 * Formats a raw byte count into human-readable string (e.g. 1.25 MB).
 */
export function formatFileSize(bytes: number): string {
  if (bytes < 0 || isNaN(bytes)) return '0 B';
  if (bytes === 0) return '0 B';

  const units = ['B', 'KB', 'MB', 'GB', 'TB'];
  const k = 1024;
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  const clampedIndex = Math.min(i, units.length - 1);
  const size = bytes / Math.pow(k, clampedIndex);

  // If exact integer, show no decimal; otherwise show up to 2 decimal places
  const formatted = size >= 10 || clampedIndex === 0 
    ? Math.round(size).toString() 
    : size.toFixed(1);

  return `${formatted} ${units[clampedIndex]}`;
}
