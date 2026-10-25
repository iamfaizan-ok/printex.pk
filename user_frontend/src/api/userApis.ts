import { APP_CONFIG } from '../config/appConfig';
import { PrintDraft } from '../types/printDraft';

// ============================================================================
// TYPES & SCHEMAS FOR DJANGO REST FRAMEWORK INTEGRATION
// ============================================================================

export interface ApiResponse<T = unknown> {
  success: boolean;
  data?: T;
  message?: string;
  errors?: Record<string, string[]>;
}

export interface ApiDocumentUploadResponse {
  documentId: string;
  originalFileName: string;
  fileSizeBytes: number;
  fileUrl: string;
  pageCount: number;
  fileType: 'pdf' | 'image';
  mimeType: string;
  uploadedAt: string;
}

export interface ApiFileSettingItem {
  documentId?: string;
  fileName: string;
  fileSizeBytes: number;
  pageCount: number;
  fileType: 'pdf' | 'image';
  copies: number;
  paperSize: 'A4' | 'A3' | 'Letter' | 'Legal';
  colourMode: 'colour' | 'bw';
  orientation: 'portrait' | 'landscape';
  sides: 'single' | 'double';
  pageRange: string;
}

export interface ApiPricingRequest {
  items: ApiFileSettingItem[];
  deliveryMethod?: 'pickup' | 'standard_delivery' | 'express_delivery';
  deliveryAddress?: {
    city: string;
    addressLine: string;
    postalCode?: string;
  };
}

export interface ApiPricingItemBreakdown {
  fileName: string;
  pageImpressions: number;
  estimatedSheets: number;
  unitPricePerImpression: number;
  paperPrice: number;
  itemSubtotal: number;
}

export interface ApiPricingResponse {
  currency: string; // e.g. "PKR"
  subtotal: number;
  deliveryFee: number;
  tax: number;
  totalAmount: number;
  items: ApiPricingItemBreakdown[];
}

export interface ApiCustomerInfo {
  fullName: string;
  email: string;
  phone: string;
  city?: string;
  shippingAddress?: string;
  notes?: string;
}

export interface ApiCreateOrderRequest {
  draftId: string;
  customer: ApiCustomerInfo;
  items: ApiFileSettingItem[];
  deliveryMethod: 'pickup' | 'standard_delivery' | 'express_delivery';
}

export type OrderStatus =
  | 'pending_payment'
  | 'payment_confirmed'
  | 'processing'
  | 'printing'
  | 'ready_for_pickup'
  | 'out_for_delivery'
  | 'completed'
  | 'cancelled';

export interface ApiOrderDetailsResponse {
  orderId: string;
  orderNumber: string; // e.g. "PRX-2026-00892"
  status: OrderStatus;
  createdAt: string;
  updatedAt: string;
  customer: ApiCustomerInfo;
  totalImpressions: number;
  totalSheets: number;
  pricing: ApiPricingResponse;
  paymentStatus: 'unpaid' | 'paid' | 'refunded';
  trackingNumber?: string;
}

export interface ApiPaymentIntentRequest {
  orderId: string;
  paymentMethod: 'stripe' | 'jazzcash' | 'easypaisa' | 'bank_transfer' | 'cash_on_delivery';
  returnUrl?: string;
}

export interface ApiPaymentIntentResponse {
  orderId: string;
  paymentId: string;
  paymentMethod: string;
  checkoutUrl?: string; // Redirect URL for JazzCash / EasyPaisa / Stripe Checkout
  clientSecret?: string; // For Stripe Elements
  amount: number;
  currency: string;
  status: 'requires_action' | 'processing' | 'succeeded';
}

// ============================================================================
// BASE HTTP CLIENT & HELPER
// ============================================================================

class ApiError extends Error {
  public status: number;
  public errors?: Record<string, string[]>;

  constructor(message: string, status: number, errors?: Record<string, string[]>) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.errors = errors;
  }
}

/**
 * Normalizes and reads API Base URL from environment variables.
 * Default fallback is http://localhost:8000/api/v1 for local Django dev.
 */
