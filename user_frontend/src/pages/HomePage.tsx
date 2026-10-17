import React from 'react';
import { Link } from 'react-router-dom';
import {
  Printer,
  UploadCloud,
  Sliders,
  CheckCircle2,
  ShieldCheck,
  Zap,
  Layers,
  ArrowRight,
  FileText,
} from 'lucide-react';
import { Button } from '../components/ui/Button';
import { usePrintDraft } from '../hooks/usePrintDraft';

export const HomePage: React.FC = () => {
  const { draft } = usePrintDraft();
  const fileCount = draft.files.length;

  return (
    <div className="flex-1 flex flex-col">
      {/* Active Draft Banner if user has files in progress */}
      {fileCount > 0 && (
        <div className="bg-blue-600 text-white py-3 px-4 sm:px-6">
          <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-3 text-xs sm:text-sm">
            <div className="flex items-center gap-2">
              <FileText className="w-4 h-4 text-blue-200" />
              <span>
                You have an ongoing print draft with <strong>{fileCount} document{fileCount === 1 ? '' : 's'}</strong>.
              </span>
            </div>
            <Link to="/upload">
              <span className="underline font-semibold hover:text-blue-100 flex items-center gap-1">
                Resume Your Draft <ArrowRight className="w-3.5 h-3.5" />
              </span>
            </Link>
          </div>
        </div>
      )}

      {/* Hero Section */}
      <section className="relative overflow-hidden bg-white border-b border-slate-200 py-16 sm:py-24">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="max-w-3xl mx-auto text-center space-y-6">
            <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-blue-50 border border-blue-200/60 text-blue-700 text-xs font-semibold tracking-wide uppercase">
              <Zap className="w-3.5 h-3.5" />
              Online Document Printing Platform
            </div>

            <h1 className="text-4xl sm:text-5xl lg:text-6xl font-extrabold text-slate-900 tracking-tight leading-[1.15]">
              Document printing made <span className="text-blue-600">simple & fast</span>
            </h1>

            <p className="text-base sm:text-lg text-slate-600 leading-relaxed max-w-2xl mx-auto">
              Upload your PDF documents and photos, customize paper sizes, color modes, and page ranges per file, and review accurate impressions with instant previews.
            </p>

            <div className="flex flex-col sm:flex-row items-center justify-center gap-3 pt-4">
              <Link to="/upload" className="w-full sm:w-auto">
                <Button
                  variant="primary"
                  size="lg"
                  className="w-full sm:w-auto font-semibold px-8"
                  icon={<UploadCloud className="w-5 h-5" />}
                >
                  Upload Documents to Print
                </Button>
              </Link>

              {fileCount > 0 && (
                <Link to="/print-settings" className="w-full sm:w-auto">
                  <Button variant="outline" size="lg" className="w-full sm:w-auto">
                    View Print Settings
                  </Button>
                </Link>
              )}
            </div>

            {/* Quick Guarantees */}
            <div className="pt-8 flex flex-wrap items-center justify-center gap-6 text-xs text-slate-500 font-medium">
              <div className="flex items-center gap-1.5">
                <CheckCircle2 className="w-4 h-4 text-emerald-500" />
                <span>Instant In-Browser PDF Inspection</span>
              </div>
              <div className="flex items-center gap-1.5">
                <CheckCircle2 className="w-4 h-4 text-emerald-500" />
                <span>Independent Settings Per File</span>
              </div>
              <div className="flex items-center gap-1.5">
                <CheckCircle2 className="w-4 h-4 text-emerald-500" />
                <span>Client-Side Document Privacy</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* How it Works Section */}
      <section className="py-16 bg-slate-50 border-b border-slate-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center max-w-xl mx-auto mb-12">
            <h2 className="text-2xl sm:text-3xl font-bold text-slate-900">How PrintX Works</h2>
            <p className="text-sm text-slate-500 mt-2">
              Three transparent steps from your digital file to fresh prints.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            <div className="card-base p-6 bg-white relative">
              <div className="w-12 h-12 rounded-xl bg-blue-50 text-blue-600 flex items-center justify-center font-bold text-lg mb-4">
                1
              </div>
              <h3 className="text-base font-bold text-slate-900 mb-2">Upload Your PDFs</h3>
              <p className="text-xs sm:text-sm text-slate-600 leading-relaxed">
                Drag and drop single or multiple PDF documents. Our client-side engine validates file signatures and extracts actual page counts automatically.
              </p>
            </div>

            <div className="card-base p-6 bg-white relative">
              <div className="w-12 h-12 rounded-xl bg-blue-50 text-blue-600 flex items-center justify-center font-bold text-lg mb-4">
                2
              </div>
              <h3 className="text-base font-bold text-slate-900 mb-2">Customize Preferences</h3>
              <p className="text-xs sm:text-sm text-slate-600 leading-relaxed">
                Configure copies, paper size (A4, A3, Letter, Legal), Color vs Black & White, duplex sheets, and specific page ranges independently for each document.
              </p>
            </div>

            <div className="card-base p-6 bg-white relative">
              <div className="w-12 h-12 rounded-xl bg-blue-50 text-blue-600 flex items-center justify-center font-bold text-lg mb-4">
                3
              </div>
              <h3 className="text-base font-bold text-slate-900 mb-2">Review & Submit</h3>
              <p className="text-xs sm:text-sm text-slate-600 leading-relaxed">
                Verify calculated page impressions and physical paper requirements with live totals before final submission.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Feature Highlights Grid */}
      <section className="py-16 bg-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
            <div className="flex gap-4 items-start">
              <div className="p-3 rounded-xl bg-blue-50 text-blue-600 flex-shrink-0">
                <Sliders className="w-6 h-6" />
              </div>
              <div>
                <h4 className="text-sm font-bold text-slate-900 mb-1">Independent Settings</h4>
                <p className="text-xs text-slate-600 leading-relaxed">
                  Need Document A in colour on A3 and Document B in B&W duplex on A4? Customize each file without interfering with others.
                </p>
              </div>
            </div>

            <div className="flex gap-4 items-start">
              <div className="p-3 rounded-xl bg-blue-50 text-blue-600 flex-shrink-0">
                <ShieldCheck className="w-6 h-6" />
              </div>
              <div>
                <h4 className="text-sm font-bold text-slate-900 mb-1">Document Security & Privacy</h4>
                <p className="text-xs text-slate-600 leading-relaxed">
                  Validation, page parsing, and preview rendering occur entirely in your local browser sandbox. No file data is leaked to AI models.
                </p>
              </div>
            </div>

            <div className="flex gap-4 items-start">
              <div className="p-3 rounded-xl bg-blue-50 text-blue-600 flex-shrink-0">
                <Layers className="w-6 h-6" />
              </div>
              <div>
                <h4 className="text-sm font-bold text-slate-900 mb-1">Live Impression Calculations</h4>
                <p className="text-xs text-slate-600 leading-relaxed">
                  See exact requested page impressions and estimated physical paper sheets calculated dynamically as you adjust settings.
                </p>
              </div>
            </div>
          </div>

          {/* Bottom CTA Box */}
          <div className="mt-16 bg-slate-900 text-white rounded-2xl p-8 sm:p-12 text-center flex flex-col items-center justify-center space-y-4">
            <Printer className="w-10 h-10 text-blue-400" />
            <h3 className="text-2xl sm:text-3xl font-bold">Ready to print your documents?</h3>
            <p className="text-sm text-slate-300 max-w-md">
              Start by uploading your PDF files. Fast, secure, and hassle-free.
            </p>
            <Link to="/upload" className="pt-2">
              <Button variant="primary" size="lg" className="font-semibold px-8">
                Start Printing Now
              </Button>
            </Link>
          </div>
        </div>
      </section>
    </div>
  );
};
