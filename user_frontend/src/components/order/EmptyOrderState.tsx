import React from 'react';
import { Link } from 'react-router-dom';
import { FileQuestion } from 'lucide-react';
import { Button } from '../ui/Button';

export interface EmptyOrderStateProps {
  title?: string;
  description?: string;
  actionText?: string;
  actionHref?: string;
}

export const EmptyOrderState: React.FC<EmptyOrderStateProps> = ({
  title = 'No documents in your order',
  description = 'You have not uploaded any PDF documents yet. Upload your files to configure print settings and review your order.',
  actionText = 'Upload Documents',
  actionHref = '/upload',
}) => {
  return (
    <div className="flex flex-col items-center justify-center p-12 text-center bg-white rounded-2xl border border-slate-200/80 shadow-subtle max-w-lg mx-auto">
      <div className="w-16 h-16 rounded-2xl bg-blue-50 text-blue-600 flex items-center justify-center mb-4">
        <FileQuestion className="w-8 h-8" />
      </div>
      <h3 className="text-lg font-bold text-slate-900 mb-1.5">{title}</h3>
      <p className="text-sm text-slate-500 mb-6 leading-relaxed max-w-sm">{description}</p>
      <Link to={actionHref}>
        <Button variant="primary">{actionText}</Button>
      </Link>
    </div>
  );
};
