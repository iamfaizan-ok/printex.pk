/**
 * PrintX Admin Portal - Configuration
 * Safe, client-side configuration parameters for Admin Side.
 * Never store secrets, API keys, or passwords here.
 */
(function (window) {
    'use strict';

    const origin = window.location.origin;

    window.PRINTX_CONFIG = Object.freeze({
        // API Base URL - always connects to same origin (works for both port 8000 and proxied port 3000)
        API_BASE_URL: origin && origin.startsWith('http') ? origin + '/api/v1' : 'http://127.0.0.1:8000/api/v1',

        // Endpoints mapping
        ENDPOINTS: {
            LOGIN: '/admin/auth/login/',
            SIGNUP: '/admin/auth/signup/',
            LOGOUT: '/admin/auth/logout/',
            ME: '/admin/auth/me/',
            PASSWORD_RESET: '/admin/auth/password-reset/',
            PASSWORD_RESET_CONFIRM: '/admin/auth/password-reset-confirm/',
            GOOGLE_AUTH: '/admin/auth/google/',
            MY_SHOP: '/admin/my-shop/',
            SHOPS: '/shops/',
            SHOP_QR: (id) => `/shops/${encodeURIComponent(id)}/qr/`,
            PRINT_JOBS: '/admin/print-jobs/',
            CLEAR_ALL: '/admin/print-jobs/clear-all/',
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
