import React from 'react';
import { PrintDraftProvider } from '../context/PrintDraftContext';

export interface ProvidersProps {
  children: React.ReactNode;
}

export const Providers: React.FC<ProvidersProps> = ({ children }) => {
  return <PrintDraftProvider>{children}</PrintDraftProvider>;
};
