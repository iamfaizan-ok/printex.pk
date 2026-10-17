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
  status: 'pending_payment' | 'processing' | 'completed';
  createdAt: string;
  totalImpressions: number;
  estimatedSheets: number;
  currency: string;
  estimatedPrice: number;
}

export interface ApiError {
  status: number;
  message: string;
  details?: Record<string, string[]>;
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
    return APP_CONFIG.apiBaseUrl;
  },

  /**
   * Submits a print order to the Django backend once connected.
   */
  async submitOrder(draft: PrintDraft): Promise<CreateOrderResponse> {
    if (!this.isBackendConfigured()) {
      throw new Error(
        'Backend API is not yet configured (Phase 1 Frontend Mode). Orders cannot be submitted to a remote server.'
      );
    }

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

    return response.json();
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
