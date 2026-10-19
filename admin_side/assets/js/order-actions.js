/**
 * PrintX Admin Portal - Order Action Handlers
 * Implements Block, Unblock, Pay OK, and Print workflows with
 * double-click prevention and accessible confirmation dialogs.
 */
(function (window) {
    'use strict';

    const config = window.PRINTX_CONFIG;
    const api = window.PrintXApi;
    const notify = window.PrintXNotifications;

    const activeOperations = new Set();

    function showConfirmModal({ title, message, confirmText, confirmClass, onConfirm }) {
        const overlay = document.getElementById('confirm-modal-overlay');
        const titleEl = document.getElementById('modal-title');
        const messageEl = document.getElementById('modal-message');
        const confirmBtn = document.getElementById('modal-confirm-btn');
        const cancelBtn = document.getElementById('modal-cancel-btn');

        if (!overlay || !confirmBtn || !cancelBtn) {
            if (window.confirm(`${title}\n\n${message}`)) {
                onConfirm();
            }
            return;
        }

        titleEl.textContent = title;
        messageEl.textContent = message;
        confirmBtn.textContent = confirmText || 'Confirm';
        confirmBtn.className = `btn ${confirmClass || 'btn-primary'}`;

        overlay.classList.add('active');
        confirmBtn.focus();

        function cleanup() {
            overlay.classList.remove('active');
            confirmBtn.removeEventListener('click', handleConfirm);
            cancelBtn.removeEventListener('click', handleCancel);
            document.removeEventListener('keydown', handleKeyDown);
        }

        function handleConfirm() {
            cleanup();
            onConfirm();
        }

        function handleCancel() {
            cleanup();
        }

        function handleKeyDown(e) {
            if (e.key === 'Escape') {
                handleCancel();
            }
        }

        confirmBtn.addEventListener('click', handleConfirm);
        cancelBtn.addEventListener('click', handleCancel);
        document.addEventListener('keydown', handleKeyDown);
    }

    async function executeAction(actionKey, buttonElement, apiFn, onSuccess) {
        if (activeOperations.has(actionKey)) {
            return;
        }

        activeOperations.add(actionKey);
        const originalText = buttonElement ? buttonElement.innerHTML : '';

        if (buttonElement) {
            buttonElement.disabled = true;
            buttonElement.classList.add('btn-loading');
            buttonElement.innerHTML = '<span class="spinner-sm"></span> Processing...';
        }

        try {
            const result = await apiFn();
            notify.success(result.message || 'Action executed successfully.');
            if (typeof onSuccess === 'function') {
                onSuccess(result.data);
            }
        } catch (error) {
            const msg = error.data && error.data.message ? error.data.message : error.message;
            notify.error(msg || 'An error occurred while executing action.');
        } finally {
            activeOperations.delete(actionKey);
            if (buttonElement) {
                buttonElement.disabled = false;
                buttonElement.classList.remove('btn-loading');
                buttonElement.innerHTML = originalText;
            }
        }
    }

    function handleBlock(order, buttonElement, onUpdated) {
        showConfirmModal({
            title: `Block Order ${order.job_number}?`,
            message: `Are you sure you want to block order ${order.job_number} ("${order.original_filename}")? Blocked orders cannot be queued, claimed, or printed.`,
            confirmText: 'Block Order',
            confirmClass: 'btn-danger',
            onConfirm: () => {
                const actionKey = `block_${order.id}`;
                executeAction(
                    actionKey,
                    buttonElement,
                    () => api.post(config.ENDPOINTS.JOB_BLOCK(order.id), { reason: 'Blocked by administrator' }),
                    onUpdated
                );
            }
        });
    }

    function handleUnblock(order, buttonElement, onUpdated) {
        showConfirmModal({
            title: `Unblock Order ${order.job_number}?`,
            message: `Do you want to unblock order ${order.job_number}? Note: Unblocking does not automatically mark cash received.`,
            confirmText: 'Unblock Order',
            confirmClass: 'btn-warning',
            onConfirm: () => {
                const actionKey = `unblock_${order.id}`;
                executeAction(
                    actionKey,
                    buttonElement,
                    () => api.post(config.ENDPOINTS.JOB_UNBLOCK(order.id), {}),
                    onUpdated
                );
            }
        });
    }

    function handlePayOk(order, buttonElement, onUpdated) {
        const amountDisplay = order.total_amount ? `${order.currency || 'PKR'} ${order.total_amount}` : 'order amount';

        showConfirmModal({
            title: `Confirm Cash Received (Pay OK)?`,
            message: `Confirm that you have received ${amountDisplay} in physical cash for Order ${order.job_number} ("${order.original_filename}"). This action authorizes the print job.`,
            confirmText: 'Pay OK (Cash Received)',
            confirmClass: 'btn-success',
            onConfirm: () => {
                const actionKey = `payok_${order.id}`;
                executeAction(
                    actionKey,
                    buttonElement,
                    () => api.post(config.ENDPOINTS.JOB_PAY_OK(order.id), {}),
                    onUpdated
                );
            }
        });
    }

    function handleAuthorizePrint(order, buttonElement, onUpdated) {
        const isCash = order.payment_status === 'cash_pending' || order.is_cash_pending;
        const amountDisplay = order.total_amount ? `${order.currency || 'PKR'} ${order.total_amount}` : 'order amount';
        const msg = isCash
            ? `Order ${order.job_number} ("${order.original_filename}") is pending cash payment of ${amountDisplay}.\n\nClicking Print will confirm cash received and immediately send the document to the physical printer. Proceed?`
            : `Submit order ${order.job_number} ("${order.original_filename}") to the physical printer spooler?`;

        showConfirmModal({
            title: `Print Order ${order.job_number}?`,
            message: msg,
            confirmText: 'Print Now',
            confirmClass: 'btn-primary',
            onConfirm: () => {
                const actionKey = `print_${order.id}`;
                executeAction(
                    actionKey,
                    buttonElement,
                    () => api.post(config.ENDPOINTS.JOB_AUTHORIZE_PRINT(order.id), {}),
                    onUpdated
                );
            }
        });
    }

    window.PrintXOrderActions = Object.freeze({
        handleBlock,
        handleUnblock,
        handlePayOk,
        handleAuthorizePrint,
        showConfirmModal,
    });
})(window);
