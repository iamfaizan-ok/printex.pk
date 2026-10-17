import React from 'react';
import { ShieldCheck, Lock, FileCode } from 'lucide-react';

export const Footer: React.FC = () => {
  return (
    <footer className="bg-white border-t border-slate-200 mt-auto py-8">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 pb-6 border-b border-slate-100 text-xs text-slate-500">
          <div className="flex items-start gap-3">
            <div className="p-2 rounded-lg bg-blue-50 text-blue-600 mt-0.5">
              <ShieldCheck className="w-4 h-4" />
            </div>
            <div>
              <h5 className="font-semibold text-slate-800 text-sm mb-1">Local Browser Processing</h5>
              <p className="leading-relaxed">
                PDF page counting and previews are processed securely inside your browser using client-side WebAssembly & Web Workers.
              </p>
            </div>
          </div>

          <div className="flex items-start gap-3">
            <div className="p-2 rounded-lg bg-blue-50 text-blue-600 mt-0.5">
              <Lock className="w-4 h-4" />
            </div>
            <div>
              <h5 className="font-semibold text-slate-800 text-sm mb-1">Privacy Guaranteed</h5>
              <p className="leading-relaxed">
                Documents are not sent to any AI models or unauthorized third parties. Document state is cleared when you close your session.
              </p>
            </div>
          </div>

          <div className="flex items-start gap-3">
            <div className="p-2 rounded-lg bg-blue-50 text-blue-600 mt-0.5">
              <FileCode className="w-4 h-4" />
            </div>
            <div>
              <h5 className="font-semibold text-slate-800 text-sm mb-1">Phase 1 Frontend Architecture</h5>
              <p className="leading-relaxed">
                Modular React + TypeScript implementation ready for upcoming Django REST Framework & desktop print agent integration.
              </p>
            </div>
          </div>
        </div>

        <div className="flex flex-col sm:flex-row items-center justify-between pt-6 text-xs text-slate-400 gap-4">
          <p>© {new Date().getFullYear()} PrintX Technologies. All rights reserved.</p>
          <div className="flex items-center gap-6">
            <span className="inline-flex items-center gap-1.5 text-slate-500">
              <span className="w-2 h-2 rounded-full bg-emerald-500" />
              Customer Frontend v1.0.0
            </span>
          </div>
        </div>
      </div>
    </footer>
  );
};
