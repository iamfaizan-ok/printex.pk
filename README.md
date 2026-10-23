# PrintX (printex.pk) — Online Document Printing Platform

PrintX is an online document printing platform built to streamline the process of uploading documents, configuring print preferences, calculating impressions, and sending orders directly to local print shops.

---

## 📁 Repository Structure

```
printex.pk/
│
├── user_frontend/       # Phase 1: Customer-facing Web Application (Completed)
│   ├── src/             # React 18, TypeScript, Tailwind CSS, PDF.js, Vite
│   ├── tests/           # Vitest + React Testing Library (28 automated tests)
│   └── README.md        # Detailed frontend documentation
│
├── backend_all/         # Phase 2: Django REST Framework API (Upcoming)
│   └── README.md        # Backend architecture & integration roadmap
│
└── admin_side/          # Phase 3: Print Shop & Desktop Print Agent (Upcoming)
    └── README.md        # Print agent & shop order management portal
```

---

## ⚡ Quick Start (Run Locally)

You can run both the Frontend and Backend concurrently with the single launcher script:

```bash
./start.sh
```

Or run individual services:

```bash
# Run only Backend (Django REST API + Admin Portal)
./start.sh backend

# Run only Frontend (Customer Portal)
./start.sh frontend
```

### Local URLs & Credentials

| Service | Local URL | Notes / Credentials |
|---|---|---|
| **Customer Web Portal** | [http://localhost:3000](http://localhost:3000) | Vite + React frontend |
| **Admin Operations Portal** | [http://localhost:8000/admin-panel/login.html](http://localhost:8000/admin-panel/login.html) | `admin` / `admin123` |
| **Interactive API Docs (Swagger)** | [http://localhost:8000/api/docs/](http://localhost:8000/api/docs/) | OpenAPI schema & test UI |
| **Django Admin Site** | [http://localhost:8000/admin/](http://localhost:8000/admin/) | `admin` / `admin123` |
| **API Health Check** | [http://localhost:8000/api/v1/health/](http://localhost:8000/api/v1/health/) | JSON health status |

---

## 🚀 Module Overview

### 1. `user_frontend` (Customer Portal — Phase 1 Completed)
A high-performance, accessible, and responsive web application for customers.
- **Client-Side Document Verification**: Parses and validates PDF magic bytes (`%PDF-`) and supports image formats (PNG, JPG, WEBP, SVG) with zero external CDN dependencies.
- **Independent File Print Settings**: Allows setting copies, paper sizes (A4, A3, Letter, Legal), color modes (Full Colour vs Black & White), duplex/single-sided, and custom page ranges per document.
- **Live Calculations**: Immediate calculation of requested page impressions and estimated physical sheets.
- **Interactive Previews**: Single-page vector PDF rendering with zoom controls and image preview.
- **Privacy First**: Files are inspected and rendered entirely in the browser heap memory with automatic resource disposal.
- **Quality Assurance**: 28 automated tests with 100% pass rate.

#### Manual Frontend Start
```bash
cd user_frontend
npm install
npm run dev
```
Runs at `http://localhost:3000`.

---

### 2. `backend_all` (Django REST API — Phase 2)
- Server-side document storage, security sanitization, and virus scanning.
- Dynamic pricing calculation engine.
- Order lifecycle management and webhook integration for payment gateways.

### 3. `admin_side` (Shop & Print Agent — Phase 3)
- Shop operator order queue and printer management.
- Desktop print agent for automated job spooling.

---

## 🔒 Security
- Documents are never transmitted to unauthorized third parties or AI models.
- Object URLs are safely created and revoked via browser garbage collection.
- Frontend includes Content Security Policy (CSP) guidelines.
- See `user_frontend/SECURITY.md` for complete security architecture.

---

## 📄 License
All rights reserved © PrintX Technologies.
