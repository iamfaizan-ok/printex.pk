/**
 * PrintX Admin Portal - Configuration
 * Safe, client-side configuration parameters for Admin Side.
 * Never store secrets, API keys, or passwords here.
 */
(function (window) {
    'use strict';

    const origin = window.location.origin;
    const isLocalhost = origin.includes('localhost') || origin.includes('127.0.0.1');

    window.PRINTX_CONFIG = Object.freeze({
        // API Base URL - always connects to Django backend on port 8000 if running locally
        API_BASE_URL: isLocalhost && !origin.includes(':8000') 
            ? 'http://localhost:8000/api/v1' 
            : (origin.startsWith('http') ? origin + '/api/v1' : 'http://localhost:8000/api/v1'),

        // Endpoints mapping
        ENDPOINTS: {
            LOGIN: '/admin/auth/login/',
            LOGOUT: '/admin/auth/logout/',
            ME: '/admin/auth/me/',
            PRINT_JOBS: '/admin/print-jobs/',
            JOB_DETAIL: (id) => `/admin/print-jobs/${encodeURIComponent(id)}/`,
            JOB_BLOCK: (id) => `/admin/print-jobs/${encodeURIComponent(id)}/block/`,
            JOB_UNBLOCK: (id) => `/admin/print-jobs/${encodeURIComponent(id)}/unblock/`,
            JOB_PAY_OK: (id) => `/admin/print-jobs/${encodeURIComponent(id)}/pay-ok/`,
            JOB_AUTHORIZE_PRINT: (id) => `/admin/print-jobs/${encodeURIComponent(id)}/authorize-print/`,
        },

        // Polling interval for live order updates (milliseconds)
        POLL_INTERVAL_MS: 3000,

        // Pagination settings
        DEFAULT_PAGE_SIZE: 15,

        // Storage keys for non-sensitive UI state
        STORAGE_KEYS: {
            ADMIN_USER: 'printx_admin_user',
            CSRF_TOKEN: 'printx_admin_csrf',
        }
    });
})(window);
