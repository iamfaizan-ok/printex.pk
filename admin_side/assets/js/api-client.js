/**
 * PrintX Admin Portal - API Client
 * Centralized fetch wrapper with CSRF extraction, session credentials,
 * timeout handling, and unified error mapping.
 */
(function (window) {
    'use strict';

    const config = window.PRINTX_CONFIG;

    /**
     * Extracts CSRF token from browser cookies.
     */
    function getCsrfFromCookie() {
        const name = 'csrftoken=';
        const decodedCookie = decodeURIComponent(document.cookie);
        const ca = decodedCookie.split(';');
        for (let i = 0; i < ca.length; i++) {
            let c = ca[i].trim();
            if (c.indexOf(name) === 0) {
                return c.substring(name.length, c.length);
            }
        }
        return null;
    }

    /**
     * Gets active CSRF token from cookie or stored session.
     */
    function getCsrfToken() {
        const cookieToken = getCsrfFromCookie();
        if (cookieToken) return cookieToken;
        return localStorage.getItem(config.STORAGE_KEYS.CSRF_TOKEN) || '';
    }

    /**
     * Centralized request executor
     */
    async function request(endpoint, options = {}) {
        const url = endpoint.startsWith('http') ? endpoint : `${config.API_BASE_URL}${endpoint}`;
        const method = (options.method || 'GET').toUpperCase();
        const headers = new Headers(options.headers || {});

        if (!headers.has('Accept')) {
            headers.set('Accept', 'application/json');
        }

        if (options.body && typeof options.body === 'string' && !headers.has('Content-Type')) {
            headers.set('Content-Type', 'application/json');
        }

        const isUnsafeMethod = ['POST', 'PUT', 'PATCH', 'DELETE'].includes(method);
        if (isUnsafeMethod) {
            const csrfToken = getCsrfToken();
            if (csrfToken) {
                headers.set('X-CSRFToken', csrfToken);
            }
        }

        const timeoutMs = options.timeout || 15000;
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

        const fetchOptions = {
            method,
            headers,
            credentials: 'include',
            signal: controller.signal,
            ...options,
        };

        try {
            const response = await fetch(url, fetchOptions);
            clearTimeout(timeoutId);

            const returnedCsrf = response.headers.get('X-CSRFToken');
            if (returnedCsrf) {
                localStorage.setItem(config.STORAGE_KEYS.CSRF_TOKEN, returnedCsrf);
            }

            let responseData = null;
            const contentType = response.headers.get('content-type') || '';
            if (contentType.includes('application/json')) {
                responseData = await response.json();
            } else {
                const text = await response.text();
                responseData = { message: text };
            }

            if (responseData && responseData.csrfToken) {
                localStorage.setItem(config.STORAGE_KEYS.CSRF_TOKEN, responseData.csrfToken);
            }

            if (response.status === 401 || (response.status === 403 && !window.location.pathname.includes('login.html'))) {
                if (!window.location.pathname.endsWith('login.html')) {
                    localStorage.removeItem(config.STORAGE_KEYS.ADMIN_USER);
                    window.location.href = 'login.html?expired=1';
                }
            }

            if (!response.ok) {
                const errorMsg = (responseData && (responseData.message || responseData.detail || responseData.error))
                    || `Request failed with status ${response.status}`;
                const err = new Error(errorMsg);
                err.status = response.status;
                err.data = responseData;
                throw err;
            }

            return responseData;
        } catch (error) {
            clearTimeout(timeoutId);

            if (error.name === 'AbortError') {
                const timeoutErr = new Error('The request timed out. Please verify your connection.');
                timeoutErr.status = 408;
                throw timeoutErr;
            }

            throw error;
        }
    }

    window.PrintXApi = Object.freeze({
        get: (endpoint, options) => request(endpoint, { ...options, method: 'GET' }),
        post: (endpoint, data, options) => request(endpoint, {
            ...options,
            method: 'POST',
            body: data ? JSON.stringify(data) : undefined
        }),
        put: (endpoint, data, options) => request(endpoint, {
            ...options,
            method: 'PUT',
            body: data ? JSON.stringify(data) : undefined
        }),
        delete: (endpoint, options) => request(endpoint, { ...options, method: 'DELETE' }),
        request,
        getCsrfToken,
    });
})(window);
