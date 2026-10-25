import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { Printer, FileText, Trash2 } from 'lucide-react';
import { usePrintDraft } from '../../hooks/usePrintDraft';
import { Button } from '../ui/Button';

export const Header: React.FC = () => {
  const { draft, clearDraft } = usePrintDraft();
  const location = useLocation();

  const totalFiles = draft.files.length;
  const isWorkflowActive = location.pathname !== '/' && totalFiles > 0;
  const [stationId, setStationId] = React.useState<string | null>(() => {
    try {
      return localStorage.getItem('printx_shop_id') || null;
    } catch {
      return null;
    }
  });

  React.useEffect(() => {
    try {
      const current = localStorage.getItem('printx_shop_id');
      if (current !== stationId) {
        setStationId(current);
      }
    } catch {
      // Ignore in sandbox
    }
  }, [location]);

  return (
    <header className="sticky top-0 z-40 bg-white/90 backdrop-blur-md border-b border-slate-200/80 transition-all">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo & Brand */}
          <Link to="/" className="flex items-center gap-2.5 group focus:outline-none focus:ring-2 focus:ring-blue-600 rounded-lg p-1">
            <div className="w-10 h-10 rounded-xl bg-blue-600 text-white flex items-center justify-center shadow-sm group-hover:bg-blue-700 transition-colors">
              <Printer className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-1.5">
                <span className="text-xl font-bold tracking-tight text-slate-900">Print</span>
                <span className="text-xl font-bold tracking-tight text-blue-600">X</span>
              </div>
              <p className="text-[10px] uppercase font-semibold tracking-wider text-slate-600 -mt-0.5">Online Printing</p>
            </div>
          </Link>

          {/* Center / Right controls */}
          <div className="flex items-center gap-3">
            {stationId && (
              <div className="hidden md:flex items-center gap-1.5 px-3 py-1 bg-emerald-50 border border-emerald-200/80 text-emerald-800 rounded-full text-xs font-semibold shadow-xs">
                <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
                <span>Station: {stationId}</span>
              </div>
            )}
            {isWorkflowActive && (
              <div className="hidden sm:flex items-center gap-2 px-3 py-1 bg-slate-100 rounded-full text-xs font-medium text-slate-700">
                <FileText className="w-3.5 h-3.5 text-blue-600" />
                <span>
                  {totalFiles} document{totalFiles === 1 ? '' : 's'} in draft
                </span>
              </div>
            )}

            {totalFiles > 0 && (
              <Button
                variant="ghost"
                size="sm"
                icon={<Trash2 className="w-4 h-4 text-slate-400 group-hover:text-red-500" />}
                onClick={() => {
                  if (window.confirm('Are you sure you want to discard this draft and start a new order?')) {
                    clearDraft();
                  }
                }}
                className="text-xs text-slate-700 hover:text-red-600 hover:bg-red-50"
                title="Discard draft and start fresh"
              >
                <span className="hidden sm:inline">Start New Order</span>
              </Button>
            )}

            <Link to="/upload">
              <Button variant="primary" size="sm">
                {totalFiles > 0 ? 'Resume Draft' : 'Print Now'}
              </Button>
            </Link>
          </div>
        </div>
      </div>
    </header>
  );
};
