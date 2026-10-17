import { PrintFile } from './printFile';

export type WorkflowStep = 'upload' | 'settings' | 'review' | 'payment';

export interface PrintDraft {
  draftId: string;
  createdAt: string;
  updatedAt: string;
  currentStep: WorkflowStep;
  files: PrintFile[];
}

export type PrintDraftAction =
  | { type: 'SET_FILES'; payload: PrintFile[] }
  | { type: 'ADD_FILES'; payload: PrintFile[] }
  | { type: 'UPDATE_FILE'; payload: { fileId: string; updates: Partial<PrintFile> } }
  | { type: 'UPDATE_FILE_SETTINGS'; payload: { fileId: string; settings: Partial<PrintFile['printSettings']> } }
  | { type: 'REMOVE_FILE'; payload: { fileId: string } }
  | { type: 'REORDER_FILES'; payload: { startIndex: number; endIndex: number } }
  | { type: 'REPLACE_FILE'; payload: { fileId: string; newFile: PrintFile } }
  | { type: 'CLEAR_DRAFT' }
  | { type: 'SET_CURRENT_STEP'; payload: WorkflowStep }
  | { type: 'LOAD_DRAFT'; payload: PrintDraft };
