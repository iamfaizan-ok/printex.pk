/**
 * PrintX Admin Portal - Notifications System
 * Accessible, lightweight toast notification module.
 */
(function (window) {
    'use strict';

    let container = null;

    function getContainer() {
        if (!container) {
            container = document.getElementById('toast-container');
            if (!container) {
                container = document.createElement('div');
                container.id = 'toast-container';
                container.setAttribute('aria-live', 'polite');
                container.setAttribute('aria-atomic', 'true');
                container.className = 'toast-container';
                document.body.appendChild(container);
            }
        }
        return container;
    }

    function showToast(message, type = 'info', duration = 4000) {
        const root = getContainer();

        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.setAttribute('role', type === 'error' ? 'alert' : 'status');

        const iconSpan = document.createElement('span');
        iconSpan.className = 'toast-icon';
        if (type === 'success') {
            iconSpan.innerHTML = '&#10003;';
        } else if (type === 'error') {
            iconSpan.innerHTML = '&#9888;';
        } else if (type === 'warning') {
            iconSpan.innerHTML = '&#9888;';
        } else {
            iconSpan.innerHTML = '&#8505;';
        }

        const textSpan = document.createElement('span');
        textSpan.className = 'toast-message';
        textSpan.textContent = message; // Safe textContent preventing XSS

        const closeBtn = document.createElement('button');
        closeBtn.type = 'button';
        closeBtn.className = 'toast-close';
        closeBtn.setAttribute('aria-label', 'Close notification');
        closeBtn.innerHTML = '&times;';
        closeBtn.addEventListener('click', () => removeToast(toast));

        toast.appendChild(iconSpan);
        toast.appendChild(textSpan);
        toast.appendChild(closeBtn);

        root.appendChild(toast);

        requestAnimationFrame(() => {
            toast.classList.add('toast-show');
        });

        if (duration > 0) {
            setTimeout(() => {
                removeToast(toast);
            }, duration);
        }

        return toast;
    }

    function removeToast(toast) {
        if (!toast || !toast.parentNode) return;
        toast.classList.remove('toast-show');
        toast.classList.add('toast-hide');
        setTimeout(() => {
            if (toast.parentNode) {
                toast.parentNode.removeChild(toast);
            }
        }, 300);
    }

    window.PrintXNotifications = Object.freeze({
        success: (msg, duration) => showToast(msg, 'success', duration),
        error: (msg, duration) => showToast(msg, 'error', duration || 5000),
        warning: (msg, duration) => showToast(msg, 'warning', duration || 4500),
        info: (msg, duration) => showToast(msg, 'info', duration),
    });
})(window);
