/**
 * PrintX Admin Portal - All Order Prints Dashboard
 * Real-time order management, tab filtering, debounced search,
 * pagination, smart polling, and compact single-line row rendering.
 */
(function (window) {
    'use strict';

    const config = window.PRINTX_CONFIG;
    const api = window.PrintXApi;
    const auth = window.PrintXAuth;
    const notify = window.PrintXNotifications;
    const actions = window.PrintXOrderActions;

    // State
    let currentTab = 'all';
    let searchQuery = '';
    let currentPage = 1;
    let pageSize = config.DEFAULT_PAGE_SIZE;
    let pollTimer = null;
    let isFetching = false;
    let searchDebounceTimer = null;

    // DOM Elements
    let tableBody = null;
    let totalCountBadge = null;
    let paginationContainer = null;
    let searchInput = null;
    let refreshBtn = null;
    let lastUpdatedEl = null;

    async function initDashboard() {
        const user = await auth.requireAuth();
        if (!user) return;

        const adminNameEl = document.getElementById('admin-user-display');
        if (adminNameEl) {
            adminNameEl.textContent = user.username || user.email;
        }

        tableBody = document.getElementById('orders-table-body');
        totalCountBadge = document.getElementById('total-orders-count');
        paginationContainer = document.getElementById('pagination-controls');
        searchInput = document.getElementById('order-search-input');
        refreshBtn = document.getElementById('manual-refresh-btn');
        lastUpdatedEl = document.getElementById('last-updated-time');

        const logoutBtn = document.getElementById('admin-logout-btn');
        if (logoutBtn) {
            logoutBtn.addEventListener('click', (e) => {
                e.preventDefault();
                auth.logout();
            });
        }

        const tabs = document.querySelectorAll('.filter-tab');
        tabs.forEach((tab) => {
            tab.addEventListener('click', () => {
                tabs.forEach((t) => t.classList.remove('active'));
                tab.classList.add('active');
                currentTab = tab.getAttribute('data-tab') || 'all';
                currentPage = 1;
                fetchOrders(true);
            });
        });

        if (searchInput) {
            searchInput.addEventListener('input', (e) => {
                clearTimeout(searchDebounceTimer);
                searchDebounceTimer = setTimeout(() => {
                    searchQuery = e.target.value.trim();
                    currentPage = 1;
                    fetchOrders(true);
                }, 350);
            });
        }

        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => {
                fetchOrders(false);
            });
        }

        document.addEventListener('visibilitychange', () => {
            if (document.visibilityState === 'visible') {
                startPolling();
                fetchOrders(false);
            } else {
                stopPolling();
            }
        });

        await fetchOrders(true);
        startPolling();
    }

    function startPolling() {
        stopPolling();
        pollTimer = setInterval(() => {
            if (document.visibilityState === 'visible' && !isFetching) {
                fetchOrders(false);
            }
        }, config.POLL_INTERVAL_MS);
    }

    function stopPolling() {
        if (pollTimer) {
            clearInterval(pollTimer);
            pollTimer = null;
        }
    }

    async function fetchOrders(showLoadingIndicator = false) {
        if (isFetching) return;
        isFetching = true;

        if (showLoadingIndicator && tableBody) {
            tableBody.innerHTML = `
                <tr class="table-state-row">
                    <td colspan="5" class="state-cell">
                        <div class="loading-state">
                            <span class="spinner"></span>
                            <span>Loading print orders...</span>
                        </div>
                    </td>
                </tr>
            `;
        }

        try {
            const params = new URLSearchParams({
                tab: currentTab,
                page: currentPage.toString(),
                page_size: pageSize.toString(),
            });

            if (searchQuery) {
                params.set('search', searchQuery);
            }

            const endpoint = `${config.ENDPOINTS.PRINT_JOBS}?${params.toString()}`;
            const res = await api.get(endpoint);

            if (res && res.success) {
                updateStatsBadges(res.stats);
                renderOrdersTable(res.data);
                renderPagination(res.pagination);
                updateLastRefreshTimestamp();
            } else {
                renderErrorState('Failed to load orders.');
            }
        } catch (error) {
            console.error('Error fetching orders:', error);
            if (showLoadingIndicator) {
                renderErrorState(error.message || 'Network error while loading orders.');
            }
        } finally {
            isFetching = false;
        }
    }

    function updateStatsBadges(stats) {
        if (!stats) return;

        const updateBadge = (id, count) => {
            const el = document.getElementById(id);
            if (el) el.textContent = count !== undefined ? count : '0';
        };

        updateBadge('stat-total', stats.total);
        updateBadge('stat-cash-pending', stats.cash_pending);
        updateBadge('stat-blocked', stats.blocked);
        updateBadge('stat-queued', stats.queued);
        updateBadge('stat-printing', stats.printing);
        updateBadge('stat-completed', stats.completed);
        updateBadge('stat-failed', stats.failed);
    }

    function renderOrdersTable(orders) {
        if (!tableBody) return;

        if (!orders || orders.length === 0) {
            tableBody.innerHTML = `
                <tr class="table-state-row">
                    <td colspan="5" class="state-cell">
                        <div class="empty-state">
                            <div class="empty-icon">&#128196;</div>
                            <div class="empty-title">No Print Orders Found</div>
                            <div class="empty-desc">
                                ${searchQuery ? 'No orders match your search criteria.' : 'There are no print orders in this view.'}
                            </div>
                        </div>
                    </td>
                </tr>
            `;
            return;
        }

        tableBody.innerHTML = '';

        orders.forEach((order) => {
            const row = document.createElement('tr');
            row.id = `order-row-${order.id}`;
            row.className = 'order-row';

            // Special Admin UI Requirement (Section 4):
            // "For an order awaiting cash-payment approval, show ONLY these three visible elements in its compact order row:
            // 1. Document filename.
            // 2. Order ID.
            // 3. One button labelled 'Pay OK'.
            // Do not show the Block or Print buttons on that particular row while it is awaiting cash-payment approval."
            const isCashPending = order.payment_status === 'cash_pending' || order.is_cash_pending;
            const isBlocked = order.approval_status === 'blocked';
            const isPrinted = order.status === 'completed' || order.status === 'submitted_to_printer';
            const isPrinting = order.status === 'submitting_to_printer' || order.status === 'downloading' || order.status === 'ready_to_print';

            if (isCashPending) {
                row.classList.add('order-row-cash-pending');
            }
            row.classList.add(`order-status-${order.status}`);
            if (isBlocked) {
                row.classList.add('order-blocked');
            }

            // 1. Filename Cell (XSS Safe)
            const fileCell = document.createElement('td');
            fileCell.className = 'col-filename';
            const fileSpan = document.createElement('span');
            fileSpan.className = 'document-filename';
            fileSpan.title = order.original_filename;
            fileSpan.textContent = order.original_filename;

            const metaSpan = document.createElement('div');
            metaSpan.className = 'document-meta';
            metaSpan.textContent = `${order.page_count || 1}p • ${order.copies || 1} copy • ${(order.colour_mode || 'bw').toUpperCase()}`;
            fileCell.appendChild(fileSpan);
            fileCell.appendChild(metaSpan);

            // 2. Order ID Cell
            const idCell = document.createElement('td');
            idCell.className = 'col-order-id';
            const idSpan = document.createElement('span');
            idSpan.className = 'order-id-badge';
            idSpan.textContent = order.job_number;
            idCell.appendChild(idSpan);

            // 3. Print / Approval Status Cell
            const statusCell = document.createElement('td');
            statusCell.className = 'col-status';
            const statusBadge = document.createElement('span');
            if (isBlocked) {
                statusBadge.className = 'badge badge-blocked';
                statusBadge.textContent = 'Blocked';
            } else if (order.status === 'queued') {
                statusBadge.className = 'badge badge-queued';
                statusBadge.textContent = 'Pending Print';
            } else {
                statusBadge.className = `badge badge-${order.status}`;
                statusBadge.textContent = formatStatusLabel(order.status);
            }
            statusCell.appendChild(statusBadge);

            // 4. Payment Status Cell
            const paymentCell = document.createElement('td');
            paymentCell.className = 'col-payment';
            const paymentBadge = document.createElement('span');
            paymentBadge.className = `badge badge-pay-${order.payment_status}`;
            paymentBadge.textContent = formatPaymentLabel(order.payment_status);
            paymentCell.appendChild(paymentBadge);

            // 5. Action Buttons Cell: Block and Print buttons side-by-side
            const actionCell = document.createElement('td');
            actionCell.className = 'col-actions';
            const btnGroup = document.createElement('div');
            btnGroup.className = 'action-btn-group';

            // Button 1: Block / Unblock Button
            if (isBlocked || order.can_unblock) {
                const unblockBtn = document.createElement('button');
                unblockBtn.type = 'button';
                unblockBtn.className = 'btn btn-outline-warning btn-sm';
                unblockBtn.textContent = 'Unblock';
                unblockBtn.title = 'Unblock this order';
                unblockBtn.addEventListener('click', (e) => {
                    e.stopPropagation();
                    actions.handleUnblock(order, unblockBtn, () => fetchOrders(false));
                });
                btnGroup.appendChild(unblockBtn);
            } else {
                const blockBtn = document.createElement('button');
                blockBtn.type = 'button';
                blockBtn.className = 'btn btn-outline-danger btn-sm';
                blockBtn.textContent = 'Block';
                blockBtn.title = 'Block this order from printing';
                blockBtn.addEventListener('click', (e) => {
                    e.stopPropagation();
                    actions.handleBlock(order, blockBtn, () => fetchOrders(false));
                });
                btnGroup.appendChild(blockBtn);
            }

            // Button 2: Print Button (Next to Block)
            const printBtn = document.createElement('button');
            printBtn.type = 'button';

            if (isBlocked) {
                printBtn.className = 'btn btn-outline-secondary btn-sm';
                printBtn.disabled = true;
                printBtn.innerHTML = '&#128438; Print';
                printBtn.title = 'Unblock this order first to print';
                btnGroup.appendChild(printBtn);
            } else if (isPrinted) {
                printBtn.className = 'btn btn-outline-secondary btn-sm';
                printBtn.disabled = true;
                printBtn.innerHTML = '&#10003; Printed';
                printBtn.title = 'Order has already been printed';
                btnGroup.appendChild(printBtn);
            } else if (isPrinting) {
                printBtn.className = 'btn btn-primary btn-sm btn-loading';
                printBtn.disabled = true;
                printBtn.innerHTML = '<span class="spinner-sm"></span> Printing...';
                btnGroup.appendChild(printBtn);
            } else {
                // Pending / Queued (including Cash Pending) -> Active Print Button!
                printBtn.className = 'btn btn-primary btn-sm btn-print-action';
                printBtn.innerHTML = '&#128438; Print';
                printBtn.title = isCashPending 
                    ? 'Confirm cash and print order' 
                    : 'Send to physical printer spooler';
                printBtn.addEventListener('click', (e) => {
                    e.stopPropagation();
                    actions.handleAuthorizePrint(order, printBtn, () => fetchOrders(false));
                });
                btnGroup.appendChild(printBtn);
            }

            // Optional Button 3: Compact Pay OK if cash is pending
            if (isCashPending && !isBlocked) {
                const payOkBtn = document.createElement('button');
                payOkBtn.type = 'button';
                payOkBtn.className = 'btn btn-pay-ok btn-sm';
                payOkBtn.setAttribute('data-job-id', order.id);
                payOkBtn.title = 'Confirm cash received only';
                payOkBtn.innerHTML = '&#10003; Pay OK';
                payOkBtn.addEventListener('click', (e) => {
                    e.stopPropagation();
                    actions.handlePayOk(order, payOkBtn, () => fetchOrders(false));
                });
                btnGroup.appendChild(payOkBtn);
            }

            actionCell.appendChild(btnGroup);

            row.appendChild(fileCell);
            row.appendChild(idCell);
            row.appendChild(statusCell);
            row.appendChild(paymentCell);
            row.appendChild(actionCell);

            tableBody.appendChild(row);
        });
    }

    function renderPagination(pagination) {
        if (!paginationContainer || !pagination) return;

        const { page, totalPages, totalCount, hasPrev, hasNext } = pagination;
        paginationContainer.innerHTML = '';
        if (totalCount === 0) return;

        const infoSpan = document.createElement('span');
        infoSpan.className = 'pagination-info';
        infoSpan.textContent = `Page ${page} of ${totalPages} (${totalCount} orders)`;
        paginationContainer.appendChild(infoSpan);

        const btnWrapper = document.createElement('div');
        btnWrapper.className = 'pagination-buttons';

        const prevBtn = document.createElement('button');
        prevBtn.type = 'button';
        prevBtn.className = 'btn btn-pagination';
        prevBtn.disabled = !hasPrev;
        prevBtn.innerHTML = '&larr; Prev';
        prevBtn.addEventListener('click', () => {
            if (hasPrev) {
                currentPage = page - 1;
                fetchOrders(true);
            }
        });
        btnWrapper.appendChild(prevBtn);

        const nextBtn = document.createElement('button');
        nextBtn.type = 'button';
        nextBtn.className = 'btn btn-pagination';
        nextBtn.disabled = !hasNext;
        nextBtn.innerHTML = 'Next &rarr;';
        nextBtn.addEventListener('click', () => {
            if (hasNext) {
                currentPage = page + 1;
                fetchOrders(true);
            }
        });
        btnWrapper.appendChild(nextBtn);

        paginationContainer.appendChild(btnWrapper);
    }

    function renderErrorState(message) {
        if (!tableBody) return;
        tableBody.innerHTML = `
            <tr class="table-state-row">
                <td colspan="5" class="state-cell">
                    <div class="error-state">
                        <div class="error-icon">&#9888;</div>
                        <div class="error-title">Failed to Load Orders</div>
                        <div class="error-desc">${message}</div>
                        <button type="button" class="btn btn-primary btn-sm" id="retry-fetch-btn">
                            Retry
                        </button>
                    </div>
                </td>
            </tr>
        `;
        const retryBtn = document.getElementById('retry-fetch-btn');
        if (retryBtn) {
            retryBtn.addEventListener('click', () => fetchOrders(true));
        }
    }

    function updateLastRefreshTimestamp() {
        if (lastUpdatedEl) {
            const now = new Date();
            lastUpdatedEl.textContent = `Updated: ${now.toLocaleTimeString()}`;
        }
    }

    function formatStatusLabel(st) {
        const map = {
            queued: 'Queued',
            claimed: 'Claimed',
            downloading: 'Downloading',
            ready_to_print: 'Ready',
            submitting_to_printer: 'Submitting',
            submitted_to_printer: 'Printing',
            completed: 'Completed',
            failed: 'Failed',
            outcome_unknown: 'Uncertain',
            cancelled: 'Cancelled',
        };
        return map[st] || st;
    }

    function formatPaymentLabel(p) {
        const map = {
            unpaid: 'Unpaid',
            cash_pending: 'Cash Pending',
            cash_received: 'Cash Paid',
            online_payment_pending: 'Online Pending',
            paid: 'Paid',
            payment_failed: 'Payment Failed',
            refunded: 'Refunded',
        };
        return map[p] || p;
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initDashboard);
    } else {
        initDashboard();
    }
})(window);
