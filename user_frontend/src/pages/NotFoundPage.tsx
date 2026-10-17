import React from 'react';
import { Link } from 'react-router-dom';
import { Printer, Home, ArrowLeft } from 'lucide-react';
import { Button } from '../components/ui/Button';

export const NotFoundPage: React.FC = () => {
  return (
    <div className="flex-1 flex items-center justify-center py-16 px-4 sm:px-6">
      <div className="max-w-md w-full bg-white rounded-2xl border border-slate-200/80 p-8 shadow-card text-center">
        <div className="w-16 h-16 rounded-2xl bg-blue-50 text-blue-600 flex items-center justify-center mx-auto mb-5">
          <Printer className="w-8 h-8 opacity-40" />
        </div>

        <span className="text-xs font-bold uppercase tracking-wider text-blue-600">404 Error</span>
        <h1 className="text-2xl font-extrabold text-slate-900 mt-1 mb-2">Page Not Found</h1>

        <p className="text-sm text-slate-600 mb-8 leading-relaxed">
          The page or document route you are trying to view does not exist or has been moved.
        </p>

        <div className="flex flex-col sm:flex-row items-center justify-center gap-3">
          <Link to="/" className="w-full sm:w-auto">
            <Button variant="primary" size="md" icon={<Home className="w-4 h-4" />} className="w-full">
              Back to Home
            </Button>
          </Link>
          <Link to="/upload" className="w-full sm:w-auto">
            <Button variant="outline" size="md" icon={<ArrowLeft className="w-4 h-4" />} className="w-full">
              Upload Files
            </Button>
          </Link>
        </div>
      </div>
    </div>
  );
};