export function getApiBaseUrl(): string {
  const envUrl = APP_CONFIG.apiBaseUrl;
  if (envUrl && envUrl.trim().length > 0) {
    return envUrl.replace(/\/+$/, '');
  }
  return 'http://localhost:8000/api/v1';
}

/**
 * Checks whether backend is configured.
 */
export function isBackendConnected(): boolean {
  return Boolean(APP_CONFIG.apiBaseUrl && APP_CONFIG.apiBaseUrl.trim().length > 0);
}

/**
 * Core fetch helper that manages JSON serialization, headers and Django error formats.
 */
async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const baseUrl = getApiBaseUrl();
  const url = `${baseUrl}${endpoint.startsWith('/') ? '' : '/'}${endpoint}`;

  const defaultHeaders: Record<string, string> = {
    Accept: 'application/json',
  };

  // Only set Content-Type if body is not FormData
  if (!(options.body instanceof FormData)) {
    defaultHeaders['Content-Type'] = 'application/json';
  }

  const config: RequestInit = {
    ...options,
    headers: {
      ...defaultHeaders,
      ...(options.headers || {}),
    },
  };

  let response: Response;
  try {
    response = await fetch(url, config);
  } catch (networkError: unknown) {
    const err = networkError as Error;
    throw new ApiError(
      `Network connection failed: Unable to connect to backend server at ${baseUrl}. (${err.message})`,
      0
    );
  }

  // Parse response
  let json: Record<string, unknown> = {};
  try {
    json = await response.json();
  } catch {
    json = {};
  }

  if (!response.ok) {
    // Parse Django REST Framework error formats (e.g. { detail: "..." }, { non_field_errors: [...] }, or field errors)
    let errorMessage = (json.message || json.detail || json.error) as string;

    if (!errorMessage) {
      if (json.non_field_errors && Array.isArray(json.non_field_errors)) {
        errorMessage = json.non_field_errors.join(', ');
      } else {
        const firstKey = Object.keys(json)[0];
        if (firstKey && Array.isArray(json[firstKey])) {
          errorMessage = `${firstKey}: ${(json[firstKey] as string[]).join(', ')}`;
        } else {
          errorMessage = `Server responded with status code ${response.status}.`;
        }
      }
    }

    throw new ApiError(
      errorMessage,
      response.status,
      json as Record<string, string[]>
    );
  }

  return json as T;
}

// ============================================================================
// ALL USER FRONTEND APIS
// ============================================================================

