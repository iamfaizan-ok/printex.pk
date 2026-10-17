import { usePrintDraftContext, PrintDraftContextValue } from '../context/PrintDraftContext';

/**
 * Custom hook to access and manage PrintX draft state across pages and components.
 */
export function usePrintDraft(): PrintDraftContextValue {
  return usePrintDraftContext();
}
