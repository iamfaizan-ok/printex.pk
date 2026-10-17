# PrintX — User Frontend API Specification & Backend Contract

This document provides the complete API contract between the **User Frontend** (`user_frontend`) and the **Django REST Framework Backend** (`backend_all`).

---

## 🌐 Network & Architecture Setup

| Parameter | Value |
|---|---|
| **Frontend URL / Origin** | `http://localhost:3000` (or `http://localhost:5173`) |
| **Backend API Base URL** | `http://localhost:8000/api/v1` |
| **Frontend API Module** | `user_frontend/src/api/userApis.ts` |
| **Authentication Header (optional)** | `Authorization: Bearer <token>` |
| **Content Types** | `application/json` (except document upload which uses `multipart/form-data`) |

### CORS Configuration Required in Django (`settings.py`):
```python
INSTALLED_APPS = [
    # ...
    'corsheaders',
    'rest_framework',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware', # Put near top
    'django.middleware.common.CommonMiddleware',
    # ...
]

CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:5173",
    "http://127.0.0.1:3000",
]

CORS_ALLOW_CREDENTIALS = True
```

---

## 📡 Endpoints Summary

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/v1/health/` | Server health check |
| `POST` | `/api/v1/documents/upload/` | Multipart file upload (PDF/Images) |
| `POST` | `/api/v1/pricing/calculate/` | Live print order price calculation |
| `POST` | `/api/v1/orders/create/` | Place a new customer print order |
| `GET` | `/api/v1/orders/:orderId/` | Get order details & status |
| `GET` | `/api/v1/orders/track/?number=...` | Public order tracking by order number |
| `POST` | `/api/v1/payments/create-intent/` | Initialize payment intent / checkout |
| `POST` | `/api/v1/payments/verify/` | Verify payment status from gateway |
| `POST` | `/api/v1/orders/:orderId/cancel/` | Cancel pending order |

---

## 📋 Endpoint Details & JSON Schemas

### 1. Health Check
- **Endpoint**: `GET /api/v1/health/`
- **Response `200 OK`**:
```json
{
  "status": "online",
  "service": "printx-backend",
  "version": "1.0.0"
}
```

---

### 2. Document Upload
- **Endpoint**: `POST /api/v1/documents/upload/`
- **Content-Type**: `multipart/form-data`
- **Request Form Data**:
  - `file`: Raw binary file (PDF, PNG, JPG, WEBP)
  - `original_name`: `string`
  - `file_size`: `number` (bytes)
- **Response `201 Created`**:
```json
{
  "documentId": "doc_8f93a1bc",
  "originalFileName": "Assignment_1.pdf",
  "fileSizeBytes": 210432,
  "fileUrl": "http://localhost:8000/media/documents/2026/10/Assignment_1.pdf",
  "pageCount": 5,
  "fileType": "pdf",
  "mimeType": "application/pdf",
  "uploadedAt": "2026-10-18T00:00:00Z"
}
```

---

### 3. Price Quote Calculation
- **Endpoint**: `POST /api/v1/pricing/calculate/`
- **Content-Type**: `application/json`
- **Request Body**:
```json
{
  "items": [
    {
      "fileName": "Document1.pdf",
      "pageCount": 10,
      "fileType": "pdf",
      "copies": 2,
      "paperSize": "A4",
      "colourMode": "bw",
      "orientation": "portrait",
      "sides": "double",
      "pageRange": "all"
    }
  ],
  "deliveryMethod": "pickup"
}
```
- **Response `200 OK`**:
```json
{
  "currency": "PKR",
  "subtotal": 120.00,
  "deliveryFee": 0.00,
  "tax": 0.00,
  "totalAmount": 120.00,
  "items": [
    {
      "fileName": "Document1.pdf",
      "pageImpressions": 20,
      "estimatedSheets": 10,
      "unitPricePerImpression": 6.00,
      "paperPrice": 60.00,
      "itemSubtotal": 120.00
    }
  ]
}
```

---

### 4. Create Order
- **Endpoint**: `POST /api/v1/orders/create/`
- **Content-Type**: `application/json`
- **Request Body**:
```json
{
  "draftId": "draft_28a01",
  "customer": {
    "fullName": "Muhammad Ali",
    "email": "ali@example.com",
    "phone": "03001234567",
    "city": "Lahore",
    "shippingAddress": "Gulberg III, Lahore",
    "notes": "Please staple on top-left"
  },
  "deliveryMethod": "standard_delivery",
  "items": [
    {
      "documentId": "doc_8f93a1bc",
      "fileName": "Thesis.pdf",
      "fileSizeBytes": 1048576,
      "pageCount": 50,
      "fileType": "pdf",
      "copies": 1,
      "paperSize": "A4",
      "colourMode": "bw",
      "orientation": "portrait",
      "sides": "double",
      "pageRange": "all"
    }
  ]
}
```
- **Response `201 Created`**:
```json
{
  "orderId": "ord_719a0b2",
  "orderNumber": "PRX-2026-00101",
  "status": "pending_payment",
  "createdAt": "2026-10-18T00:50:00Z",
  "updatedAt": "2026-10-18T00:50:00Z",
  "totalImpressions": 50,
  "totalSheets": 25,
  "pricing": {
    "currency": "PKR",
    "subtotal": 300.00,
    "deliveryFee": 150.00,
    "tax": 0.00,
    "totalAmount": 450.00,
    "items": []
  },
  "paymentStatus": "unpaid"
}
```

---

### 5. Order Tracking & Status
- **Endpoint**: `GET /api/v1/orders/:orderId/` OR `GET /api/v1/orders/track/?number=PRX-2026-00101`
- **Response `200 OK`**:
```json
{
  "orderId": "ord_719a0b2",
  "orderNumber": "PRX-2026-00101",
  "status": "printing",
  "paymentStatus": "paid",
  "totalImpressions": 50,
  "totalSheets": 25,
  "trackingNumber": "TCS-99182371",
  "createdAt": "2026-10-18T00:50:00Z",
  "updatedAt": "2026-10-18T01:10:00Z"
}
```

---

### 6. Payment Intent & Checkout
- **Endpoint**: `POST /api/v1/payments/create-intent/`
- **Request Body**:
```json
{
  "orderId": "ord_719a0b2",
  "paymentMethod": "jazzcash",
  "returnUrl": "http://localhost:3000/orders/ord_719a0b2/success"
}
```
- **Response `200 OK`**:
```json
{
  "orderId": "ord_719a0b2",
  "paymentId": "pay_98b1a3",
  "paymentMethod": "jazzcash",
  "checkoutUrl": "https://sandbox.jazzcash.com.pk/CustomerPortal/transactionmanagement/merchantform/",
  "amount": 450.00,
  "currency": "PKR",
  "status": "requires_action"
}
```

---

## ⚠️ Standard Error Formats (DRF Compatible)

The frontend automatically extracts error messages from any of these Django REST formats:

### Simple Error
```json
{
  "detail": "Invalid order reference."
}
```

### Validation Error
```json
{
  "email": ["Enter a valid email address."],
  "phone": ["Phone number must be at least 10 digits."]
}
```

### Non-field Error
```json
{
  "non_field_errors": ["The requested paper size is currently out of stock."]
}
```
