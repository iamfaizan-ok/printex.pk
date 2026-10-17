import React from 'react';
import { useLocation, Link } from 'react-router-dom';
import { Check, UploadCloud, Sliders, CheckSquare, CreditCard } from 'lucide-react';
import { usePrintDraft } from '../../hooks/usePrintDraft';

interface StepItem {
  id: number;
  name: string;
  path: string;
  icon: React.ReactNode;
}

const STEPS: StepItem[] = [
  { id: 1, name: 'Upload Files', path: '/upload', icon: <UploadCloud className="w-4 h-4" /> },
  { id: 2, name: 'Print Settings', path: '/print-settings', icon: <Sliders className="w-4 h-4" /> },
  { id: 3, name: 'Review Order', path: '/review-order', icon: <CheckSquare className="w-4 h-4" /> },
  { id: 4, name: 'Payment', path: '/payment-coming-soon', icon: <CreditCard className="w-4 h-4" /> },
];

export const StepIndicator: React.FC = () => {
  const location = useLocation();
  const { canProceedToSettings, canProceedToReview } = usePrintDraft();

  const getCurrentStepIndex = () => {
    switch (location.pathname) {
      case '/upload':
        return 1;
      case '/print-settings':
        return 2;
      case '/review-order':
        return 3;
      case '/payment-coming-soon':
        return 4;
      default:
        return 0;
    }
  };

  const currentStep = getCurrentStepIndex();

  if (currentStep === 0) return null;

  const isStepAccessible = (stepId: number) => {
    if (stepId === 1) return true;
    if (stepId === 2) return canProceedToSettings;
    if (stepId === 3) return canProceedToReview;
    if (stepId === 4) return canProceedToReview;
    return false;
  };

  return (
    <div className="w-full bg-white border-b border-slate-200/80 py-4 px-4 sm:px-6">
      <div className="max-w-4xl mx-auto">
        <nav aria-label="Progress">
          <ol className="flex items-center justify-between relative">
            {STEPS.map((step, index) => {
              const isCompleted = currentStep > step.id;
              const isCurrent = currentStep === step.id;
              const accessible = isStepAccessible(step.id);

              const content = (
                <div className="flex flex-col items-center group relative z-10">
                  <div
                    className={`w-9 h-9 sm:w-10 sm:h-10 rounded-full flex items-center justify-center font-semibold text-xs sm:text-sm transition-all shadow-sm ${
                      isCompleted
                        ? 'bg-blue-600 text-white'
                        : isCurrent
                        ? 'bg-blue-50 text-blue-600 ring-2 ring-blue-600 ring-offset-2'
                        : 'bg-slate-100 text-slate-700'
                    }`}
                  >
                    {isCompleted ? <Check className="w-5 h-5 stroke-[2.5]" /> : step.icon}
                  </div>
                  <span
                    className={`mt-1.5 text-[11px] sm:text-xs font-medium tracking-tight text-center ${
                      isCurrent
                        ? 'text-blue-700 font-semibold'
                        : isCompleted
                        ? 'text-slate-800'
                        : 'text-slate-600'
                    }`}
                  >
                    {step.name}
                  </span>
                </div>
              );

              return (
                <li key={step.name} className="relative flex-1 flex flex-col items-center">
                  {/* Connecting Line */}
                  {index !== 0 && (
                    <div
                      aria-hidden="true"
                      className={`absolute top-4 sm:top-5 -left-1/2 w-full h-[2px] transition-colors -z-0 ${
                        currentStep > index ? 'bg-blue-600' : 'bg-slate-200'
                      }`}
                    />
                  )}

                  {accessible && !isCurrent ? (
                    <Link to={step.path} className="focus-ring rounded-lg">
                      {content}
                    </Link>
                  ) : (
                    <div>{content}</div>
                  )}
                </li>
              );
            })}
          </ol>
        </nav>
      </div>
    </div>
  );
};