export const userApis = {
  /**
   * 1. Health check & Server Status
   * GET /health/
   */
  async checkHealth(): Promise<{ status: string; service: string; version: string }> {
    return request('/health/', { method: 'GET' });
  },

  /**
   * 2. Upload Document to Backend Storage (PDF or Image)
   * POST /documents/upload/
   * Sends multipart/form-data with raw file binary to Django
   */
  async uploadDocument(
    file: File,
    onProgress?: (percent: number) => void
  ): Promise<ApiDocumentUploadResponse> {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('original_name', file.name);
    formData.append('file_size', file.size.toString());
    const savedShopId = typeof window !== 'undefined' ? localStorage.getItem('printx_shop_id') : null;
    if (savedShopId) {
      formData.append('shop_id', savedShopId);
    }

    // If XMLHttpRequest is preferred for upload progress
    if (onProgress && typeof XMLHttpRequest !== 'undefined') {
      return new Promise((resolve, reject) => {
        const xhr = new XMLHttpRequest();
        xhr.open('POST', `${getApiBaseUrl()}/documents/upload/`);
        xhr.setRequestHeader('Accept', 'application/json');

        xhr.upload.onprogress = (e) => {
          if (e.lengthComputable) {
            const percent = Math.round((e.loaded / e.total) * 100);
            onProgress(percent);
          }
        };

        xhr.onload = () => {
          if (xhr.status >= 200 && xhr.status < 300) {
            try {
              resolve(JSON.parse(xhr.responseText));
            } catch {
              reject(new ApiError('Failed to parse upload response.', xhr.status));
            }
          } else {
            reject(new ApiError(`Upload failed with status ${xhr.status}`, xhr.status));
          }
        };

        xhr.onerror = () => {
          reject(new ApiError('Network error occurred during document upload.', 0));
        };

        xhr.send(formData);
      });
    }

    return request<ApiDocumentUploadResponse>('/documents/upload/', {
      method: 'POST',
      body: formData,
    });
  },

  /**
   * 3. Request Live Server-Side Price Calculation
   * POST /pricing/calculate/
   * Sends document print configurations to get accurate price breakdown from Django pricing engine
   */
  async calculatePricing(pricingRequest: ApiPricingRequest): Promise<ApiPricingResponse> {
    return request<ApiPricingResponse>('/pricing/calculate/', {
      method: 'POST',
      body: JSON.stringify(pricingRequest),
    });
  },

  /**
   * 4. Submit Complete Print Order from Draft
   * POST /orders/create/
   */
  async createOrder(orderData: ApiCreateOrderRequest & { shop_id?: string }): Promise<ApiOrderDetailsResponse> {
    const savedShopId = typeof window !== 'undefined' ? localStorage.getItem('printx_shop_id') : null;
    const payload = {
      ...orderData,
      ...(savedShopId ? { shop_id: savedShopId } : {}),
    };
    return request<ApiOrderDetailsResponse>('/orders/create/', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  /**
   * 5. Helper: Submit directly from frontend PrintDraftContext state
   */
  async submitDraftAsOrder(
    draft: PrintDraft,
    customer: ApiCustomerInfo,
    deliveryMethod: 'pickup' | 'standard_delivery' | 'express_delivery' = 'pickup'
  ): Promise<ApiOrderDetailsResponse> {
    const payload: ApiCreateOrderRequest = {
      draftId: draft.draftId,
      customer,
      deliveryMethod,
      items: draft.files
        .filter((f) => f.processingStatus === 'ready')
        .map((f) => ({
          documentId: f.fileId,
          fileName: f.originalFileName,
          fileSizeBytes: f.fileSize,
          pageCount: f.pageCount,
          fileType: f.fileType || 'pdf',
          copies: f.printSettings.copies,
          paperSize: f.printSettings.paperSize,
          colourMode: f.printSettings.colourMode,
          orientation: f.printSettings.orientation,
          sides: f.printSettings.sides,
          pageRange: f.printSettings.pageRange,
        })),
    };

    return this.createOrder(payload);
  },

  /**
   * 6. Get Order Details & Live Status
   * GET /orders/:orderId/
   */
  async getOrderDetails(orderId: string): Promise<ApiOrderDetailsResponse> {
    return request<ApiOrderDetailsResponse>(`/orders/${encodeURIComponent(orderId)}/`, {
      method: 'GET',
    });
  },

  /**
   * 7. Track Order by Order Number (Public Tracking)
   * GET /orders/track/?number=PRX-XXXX
   */
  async trackOrderByNumber(orderNumber: string): Promise<ApiOrderDetailsResponse> {
    return request<ApiOrderDetailsResponse>(
      `/orders/track/?number=${encodeURIComponent(orderNumber)}`,
      { method: 'GET' }
    );
  },

  /**
   * 8. Initialize Payment Intent / Checkout Session
   * POST /payments/create-intent/
   * Integrates Stripe, JazzCash, EasyPaisa, or Cash On Delivery
   */
  async createPaymentIntent(
    paymentRequest: ApiPaymentIntentRequest
  ): Promise<ApiPaymentIntentResponse> {
    return request<ApiPaymentIntentResponse>('/payments/create-intent/', {
      method: 'POST',
      body: JSON.stringify(paymentRequest),
    });
  },

  /**
   * 9. Verify Payment Callback / Status
   * POST /payments/verify/
   */
  async verifyPayment(paymentId: string, orderId: string): Promise<{ status: string; isPaid: boolean }> {
    return request('/payments/verify/', {
      method: 'POST',
      body: JSON.stringify({ paymentId, orderId }),
    });
  },

  /**
   * 10. Cancel Order (if order is still pending)
   * POST /orders/:orderId/cancel/
   */
  async cancelOrder(orderId: string, reason?: string): Promise<{ success: boolean; message: string }> {
    return request(`/orders/${encodeURIComponent(orderId)}/cancel/`, {
      method: 'POST',
      body: JSON.stringify({ reason }),
    });
  },
};
