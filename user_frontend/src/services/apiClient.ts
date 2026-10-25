import { APP_CONFIG } from '../config/appConfig';
import { PrintDraft } from '../types/printDraft';

export interface CreateOrderRequest {
  draftId: string;
  files: Array<{
    fileName: string;
    fileSizeBytes: number;
    pageCount: number;
    settings: {
      copies: number;
      paperSize: string;
      colourMode: string;
      orientation: string;
      sides: string;
      pageRange: string;
    };
  }>;
}

export interface CreateOrderResponse {
  orderId: string;
  orderNumber: string;
  status: 'pending_payment' | 'processing' | 'completed' | string;
  createdAt: string;
  totalImpressions: number;
  estimatedSheets: number;
  currency: string;
  estimatedPrice: number;
  targetPrinter?: string;
  printerDispatched?: boolean;
}

/**
 * Service client prepared for the future Django REST Framework backend.
 * In Phase 1 (frontend-only), operations report backend status transparently.
 */
export const apiClient = {
  isBackendConfigured(): boolean {
    return Boolean(APP_CONFIG.apiBaseUrl && APP_CONFIG.apiBaseUrl.trim().length > 0);
  },

  getBaseUrl(): string {
    const url = APP_CONFIG.apiBaseUrl || '/api/v1';
    return url.replace(/\/+$/, '');
  },

  /**
   * Submits a print order to the Django backend once connected.
   * If raw PDF File is in browser memory, submits as multipart/form-data to /print-jobs/.
   * Otherwise sends structured JSON order payload to /orders/.
   */
  async submitOrder(
    draft: PrintDraft,
    options: {
      paymentMethod?: string;
      customerName?: string;
      phone?: string;
      deliveryMethod?: string;
    } = {}
  ): Promise<CreateOrderResponse> {
    if (!this.isBackendConfigured()) {
      throw new Error(
        'Backend API is not yet configured. Please ensure VITE_API_BASE_URL is set in your environment.'
      );
    }

    const readyFiles = draft.files.filter((f) => f.processingStatus === 'ready' && f.file instanceof File);
    const paymentMethod = options.paymentMethod || 'cash_on_delivery';

    // If in-memory browser Files are available, submit single multipart order to /orders/
    if (readyFiles.length > 0) {
      const formData = new FormData();
      readyFiles.forEach((fileItem) => {
        formData.append('files', fileItem.file as File);
      });

      const fileSettings = readyFiles.map((f) => ({
        fileName: f.originalFileName || (f.file ? f.file.name : 'document.pdf'),
        pageCount: f.pageCount || 1,
        copies: f.printSettings.copies,
        paperSize: f.printSettings.paperSize,
        colourMode: f.printSettings.colourMode,
        orientation: f.printSettings.orientation,
        sides: f.printSettings.sides,
        pageRange: f.printSettings.pageRange,
      }));
      formData.append('file_settings', JSON.stringify(fileSettings));

      formData.append('customer_name', options.customerName || 'Online Customer');
      formData.append('customer_phone', options.phone || '0300-0000000');
      formData.append('delivery_method', options.deliveryMethod || 'pickup');
      formData.append('payment_method', paymentMethod);
      const isCash = paymentMethod === 'cash_on_delivery' || paymentMethod === 'cash';
      formData.append('auto_print', isCash ? 'false' : 'true');
      formData.append('notes', `Payment Mode: ${paymentMethod.toUpperCase()}`);

      const resp = await fetch(`${this.getBaseUrl()}/orders/`, {
        method: 'POST',
        headers: { Accept: 'application/json' },
        body: formData,
      });

      if (!resp.ok) {
        let err = `Server error (${resp.status})`;
        try {
          const j = await resp.json();
          if (j.message) {
            err = j.message;
          } else if (j.detail) {
            err = j.detail;
          } else if (j.error) {
            err = j.error;
          } else if (typeof j === 'object' && j !== null) {
            const msgs = Object.entries(j)
              .map(([field, msg]) => Array.isArray(msg) ? `${field}: ${msg.join(', ')}` : `${field}: ${msg}`)
              .join(' | ');
            if (msgs) err = msgs;
          }
        } catch {
          // ignore
        }
        throw new Error(err);
      }

      const resJson = await resp.json();
      const orderData = resJson.data || resJson;

      return {
        orderId: orderData.orderId || orderData.id,
        orderNumber: orderData.orderNumber || orderData.job_number || 'ORD id 101',
        status: orderData.status || 'queued',
        createdAt: orderData.createdAt || new Date().toISOString(),
        totalImpressions: orderData.totalImpressions || 1,
        estimatedSheets: orderData.totalSheets || 1,
        currency: orderData.pricing?.currency || 'PKR',
        estimatedPrice: orderData.pricing?.totalAmount || 0,
        targetPrinter: orderData.targetPrinter || 'Default Printer',
        printerDispatched: Boolean(orderData.printerDispatched),
      };
    }

    // JSON fallback payload to /orders/
    const payload: CreateOrderRequest = {
      draftId: draft.draftId,
      files: draft.files.map((f) => ({
        fileName: f.originalFileName,
        fileSizeBytes: f.fileSize,
        pageCount: f.pageCount,
        settings: {
          copies: f.printSettings.copies,
          paperSize: f.printSettings.paperSize,
          colourMode: f.printSettings.colourMode,
          orientation: f.printSettings.orientation,
          sides: f.printSettings.sides,
          pageRange: f.printSettings.pageRange,
        },
      })),
    };

    const response = await fetch(`${this.getBaseUrl()}/orders/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Accept: 'application/json',
      },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      let errorMessage = `Server error (${response.status})`;
      try {
        const errorJson = await response.json();
        if (errorJson.message) errorMessage = errorJson.message;
      } catch {
        // Fallback to HTTP error
      }
      throw new Error(errorMessage);
    }

    const orderData = await response.json();
    return {
      orderId: orderData.orderId || orderData.id,
      orderNumber: orderData.orderNumber || orderData.job_number || 'ORD id 101',
      status: orderData.status || 'pending_payment',
      createdAt: orderData.createdAt || new Date().toISOString(),
      totalImpressions: orderData.totalImpressions || 1,
      estimatedSheets: orderData.totalSheets || 1,
      currency: orderData.pricing?.currency || 'PKR',
      estimatedPrice: orderData.pricing?.totalAmount || 0,
    };
  },

  /**
   * Health check for future Django REST Framework API.
   */
  async checkHealth(): Promise<{ status: 'online' | 'offline'; version?: string }> {
    if (!this.isBackendConfigured()) {
      return { status: 'offline' };
    }

    try {
      const response = await fetch(`${this.getBaseUrl()}/health/`, {
        method: 'GET',
        headers: { Accept: 'application/json' },
      });
      if (response.ok) {
        const data = await response.json();
        return { status: 'online', version: data.version };
      }
      return { status: 'offline' };
    } catch {
      return { status: 'offline' };
    }
  },
};

export { userApis } from '../api/userApis';
export * from '../api/userApis';
