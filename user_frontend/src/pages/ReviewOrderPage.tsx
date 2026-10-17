import React from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { ArrowLeft, CheckCircle2, ShieldCheck } from 'lucide-react';
import { usePrintDraft } from '../hooks/usePrintDraft';
import { OrderFileSummary } from '../components/order/OrderFileSummary';
import { OrderSummary } from '../components/order/OrderSummary';
import { EmptyOrderState } from '../components/order/EmptyOrderState';
import { Button } from '../components/ui/Button';

export const ReviewOrderPage: React.FC = () => {
  const navigate = useNavigate();
  const { draft, totals, canProceedToReview } = usePrintDraft();

  const validFiles = draft.files.filter((f) => f.processingStatus === 'ready');

  if (validFiles.length === 0) {
    return (
      <div className="flex-1 py-12 px-4 sm:px-6">
        <EmptyOrderState
          title="No documents to review"
          description="Your draft is empty or documents have not been verified yet."
          actionText="Upload Documents"
          actionHref="/upload"
        />
      </div>
    );
  }

  return (
    <div className="flex-1 py-8 sm:py-12">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="mb-8 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight">
              Step 3: Review Your Print Order
            </h1>
            <p className="text-sm text-slate-500 mt-1">
              Please double check your document preferences and print impression calculations.
            </p>
          </div>

          <div className="flex items-center gap-2">
            <Link to="/print-settings">
              <Button variant="outline" size="sm" icon={<ArrowLeft className="w-4 h-4" />}>
                Modify Settings
              </Button>
            </Link>
          </div>
        </div>

        {/* Two-Column Grid: Left = Document List, Right = Summary Card */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
          {/* Left: Document List */}
          <div className="lg:col-span-8 space-y-4">
            <div className="flex items-center justify-between pb-2 border-b border-slate-200">
              <h2 className="text-sm font-bold text-slate-800 uppercase tracking-wider">
                Documents in this Order ({validFiles.length})
              </h2>
              <span className="text-xs text-slate-500 font-medium flex items-center gap-1">
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                Verified & Ready
              </span>
            </div>

            <div className="space-y-3">
              {validFiles.map((file, idx) => (
                <OrderFileSummary key={file.fileId} file={file} index={idx} />
              ))}
            </div>

            {/* Print Fulfillment Guarantee Note */}
            <div className="card-base p-4 bg-slate-50/80 border-slate-200/80 flex items-start gap-3 text-xs text-slate-600 mt-6">
              <ShieldCheck className="w-5 h-5 text-blue-600 flex-shrink-0 mt-0.5" />
              <div>
                <strong className="text-slate-800 block text-xs">Quality & Specification Notice</strong>
                <p className="mt-0.5 leading-relaxed">
                  Your selected settings (duplex, colour mode, paper dimensions) represent requested printing parameters. Our high-grade laser production printers will reproduce your vector graphics and text with crisp sharpness.
                </p>
              </div>
            </div>
          </div>

          {/* Right: Order Summary Sidebar */}
          <div className="lg:col-span-4 sticky top-20">
            <OrderSummary
              totals={totals}
              proceedDisabled={!canProceedToReview}
              onProceed={() => navigate('/payment-coming-soon')}
            />
          </div>
        </div>
      </div>
    </div>
  );
};
