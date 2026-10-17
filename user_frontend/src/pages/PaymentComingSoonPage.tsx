import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  CreditCard,
  ShieldCheck,
  ArrowLeft,
  RotateCcw,
  Server,
  CheckCircle2,
} from 'lucide-react';
import { usePrintDraft } from '../hooks/usePrintDraft';
import { apiClient } from '../services/apiClient';
import { Button } from '../components/ui/Button';
import { Alert } from '../components/ui/Alert';

export const PaymentComingSoonPage: React.FC = () => {
  const navigate = useNavigate();
  const { draft, totals, clearDraft } = usePrintDraft();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [apiFeedback, setApiFeedback] = useState<{
    type: 'info' | 'success' | 'error';
    message: string;
  } | null>(null);

  const handleTestBackendSubmission = async () => {
    setIsSubmitting(true);
    setApiFeedback(null);

    try {
      if (!apiClient.isBackendConfigured()) {
        setApiFeedback({
          type: 'info',
          message:
            'Phase 1 Frontend Mode: Django REST Framework API is not currently connected. Once VITE_API_BASE_URL is pointed to your active Django server, this action will submit the JSON order payload to the backend.',
        });
        setIsSubmitting(false);
        return;
      }

      const response = await apiClient.submitOrder(draft);
      setApiFeedback({
        type: 'success',
        message: `Order successfully recorded by backend! Reference ID: ${response.orderNumber || response.orderId}`,
      });
    } catch (err: unknown) {
      const error = err as { message?: string };
      setApiFeedback({
        type: 'error',
        message: error.message || 'Unable to connect to backend server.',
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleStartFresh = () => {
    if (window.confirm('Do you want to discard this draft and start a new order?')) {
      clearDraft();
      navigate('/upload');
    }
  };

  return (
    <div className="flex-1 py-12 sm:py-16">
      <div className="max-w-3xl mx-auto px-4 sm:px-6">
        <div className="card-base p-8 sm:p-12 bg-white text-center shadow-card border-slate-200">
          {/* Top Badge & Icon */}
          <div className="w-16 h-16 rounded-2xl bg-blue-50 text-blue-600 flex items-center justify-center mx-auto mb-5 shadow-sm">
            <CreditCard className="w-8 h-8" />
          </div>

          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-blue-50 text-blue-700 text-xs font-semibold mb-3">
            <span className="w-2 h-2 rounded-full bg-blue-600 animate-pulse" />
            Phase 1 Completed — Phase 2 Ready
          </div>

          <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 mb-3">
            Payment & Checkout Coming Soon
          </h1>

          <p className="text-sm sm:text-base text-slate-600 max-w-lg mx-auto mb-8 leading-relaxed">
            The customer-facing frontend workflow is complete! Payment gateway integration (Stripe / JazzCash / EasyPaisa) and Django REST backend order dispatch are part of the upcoming Phase 2 milestone.
          </p>

          {/* Draft Order Snapshot */}
          <div className="bg-slate-50 rounded-2xl p-6 border border-slate-200/80 text-left mb-8 max-w-xl mx-auto">
            <h3 className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-3">
              Order Draft Ready for Dispatch
            </h3>

            <div className="space-y-2 text-xs sm:text-sm">
              <div className="flex justify-between text-slate-600">
                <span>Draft Reference ID:</span>
                <span className="font-mono font-semibold text-slate-900">{draft.draftId}</span>
              </div>
              <div className="flex justify-between text-slate-600">
                <span>Total Documents:</span>
                <span className="font-semibold text-slate-900">{totals.readyFilesCount}</span>
              </div>
              <div className="flex justify-between text-slate-600">
                <span>Page Impressions:</span>
                <span className="font-semibold text-blue-600">{totals.totalPageImpressions} impressions</span>
              </div>
              <div className="flex justify-between text-slate-600">
                <span>Estimated Paper Sheets:</span>
                <span className="font-semibold text-slate-900">~{totals.totalEstimatedSheets} sheets</span>
              </div>
            </div>
          </div>

          {/* API Backend Simulation Status */}
          {apiFeedback && (
            <div className="max-w-xl mx-auto mb-6 text-left">
              <Alert
                type={apiFeedback.type}
                title={
                  apiFeedback.type === 'success'
                    ? 'Backend Connection Active'
                    : apiFeedback.type === 'error'
                    ? 'Connection Error'
                    : 'Backend Status Notice'
                }
              >
                {apiFeedback.message}
              </Alert>
            </div>
          )}

          {/* Action Buttons */}
          <div className="flex flex-col sm:flex-row items-center justify-center gap-3">
            <Button
              type="button"
              variant="outline"
              size="md"
              icon={<Server className="w-4 h-4 text-slate-500" />}
              isLoading={isSubmitting}
              onClick={handleTestBackendSubmission}
            >
              Test Backend Connection
            </Button>

            <Link to="/review-order">
              <Button variant="secondary" size="md" icon={<ArrowLeft className="w-4 h-4" />}>
                Review Order
              </Button>
            </Link>

            <Button
              type="button"
              variant="ghost"
              size="md"
              icon={<RotateCcw className="w-4 h-4" />}
              onClick={handleStartFresh}
              className="text-slate-600"
            >
              Start New Order
            </Button>
          </div>

          {/* Security & Authenticity Footnote */}
          <div className="mt-10 pt-6 border-t border-slate-100 flex flex-wrap items-center justify-center gap-4 text-xs text-slate-400">
            <span className="flex items-center gap-1.5">
              <ShieldCheck className="w-4 h-4 text-emerald-500" />
              Zero Mock Card Processing
            </span>
            <span>•</span>
            <span className="flex items-center gap-1.5">
              <CheckCircle2 className="w-4 h-4 text-emerald-500" />
              Ready for Django REST API
            </span>
          </div>
        </div>
      </div>
    </div>
  );
};
