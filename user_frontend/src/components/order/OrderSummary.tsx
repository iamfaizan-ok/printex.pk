import React from 'react';
import { Link } from 'react-router-dom';
import { Info, ArrowRight, ArrowLeft, Printer } from 'lucide-react';
import { OverallOrderCalculation } from '../../utils/printCalculations';
import { Button } from '../ui/Button';

export interface OrderSummaryProps {
  totals: OverallOrderCalculation;
  onProceed?: () => void;
  proceedDisabled?: boolean;
}

export const OrderSummary: React.FC<OrderSummaryProps> = ({
  totals,
  onProceed,
  proceedDisabled = false,
}) => {
  return (
    <div className="card-base p-6 bg-white space-y-6 shadow-subtle border-slate-200">
      <div>
        <h3 className="text-base font-bold text-slate-900">Order Totals</h3>
        <p className="text-xs text-slate-500 mt-0.5">Calculated based on your selected print preferences.</p>
      </div>

      {/* Metrics List */}
      <div className="space-y-3 border-t border-b border-slate-100 py-4 text-sm">
        <div className="flex justify-between items-center text-slate-600">
          <span>Total Documents</span>
          <span className="font-semibold text-slate-900">{totals.readyFilesCount}</span>
        </div>

        <div className="flex justify-between items-center text-slate-600">
          <span>Total Page Impressions</span>
          <span className="font-bold text-slate-900 text-base">{totals.totalPageImpressions}</span>
        </div>

        <div className="flex justify-between items-center text-slate-600">
          <span>Estimated Physical Sheets</span>
          <span className="font-semibold text-slate-900">~{totals.totalEstimatedSheets} sheets</span>
        </div>

        <div className="pt-2 border-t border-slate-100 flex justify-between items-center">
          <span className="font-bold text-slate-900">Calculated Price</span>
          <span className="badge-slate font-semibold text-xs">Calculated at Checkout</span>
        </div>
      </div>

      {/* Pricing Policy Disclaimer */}
      <div className="bg-slate-50 rounded-xl p-3.5 border border-slate-200/70 text-xs text-slate-600 flex items-start gap-2.5">
        <Info className="w-4 h-4 text-slate-500 flex-shrink-0 mt-0.5" />
        <p className="leading-relaxed">
          <strong className="text-slate-800">Print Pricing Notice:</strong> Document rates are calculated dynamically by the print facility based on paper stock, color mode, and volume once the backend pricing system is active.
        </p>
      </div>

      {/* Action Buttons */}
      <div className="space-y-2 pt-2">
        {onProceed ? (
          <Button
            type="button"
            variant="primary"
            size="lg"
            className="w-full"
            disabled={proceedDisabled}
            onClick={onProceed}
            icon={<ArrowRight className="w-4 h-4" />}
          >
            Continue to Payment
          </Button>
        ) : (
          <Link to="/payment-coming-soon" className="block w-full">
            <Button
              type="button"
              variant="primary"
              size="lg"
              className="w-full"
              disabled={proceedDisabled}
              icon={<ArrowRight className="w-4 h-4" />}
            >
              Continue to Payment
            </Button>
          </Link>
        )}

        <Link to="/print-settings" className="block w-full">
          <Button
            type="button"
            variant="ghost"
            size="md"
            className="w-full text-slate-600"
            icon={<ArrowLeft className="w-4 h-4" />}
          >
            Back to Settings
          </Button>
        </Link>
      </div>

      <div className="flex items-center justify-center gap-1.5 text-[11px] text-slate-400">
        <Printer className="w-3.5 h-3.5" />
        <span>PrintX Fast Fulfillment</span>
      </div>
    </div>
  );
};
