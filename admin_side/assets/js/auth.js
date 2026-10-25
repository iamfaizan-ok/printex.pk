/**
 * PrintX Admin Portal - Authentication Module
 * Manages admin login, logout, and session lifecycle.
 */
(function (window) {
    'use strict';

    const config = window.PRINTX_CONFIG;
    const api = window.PrintXApi;

    async function checkSession() {
        try {
            const res = await api.get(config.ENDPOINTS.ME);
            if (res && res.success && res.data) {
                localStorage.setItem(config.STORAGE_KEYS.ADMIN_USER, JSON.stringify(res.data));
                return res.data;
            }
            return null;
        } catch (error) {
            localStorage.removeItem(config.STORAGE_KEYS.ADMIN_USER);
            return null;
        }
    }

    async function requireAuth() {
        const user = await checkSession();
        if (!user) {
            window.location.href = 'login.html';
            return null;
        }
        return user;
    }

    async function redirectIfAuthenticated() {
        const user = await checkSession();
        if (user) {
            window.location.href = 'all-order-prints.html';
        }
    }

    async function login(username, password) {
        try {
            const res = await api.post(config.ENDPOINTS.LOGIN, { username, password });
            if (res && res.success) {
                if (res.data) {
                    localStorage.setItem(config.STORAGE_KEYS.ADMIN_USER, JSON.stringify(res.data));
                }
                if (res.csrfToken) {
                    localStorage.setItem(config.STORAGE_KEYS.CSRF_TOKEN, res.csrfToken);
                }
                return res;
            }
            throw new Error(res.message || 'Login failed.');
        } catch (error) {
            throw error;
        }
    }

    async function logout() {
        try {
            await api.post(config.ENDPOINTS.LOGOUT, {});
        } catch (err) {
            console.warn('Logout API warning:', err);
        } finally {
            localStorage.removeItem(config.STORAGE_KEYS.ADMIN_USER);
            localStorage.removeItem(config.STORAGE_KEYS.CSRF_TOKEN);
            window.location.href = 'login.html?logged_out=1';
        }
    }

    function getCurrentUser() {
        try {
            const raw = localStorage.getItem(config.STORAGE_KEYS.ADMIN_USER);
            return raw ? JSON.parse(raw) : null;
        } catch (e) {
            return null;
        }
    }

    async function signup(data) {
        try {
            const res = await api.post(config.ENDPOINTS.SIGNUP, data);
            if (res && res.success) {
                if (res.data) {
                    localStorage.setItem(config.STORAGE_KEYS.ADMIN_USER, JSON.stringify(res.data));
                }
                if (res.csrfToken) {
                    localStorage.setItem(config.STORAGE_KEYS.CSRF_TOKEN, res.csrfToken);
                }
                return res;
            }
            throw new Error(res.message || 'Signup failed.');
        } catch (error) {
            throw error;
        }
    }

    async function forgotPassword(email) {
        return api.post(config.ENDPOINTS.PASSWORD_RESET, { email });
    }

    async function resetPassword(uid, token, new_password) {
        return api.post(config.ENDPOINTS.PASSWORD_RESET_CONFIRM, { uid, token, new_password });
    }

    async function googleLogin(credential, extraData = {}) {
        try {
            const res = await api.post(config.ENDPOINTS.GOOGLE_AUTH, { credential, ...extraData });
            if (res && res.success) {
                if (res.data) {
                    localStorage.setItem(config.STORAGE_KEYS.ADMIN_USER, JSON.stringify(res.data));
                }
                if (res.csrfToken) {
                    localStorage.setItem(config.STORAGE_KEYS.CSRF_TOKEN, res.csrfToken);
                }
                return res;
            }
            throw new Error(res.message || 'Google sign-in failed.');
        } catch (error) {
            throw error;
        }
    }

    async function getMyShop() {
        return api.get(config.ENDPOINTS.MY_SHOP);
    }

    window.PrintXAuth = Object.freeze({
        login,
        signup,
        logout,
        forgotPassword,
        resetPassword,
        googleLogin,
        getMyShop,
        checkSession,
        requireAuth,
        redirectIfAuthenticated,
        getCurrentUser,
    });
})(window);
