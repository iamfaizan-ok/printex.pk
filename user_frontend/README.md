# PrintX — Customer Frontend (Phase 1)

Modern, secure, and fast customer-facing web application for **PrintX**, an online document printing platform. Built with React, TypeScript (strict mode), Vite, Tailwind CSS, Lucide icons, PDF.js, and Vitest.

---

## 🚀 Key Features

1. **Client-Side PDF Processing & Verification**
   - In-browser validation of file size, mime type, and PDF signature magic bytes (`%PDF-`).
   - Client-side page count extraction using PDF.js without server upload.
   - Interactive, zoomable vector preview with single-page on-demand canvas rendering.
   - Protection against corrupted, password-protected, and oversized files.

2. **Independent Print Settings Per File**
   - Copies selection (1 to 100) with increment/decrement steppers.
   - Paper sizes: **A4**, **A3**, **Letter**, **Legal** with dimensions indicator.
   - Colour modes: **Full Colour** vs **Black & White**.
   - Sides: **Double-Sided (Duplex)** vs **Single-Sided**.
   - Orientation: **Portrait** vs **Landscape**.
   - Page range: **All Pages** or custom comma-separated ranges (e.g., `1-3, 5, 8-10`) with live validation.

3. **Live Calculations & Order Summary**
   - Immediate calculation of requested page impressions (`selected pages × copies`).
   - Accurate physical sheet estimation taking duplex printing into account.
   - Transparent pricing notice without fabricated or hardcoded mock prices.

4. **Robust Workflow & Guarded Navigation**
   - 4-step workflow: `Home → Upload → Print Settings → Review Order → Payment Placeholder`.
   - In-memory state management with `PrintDraftContext` and `sessionStorage` metadata synchronization.
   - Object URLs and PDF resources automatically revoked to prevent memory leaks.

---

## 🛠️ Technology Stack

- **Framework**: React 18
- **Language**: TypeScript (Strict type checking)
- **Bundler & Dev Server**: Vite 5
- **Styling**: Tailwind CSS with custom design tokens
- **PDF Engine**: PDF.js (`pdfjs-dist`)
- **Routing**: React Router 6 (Data Router)
- **Icons**: Lucide React
- **Testing**: Vitest + React Testing Library + JSDOM

---

## 📂 Project Structure

```
user_frontend/
├── public/
│   └── favicon.svg
├── src/
│   ├── app/
│   │   ├── App.tsx             # Root application component
│   │   ├── router.tsx          # Route definitions & guards
│   │   └── providers.tsx       # Context providers wrapper
│   ├── pages/
│   │   ├── HomePage.tsx        # Landing & hero page
│   │   ├── UploadPage.tsx      # Step 1: Drag-and-drop PDF upload
│   │   ├── PrintSettingsPage.tsx # Step 2: Independent settings & preview
│   │   ├── ReviewOrderPage.tsx # Step 3: Order impression totals review
│   │   ├── PaymentComingSoonPage.tsx # Step 4: Phase 2 payment placeholder
│   │   └── NotFoundPage.tsx    # 404 handler
│   ├── components/
│   │   ├── layout/             # Header, Footer, MainLayout, StepIndicator
│   │   ├── upload/             # FileDropzone, FilePicker, UploadedFileCard, FileList
│   │   ├── pdf/                # PDFPreview, PDFPageNavigation, PDFLoadingState
│   │   ├── printing/           # PrintSettingsForm, CopiesInput, PaperSizeSelect, etc.
│   │   ├── order/              # OrderSummary, OrderFileSummary, EmptyOrderState
│   │   └── ui/                 # Button, Input, Select, Modal, Spinner, Alert, ErrorBoundary
│   ├── context/
│   │   └── PrintDraftContext.tsx # Central draft reducer & state
│   ├── hooks/
│   │   ├── usePrintDraft.ts    # Access print draft state
│   │   ├── usePDFDocument.ts   # Safe PDF.js lifecycle & cleanup
│   │   └── useObjectURL.ts     # Safe Blob URL management
│   ├── services/
│   │   ├── apiClient.ts        # Typed client ready for Django backend
│   │   ├── pdfService.ts       # PDF.js inspection & canvas rendering
│   │   └── storageService.ts   # Session storage draft metadata sync
│   ├── types/                  # Typed models: printFile, printSettings, printDraft
│   ├── utils/                  # fileValidation, pageRange, printCalculations, formatFileSize, generateId
│   ├── config/                 # appConfig, printDefaults
│   ├── styles/                 # globals.css, components.css, index.css
│   └── test/
│       └── setup.ts            # Vitest environment setup
├── tests/                      # Automated unit and component tests
├── .env.example
├── index.html
├── package.json
├── tsconfig.json
├── vite.config.ts
├── tailwind.config.js
└── SECURITY.md
```

---

## 🏃 Getting Started

### 1. Install Dependencies
```bash
npm install
```

### 2. Start Development Server
```bash
npm run dev
```
Open `http://localhost:3000` in your browser.

### 3. Run Automated Tests
```bash
npm run test
```

### 4. Build for Production
```bash
npm run build
```

---

## 🔌 Connecting to Django REST Framework (Phase 2)

In Phase 1, the frontend works in standalone client-side mode. To connect to the upcoming Django backend in Phase 2:

1. Configure `.env`:
   ```bash
   VITE_API_BASE_URL=http://localhost:8000/api/v1
   ```
2. The `apiClient.ts` module in `src/services/apiClient.ts` contains typed interfaces (`CreateOrderRequest`, `CreateOrderResponse`) ready to dispatch JSON payloads to Django endpoints:
   - `POST /api/v1/orders/` — submits draft items and print settings
   - `GET /api/v1/health/` — checks backend service status
