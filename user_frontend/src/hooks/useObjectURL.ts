import { useState, useEffect } from 'react';

/**
 * Creates and safely manages a browser Object URL for a given File or Blob,
 * ensuring automatic revocation upon unmount or when the file changes.
 */
export function useObjectURL(file: File | Blob | null | undefined): string | null {
  const [objectUrl, setObjectUrl] = useState<string | null>(null);

  useEffect(() => {
    if (!file) {
      setObjectUrl(null);
      return;
    }

    const url = URL.createObjectURL(file);
    setObjectUrl(url);

    return () => {
      URL.revokeObjectURL(url);
    };
  }, [file]);

  return objectUrl;
}
