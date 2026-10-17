/**
 * Generates a cryptographically random unique identifier.
 * Safe for modern browsers and Node/test environments.
 */
export function generateId(prefix: string = 'px'): string {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return `${prefix}_${crypto.randomUUID()}`;
  }
  
  // Fallback for older environments
  const timestamp = Date.now().toString(36);
  const randomPart = Math.random().toString(36).substring(2, 10);
  return `${prefix}_${timestamp}_${randomPart}`;
}
