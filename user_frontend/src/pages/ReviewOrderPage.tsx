import React, { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { ArrowLeft, CheckCircle2, ShieldCheck, Printer, RefreshCw } from 'lucide-react';
import { usePrintDraft } from '../hooks/usePrintDraft';
import { OrderFileSummary } from '../components/order/OrderFileSummary';
import { OrderSummary } from '../components/order/OrderSummary';
import { EmptyOrderState } from '../components/order/EmptyOrderState';
import { Button } from '../components/ui/Button';
import { Alert } from '../components/ui/Alert';
import { apiClient } from '../services/apiClient';

export const ReviewOrderPage: React.FC = () => {
  const navigate = useNavigate();
  const { draft, totals, canProceedToReview, clearDraft } = usePrintDraft();
  const [isCashSubmitting, setIsCashSubmitting] = useState(false);
  const [placedOrder, setPlacedOrder] = useState<any | null>(null);
  const [liveStatus, setLiveStatus] = useState<string>('queued');
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const validFiles = draft.files.filter((f) => f.processingStatus === 'ready');

  // Live status polling if order is placed
  useEffect(() => {
    if (!placedOrder?.orderId) return;

    const interval = setInterval(async () => {
      try {
        const res = await fetch(`http://localhost:8000/api/v1/print-jobs/${placedOrder.orderId}/status/`);
        if (res.ok) {
          const data = await res.json();
          const currentStatus = data.data?.status || data.status;
          if (currentStatus) {
            setLiveStatus(currentStatus);
          }
        }
      } catch {
        // silent polling catch
      }
    }, 3000);

    return () => clearInterval(interval);
  }, [placedOrder?.orderId]);

  const handleCashPayment = async () => {
    setIsCashSubmitting(true);
    setErrorMsg(null);

    try {
      const response = await apiClient.submitOrder(draft, {
        paymentMethod: 'cash_on_delivery',
        customerName: 'Customer',
        phone: '0300-0000000',
        deliveryMethod: 'pickup',
      });
      setPlacedOrder(response);
      setLiveStatus(response.status || 'queued');
    } catch (err: unknown) {
      const error = err as { message?: string };
      setErrorMsg(error.message || 'Failed to submit cash print order. Please verify backend is running.');
    } finally {
      setIsCashSubmitting(false);
    }
  };

  const handleStartNewOrder = () => {
    clearDraft();
    navigate('/upload');
  };

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

        {/* Error Alert if any */}
        {errorMsg && (
          <div className="mb-6">
            <Alert type="error" title="Print Submission Error">
              {errorMsg}
            </Alert>
          </div>
        )}

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
              proceedDisabled={!canProceedToReview || Boolean(placedOrder)}
              onProceed={() => navigate('/payment-coming-soon')}
              onCashPayment={handleCashPayment}
              isCashSubmitting={isCashSubmitting}
            />
          </div>
        </div>

        {/* Live Order Confirmation Modal / Card */}
        {placedOrder && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm animate-fade-in">
            <div className="bg-white rounded-3xl p-6 sm:p-8 max-w-lg w-full shadow-2xl border border-slate-100 text-center space-y-5">
              <div className="w-16 h-16 rounded-full bg-emerald-100 text-emerald-600 flex items-center justify-center mx-auto shadow-inner">
                <Printer className="w-8 h-8 animate-bounce" />
              </div>

              <div>
                <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold mb-2 ${
                  liveStatus === 'queued'
                    ? 'bg-amber-50 text-amber-800'
                    : 'bg-emerald-50 text-emerald-700'
                }`}>
                  <span className={`w-2 h-2 rounded-full ${
                    liveStatus === 'queued'
                      ? 'bg-amber-500 animate-ping'
                      : 'bg-emerald-600 animate-pulse'
                  }`} />
                  {liveStatus === 'queued' ? 'Awaiting Admin Print Approval' : 'Printing Authorized'}
                </span>
                <h2 className="text-2xl font-black text-slate-900">
                  {liveStatus === 'queued' ? 'Order Placed (Pending Print)' : 'Print Job Dispatched!'}
                </h2>
                <p className="text-xs sm:text-sm text-slate-500 mt-1">
                  {liveStatus === 'queued'
                    ? 'Your order has reached the admin queue. Please pay cash at the counter — the operator will click Print to begin printing.'
                    : 'Your print order was authorized and sent to the physical printer spooler.'}
                </p>
              </div>

              {/* Order Snapshot Table */}
              <div className="bg-slate-50 rounded-2xl p-4 border border-slate-200/80 text-left space-y-2.5 text-xs sm:text-sm">
                <div className="flex justify-between items-center text-slate-600">
                  <span>Job Number:</span>
                  <span className="font-mono font-bold text-slate-900 text-base">{placedOrder.orderNumber}</span>
                </div>
                <div className="flex justify-between items-center text-slate-600">
                  <span>Payment Mode:</span>
                  <span className="font-semibold text-emerald-700 bg-emerald-100/60 px-2 py-0.5 rounded">
                    Cash Payment
                  </span>
                </div>
                {placedOrder.targetPrinter && (
                  <div className="flex justify-between items-center text-slate-600">
                    <span>Target Printer:</span>
                    <span className="font-semibold text-slate-800 text-xs truncate max-w-[200px]" title={placedOrder.targetPrinter}>
                      {placedOrder.targetPrinter}
                    </span>
                  </div>
                )}
                <div className="flex justify-between items-center text-slate-600">
                  <span>Live Spooler Status:</span>
                  <span className="inline-flex items-center gap-1.5 font-bold text-blue-700 bg-blue-50 px-2 py-0.5 rounded uppercase text-xs">
                    <RefreshCw className="w-3 h-3 animate-spin" />
                    {liveStatus}
                  </span>
                </div>
                <div className="flex justify-between items-center text-slate-600 border-t border-slate-200/80 pt-2">
                  <span className="font-bold text-slate-900">Amount Due:</span>
                  <span className="font-black text-slate-900 text-base">
                    {placedOrder.currency || 'PKR'} {placedOrder.estimatedPrice || totals.totalPageImpressions * 5}
                  </span>
                </div>
              </div>

              {/* Action Buttons */}
              <div className="pt-2 flex flex-col sm:flex-row items-center justify-center gap-3">
                <Button
                  type="button"
                  variant="primary"
                  size="md"
                  className="w-full bg-emerald-600 hover:bg-emerald-700 text-white font-bold"
                  onClick={handleStartNewOrder}
                  icon={<CheckCircle2 className="w-4 h-4" />}
                >
                  Start New Order
                </Button>
                <Button
                  type="button"
                  variant="outline"
                  size="md"
                  className="w-full text-slate-600"
                  onClick={() => setPlacedOrder(null)}
                >
                  Dismiss
                </Button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
