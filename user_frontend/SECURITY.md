# Security Policy & Architecture Guide — PrintX Frontend

## Document Security & Privacy Principles

Customer print jobs often contain confidential, academic, legal, or personal information. PrintX enforces privacy and security-first engineering:

### 1. Client-Side Processing Sandbox
- **No AI Exfiltration**: PDF files are inspected and rendered entirely within the user's browser using client-side WebAssembly / PDF.js workers. Documents are never transmitted to AI models or third-party APIs during Phase 1.
- **In-Memory Storage Only**: Raw PDF binaries and `File` objects remain in browser heap memory during the active session. They are **never** persisted to `localStorage` or unencrypted client databases.
- **Session Storage Metadata**: Only non-sensitive order metadata (e.g., file names, page counts, print preference selections) is cached in `sessionStorage` to preserve user draft state during page navigation.

### 2. File Validation & Sanitization
- **Magic Bytes Verification**: File extension alone is not trusted. The frontend reads the first 5 bytes of every file to enforce the `%PDF-` (`0x25, 0x50, 0x44, 0x46, 0x2D`) signature.
- **Filename Sanitization**: Dangerous characters, path traversal sequences (`../`, `..\`), and non-printable control characters are stripped.
- **Resource Cleanup**: Browser Object URLs (`blob:...`) are explicitly revoked upon file deletion, document replacement, or draft clearing via `URL.revokeObjectURL()` to prevent memory leaks and dangling pointers.

### 3. Content Security Policy (CSP)
The application defines a strict Content Security Policy in `index.html`:
- Scripts are restricted to `'self'`.
- PDF.js web worker execution is scoped to `'self' blob:`.
- External network connections are restricted.
- No `eval` execution is allowed (`isEvalSupported: false` configured in PDF.js loader).

---

## Limitations of Frontend-Only Validation

> ⚠️ **Important Security Notice**: Frontend validation is an ergonomics and performance mechanism, not an absolute security boundary.

In Phase 1:
- A malicious actor can inspect and modify client-side JavaScript execution via browser developer tools.
- Client-side checks cannot protect against sophisticated PDF exploits targeting browser rendering engines without an isolated backend sandbox.

---

## Phase 2 Django Backend Requirements

When the Django REST Framework backend is introduced in Phase 2, the backend **must independently enforce**:

1. **Server-Side File Validation**:
   - Re-verify MIME types using `python-magic` / `libmagic`.
   - Re-check `%PDF-` file headers.
   - Enforce hard size and page count limits on the server before storing.
2. **Malware & Sandbox Scanning**:
   - Run uploaded PDFs through an antivirus scanner (e.g. ClamAV) and verify with a headless PDF parser in an isolated Linux container before queueing for printer agents.
3. **Authentication & Authorization**:
   - Secure Django session/JWT tokens with `HttpOnly`, `SameSite=Lax`, and `Secure` flags.
   - Restrict order retrieval to the authenticating user or authorized print shop operators.
4. **Server-Side Pricing Engine**:
   - Calculate all final prices and sheet counts on the server; never trust client-submitted monetary totals.
5. **Secure Payment Gateways**:
   - Integrate payment processors (Stripe / Local Gateways) using server-side webhook validation and tokenized checkout sessions. Zero credit card numbers or secrets touch PrintX database.
6. **Retention & Deletion Lifecycle**:
   - Automatically purge customer PDF binaries from disk/S3 within a configured retention period (e.g., 24-48 hours after print completion).
