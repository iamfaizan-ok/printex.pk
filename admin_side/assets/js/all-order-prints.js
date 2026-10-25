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
    const actions = window.PrintXOrderActions;

    function escapeHtml(str) {
        if (!str) return '';
        return String(str)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
    }

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

        const shopDisplayEl = document.getElementById('admin-shop-display');
        if (shopDisplayEl) {
            if (user.shop && user.shop.name) {
                shopDisplayEl.textContent = `${user.shop.name} (${user.shop.shop_id})`;
            } else if (user.is_superuser) {
                shopDisplayEl.textContent = 'Global Admin (All Shops)';
            } else {
                shopDisplayEl.textContent = 'Print Shop Operator';
            }
        }

        // Shop QR Code Modal Handlers
        const qrModal = document.getElementById('shop-qr-modal-overlay');
        const qrModalBtn = document.getElementById('shop-qr-modal-btn');
        const qrCloseBtn = document.getElementById('shop-qr-close-btn');
        const printQrBtn = document.getElementById('btn-print-qr-code');
        const copyLinkBtn = document.getElementById('btn-copy-shop-link');

        let currentShopInfo = user.shop || null;

        if (qrModalBtn) {
            qrModalBtn.addEventListener('click', async () => {
                try {
                    const res = await auth.getMyShop();
                    if (res && res.success && res.data) {
                        currentShopInfo = res.data;
                    }
                } catch (e) {
                    console.warn('Could not fetch latest shop info', e);
                }

                if (currentShopInfo) {
                    const shopNameEl = document.getElementById('modal-shop-name');
                    const shopIdBadge = document.getElementById('modal-shop-id-badge');
                    const qrImg = document.getElementById('shop-qr-img');
                    const customerUrlEl = document.getElementById('modal-customer-url');

                    if (shopNameEl) shopNameEl.textContent = currentShopInfo.name;
                    if (shopIdBadge) shopIdBadge.textContent = currentShopInfo.shop_id;
                    if (qrImg) qrImg.src = config.API_BASE_URL + `/shops/${encodeURIComponent(currentShopInfo.shop_id)}/qr/`;
                    const custUrl = currentShopInfo.customer_url || `${window.location.origin}/?shop=${currentShopInfo.shop_id}`;
                    if (customerUrlEl) customerUrlEl.textContent = custUrl;

                    qrModal.style.display = 'flex';
                }
            });
        }

        if (qrCloseBtn) {
            qrCloseBtn.addEventListener('click', () => {
                qrModal.style.display = 'none';
            });
        }

        if (printQrBtn) {
            printQrBtn.addEventListener('click', () => {
                const qrImgSrc = document.getElementById('shop-qr-img').src;
                const shopName = document.getElementById('modal-shop-name').textContent;
                const shopId = document.getElementById('modal-shop-id-badge').textContent;
                const customerUrl = document.getElementById('modal-customer-url').textContent;

                const printWindow = window.open('', '_blank', 'width=600,height=700');
                printWindow.document.write(`
                    <!DOCTYPE html>
                    <html>
                    <head>
                        <title>Countertop QR - ${shopName}</title>
                        <style>
                            body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; text-align: center; padding: 40px; color: #111; }
                            .card { border: 2px dashed #2563eb; border-radius: 16px; padding: 30px; display: inline-block; max-width: 380px; }
                            h1 { margin: 0 0 8px 0; font-size: 24px; color: #1e3a8a; }
                            .tagline { color: #64748b; font-size: 14px; margin-bottom: 20px; }
                            img { width: 220px; height: 220px; margin: 0 auto; display: block; }
                            .instructions { margin-top: 18px; font-size: 15px; font-weight: 600; color: #0f172a; }
                            .subtext { margin-top: 8px; font-size: 12px; color: #64748b; word-break: break-all; }
                            .badge { background: #e0f2fe; color: #0369a1; padding: 4px 12px; border-radius: 999px; font-size: 12px; font-weight: 700; display: inline-block; margin-top: 14px; }
                        </style>
                    </head>
                    <body>
                        <div class="card">
                            <h1>PrintX Counter</h1>
                            <div class="tagline">Scan &amp; Print Documents Instantly</div>
                            <img src="${qrImgSrc}" alt="QR Code" />
                            <div class="instructions">Scan with phone camera to send prints directly here</div>
                            <div class="badge">${shopName} &bull; ${shopId}</div>
                            <div class="subtext">${customerUrl}</div>
                        </div>
                        <script>
                            window.onload = function() { window.print(); };
                        <\/script>
                    </body>
                    </html>
                `);
                printWindow.document.close();
            });
        }

        if (copyLinkBtn) {
            copyLinkBtn.addEventListener('click', () => {
                const url = document.getElementById('modal-customer-url').textContent;
                navigator.clipboard.writeText(url).then(() => {
                    if (window.PrintXNotify) {
                        window.PrintXNotify.success('Shop URL copied to clipboard!');
                    }
                });
            });
        }

        tableBody = document.getElementById('orders-table-body');
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

        const clearAllBtn = document.getElementById('clear-all-orders-btn');
        if (clearAllBtn) {
            clearAllBtn.addEventListener('click', () => {
                actions.handleClearAllOrders(clearAllBtn, () => {
                    currentPage = 1;
                    fetchOrders(true);
                });
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

        // Automatic 30-minute dashboard check & refresh (without requiring manual page refresh)
        setInterval(() => {
            fetchOrders(false);
        }, 30 * 60 * 1000);
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

    // Set to keep track of open user group accordions across polling cycles
    const expandedGroupKeys = new Set();

    function formatOrderId(num) {
        if (!num) return 'ORD id 101';
        const str = String(num).trim();
        if (str.startsWith('ORD id')) return str;
        return `ORD id ${str}`;
    }

    function formatDateTime(isoStr) {
        if (!isoStr) return '';
        try {
            const d = new Date(isoStr);
            const timeStr = d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
            const dateStr = d.toLocaleDateString([], { month: 'short', day: 'numeric' });
            return `${dateStr}, ${timeStr}`;
        } catch {
            return String(isoStr).substring(0, 16);
        }
    }

    function createOrderActionButtons(order) {
        const isCashPending = order.payment_status === 'cash_pending' || order.is_cash_pending;
        const isBlocked = order.approval_status === 'blocked';
        const isPrinted = order.status === 'completed' || order.status === 'submitted_to_printer';
        const isPrinting = order.status === 'submitting_to_printer' || order.status === 'downloading' || order.status === 'ready_to_print';

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

        // Button 2: Print Button
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

        // Button 3: Compact Pay OK if cash is pending
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

        return btnGroup;
    }

    function createSingleFileOrderRow(order) {
        const row = document.createElement('tr');
        row.id = `order-row-${order.id}`;
        row.className = 'order-row';

        const isCashPending = order.payment_status === 'cash_pending' || order.is_cash_pending;
        const isBlocked = order.approval_status === 'blocked';

        if (isCashPending) {
            row.classList.add('order-row-cash-pending');
        }
        row.classList.add(`order-status-${order.status}`);
        if (isBlocked) {
            row.classList.add('order-blocked');
        }

        const file = order.files[0];

        // 1. Filename Cell with Customer and View/Download actions
        const fileCell = document.createElement('td');
        fileCell.className = 'col-filename';

        const fileSpan = document.createElement('span');
        fileSpan.className = 'document-filename';
        fileSpan.title = file.original_filename || '';
        fileSpan.innerHTML = `&#128196; ${escapeHtml(file.original_filename || 'document.pdf')}`;

        const metaSpan = document.createElement('div');
        metaSpan.className = 'document-meta';
        metaSpan.textContent = `${file.page_count || 1}p • ${file.copies || 1} copy • ${(file.colour_mode || 'bw').toUpperCase()} • ${file.paper_size || 'A4'}${order.customer_name ? ` • 👤 ${order.customer_name}` : ''}${order.customer_phone ? ` (📞 ${order.customer_phone})` : ''}`;

        fileCell.appendChild(fileSpan);
        fileCell.appendChild(metaSpan);

        // 2. Order ID Cell
        const idCell = document.createElement('td');
        idCell.className = 'col-order-id';
        const idSpan = document.createElement('span');
        idSpan.className = 'order-id-badge';
        idSpan.textContent = formatOrderId(order.order_number || order.job_number);
        idCell.appendChild(idSpan);

        // 3. Print / Approval Status Cell with Date
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

        if (order.created_at) {
            const timeEl = document.createElement('div');
            timeEl.className = 'document-meta';
            timeEl.style.marginTop = '4px';
            timeEl.textContent = `🕒 ${formatDateTime(order.created_at)}`;
            statusCell.appendChild(timeEl);
        }

        // 4. Payment Status Cell
        const paymentCell = document.createElement('td');
        paymentCell.className = 'col-payment';
        const paymentBadge = document.createElement('span');
        paymentBadge.className = `badge badge-pay-${order.payment_status}`;
        paymentBadge.textContent = formatPaymentLabel(order.payment_status);
        paymentCell.appendChild(paymentBadge);

        if (order.total_amount) {
            const priceEl = document.createElement('div');
            priceEl.className = 'document-meta';
            priceEl.style.marginTop = '4px';
            priceEl.style.fontWeight = '600';
            priceEl.textContent = `${order.currency || 'PKR'} ${order.total_amount}`;
            paymentCell.appendChild(priceEl);
        }

        // 5. Actions Cell
        const actionCell = document.createElement('td');
        actionCell.className = 'col-actions';
        const btnGroup = document.createElement('div');
        btnGroup.className = 'action-btn-group';

        const viewLink = document.createElement('a');
        viewLink.href = encodeURI(file.view_url || `/api/v1/admin/print-jobs/${file.id}/download/?inline=1`);
        viewLink.target = '_blank';
        viewLink.rel = 'noopener noreferrer';
        viewLink.className = 'btn btn-outline-info btn-sm';
        viewLink.title = `View ${file.original_filename || 'PDF'}`;
        viewLink.innerHTML = '&#128065; View';

        const dlLink = document.createElement('a');
        dlLink.href = encodeURI(file.download_url || `/api/v1/admin/print-jobs/${file.id}/download/`);
        dlLink.className = 'btn btn-outline-secondary btn-sm';
        dlLink.title = `Download ${file.original_filename || 'PDF'}`;
        dlLink.setAttribute('download', file.original_filename || 'document.pdf');
        dlLink.innerHTML = '&#11015; Download';

        btnGroup.appendChild(viewLink);
        btnGroup.appendChild(dlLink);

        const orderActions = createOrderActionButtons(order);
        Array.from(orderActions.children).forEach((btn) => btnGroup.appendChild(btn));

        actionCell.appendChild(btnGroup);

        row.appendChild(fileCell);
        row.appendChild(idCell);
        row.appendChild(statusCell);
        row.appendChild(paymentCell);
        row.appendChild(actionCell);

        return row;
    }

    function createMultiFileOrderHeaderRow(order, isExpanded, toggleCallback) {
        const row = document.createElement('tr');
        row.id = `group-header-${order.id}`;
        row.className = `order-row order-group-header-row ${isExpanded ? 'group-expanded' : ''}`;

        const isCashPending = order.payment_status === 'cash_pending' || order.is_cash_pending;
        const isBlocked = order.approval_status === 'blocked';

        if (isCashPending) {
            row.classList.add('order-row-cash-pending');
        }
        if (isBlocked) {
            row.classList.add('order-blocked');
        }

        // 1. Filename Cell with See More Arrow Button
        const fileCell = document.createElement('td');
        fileCell.className = 'col-filename';

        const wrapper = document.createElement('div');
        wrapper.className = 'group-header-flex';

        // Prominent See More Arrow Button
        const toggleBtn = document.createElement('button');
        toggleBtn.type = 'button';
        toggleBtn.className = `btn btn-see-more-toggle ${isExpanded ? 'is-open' : ''}`;
        toggleBtn.title = isExpanded ? 'Hide documents list' : `See more (${order.files.length} PDFs uploaded)`;
        toggleBtn.innerHTML = `
            <span class="see-more-arrow">${isExpanded ? '&#9650;' : '&#9660;'}</span>
            <span class="see-more-label">${isExpanded ? 'Hide' : 'See More'} (${order.files.length} PDFs)</span>
        `;
        toggleBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            toggleCallback();
        });

        const customerBadge = document.createElement('span');
        customerBadge.className = 'customer-badge';
        customerBadge.innerHTML = `&#128100; <strong>${escapeHtml(order.customer_name || 'Customer')}</strong>${order.customer_phone ? ` • ${escapeHtml(order.customer_phone)}` : ''}`;

        wrapper.appendChild(toggleBtn);
        wrapper.appendChild(customerBadge);

        const summaryDesc = document.createElement('div');
        summaryDesc.className = 'group-summary-meta';
        summaryDesc.textContent = `${order.files.length} documents • Total ${order.total_impressions} impressions • ~${order.estimated_sheets} sheets`;

        fileCell.appendChild(wrapper);
        fileCell.appendChild(summaryDesc);

        // 2. Order ID Cell
        const idCell = document.createElement('td');
        idCell.className = 'col-order-id';
        const idSpan = document.createElement('span');
        idSpan.className = 'order-id-badge group-id-badge';
        idSpan.textContent = formatOrderId(order.order_number || order.job_number);
        const moreCountBadge = document.createElement('span');
        moreCountBadge.className = 'badge-more-count';
        moreCountBadge.textContent = `${order.files.length} PDFs`;
        idCell.appendChild(idSpan);
        idCell.appendChild(moreCountBadge);

        // 3. Status Cell
        const statusCell = document.createElement('td');
        statusCell.className = 'col-status';
        const statusBadge = document.createElement('span');
        if (isBlocked) {
            statusBadge.className = 'badge badge-blocked';
            statusBadge.textContent = 'Blocked';
        } else if (order.status === 'completed') {
            statusBadge.className = 'badge badge-completed';
            statusBadge.textContent = `Completed (${order.files.length})`;
        } else if (order.status === 'submitting_to_printer' || order.status === 'submitted_to_printer') {
            statusBadge.className = 'badge badge-printing';
            statusBadge.textContent = 'Printing In Progress';
        } else {
            statusBadge.className = 'badge badge-queued';
            statusBadge.textContent = `Queued (${order.files.length} PDFs)`;
        }
        statusCell.appendChild(statusBadge);

        if (order.created_at) {
            const timeEl = document.createElement('div');
            timeEl.className = 'document-meta';
            timeEl.style.marginTop = '4px';
            timeEl.textContent = `🕒 ${formatDateTime(order.created_at)}`;
            statusCell.appendChild(timeEl);
        }

        // 4. Payment Cell
        const paymentCell = document.createElement('td');
        paymentCell.className = 'col-payment';
        const paymentBadge = document.createElement('span');
        paymentBadge.className = `badge badge-pay-${order.payment_status}`;
        paymentBadge.textContent = formatPaymentLabel(order.payment_status);
        paymentCell.appendChild(paymentBadge);

        if (order.total_amount) {
            const priceEl = document.createElement('div');
            priceEl.className = 'document-meta';
            priceEl.style.marginTop = '4px';
            priceEl.style.fontWeight = '600';
            priceEl.textContent = `${order.currency || 'PKR'} ${order.total_amount}`;
            paymentCell.appendChild(priceEl);
        }

        // 5. Actions Cell
        const actionCell = document.createElement('td');
        actionCell.className = 'col-actions';
        const btnGroup = document.createElement('div');
        btnGroup.className = 'action-btn-group';

        const quickToggle = document.createElement('button');
        quickToggle.type = 'button';
        quickToggle.className = `btn btn-sm ${isExpanded ? 'btn-outline-secondary' : 'btn-outline-primary'}`;
        quickToggle.innerHTML = isExpanded ? '&#9650; Collapse' : '&#9660; View All PDFs';
        quickToggle.addEventListener('click', (e) => {
            e.stopPropagation();
            toggleCallback();
        });
        btnGroup.appendChild(quickToggle);

        const orderActions = createOrderActionButtons(order);
        Array.from(orderActions.children).forEach((btn) => btnGroup.appendChild(btn));

        actionCell.appendChild(btnGroup);

        row.appendChild(fileCell);
        row.appendChild(idCell);
        row.appendChild(statusCell);
        row.appendChild(paymentCell);
        row.appendChild(actionCell);

        return row;
    }

    function createSubFileRow(order, file, index, totalFiles) {
        const row = document.createElement('tr');
        row.id = `sub-file-row-${file.id}`;
        row.className = 'order-row order-sub-row animate-fade-in';

        // 1. Filename Cell with tree indicator and View/Download buttons
        const fileCell = document.createElement('td');
        fileCell.className = 'col-filename col-sub-filename';

        const treeBox = document.createElement('div');
        treeBox.className = 'sub-file-tree-box';

        const branchIcon = document.createElement('span');
        branchIcon.className = 'tree-branch-symbol';
        branchIcon.innerHTML = '&rdsh;';

        const docIcon = document.createElement('span');
        docIcon.className = 'sub-doc-icon';
        docIcon.innerHTML = '&#128196;';

        const fileSpan = document.createElement('span');
        fileSpan.className = 'document-filename sub-document-filename';
        fileSpan.title = file.original_filename;
        fileSpan.textContent = file.original_filename;

        treeBox.appendChild(branchIcon);
        treeBox.appendChild(docIcon);
        treeBox.appendChild(fileSpan);

        const metaSpan = document.createElement('div');
        metaSpan.className = 'document-meta sub-document-meta';
        metaSpan.textContent = `PDF #${index + 1} of ${totalFiles} • ${file.page_count || 1}p • ${file.copies || 1} copy • ${(file.colour_mode || 'bw').toUpperCase()} • ${file.paper_size || 'A4'}`;

        fileCell.appendChild(treeBox);
        fileCell.appendChild(metaSpan);

        // 2. Order ID Cell (clean / empty; order ID is displayed in header row above)
        const idCell = document.createElement('td');
        idCell.className = 'col-order-id col-sub-empty';

        // 3. Status Cell (clean / empty; queue status is displayed in header row above)
        const statusCell = document.createElement('td');
        statusCell.className = 'col-status col-sub-empty';

        // 4. Payment Cell (clean / empty; payment status is displayed in header row above)
        const paymentCell = document.createElement('td');
        paymentCell.className = 'col-payment col-sub-empty';

        // 5. Actions Cell: Functional View and Download actions on the right side of the row
        const actionCell = document.createElement('td');
        actionCell.className = 'col-actions';
        const subActionGroup = document.createElement('div');
        subActionGroup.className = 'action-btn-group';

        const subViewLink = document.createElement('a');
        subViewLink.href = encodeURI(file.view_url || `/api/v1/admin/print-jobs/${file.id}/download/?inline=1`);
        subViewLink.target = '_blank';
        subViewLink.rel = 'noopener noreferrer';
        subViewLink.className = 'btn btn-outline-info btn-sm';
        subViewLink.title = `View ${file.original_filename || 'PDF'}`;
        subViewLink.innerHTML = '&#128065; View';

        const subDlLink = document.createElement('a');
        subDlLink.href = encodeURI(file.download_url || `/api/v1/admin/print-jobs/${file.id}/download/`);
        subDlLink.className = 'btn btn-outline-secondary btn-sm';
        subDlLink.title = `Download ${file.original_filename || 'PDF'}`;
        subDlLink.setAttribute('download', file.original_filename || 'document.pdf');
        subDlLink.innerHTML = '&#11015; Download';

        subActionGroup.appendChild(subViewLink);
        subActionGroup.appendChild(subDlLink);
        actionCell.appendChild(subActionGroup);

        row.appendChild(fileCell);
        row.appendChild(idCell);
        row.appendChild(statusCell);
        row.appendChild(paymentCell);
        row.appendChild(actionCell);

        return row;
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
            const files = (order.files && order.files.length > 0)
                ? order.files
                : [{
                    id: order.id,
                    original_filename: order.original_filename || 'document.pdf',
                    page_count: order.page_count || 1,
                    copies: order.copies || 1,
                    colour_mode: order.colour_mode || 'bw',
                    paper_size: order.paper_size || 'A4',
                    download_url: `/api/v1/admin/print-jobs/${order.id}/download/`,
                    view_url: `/api/v1/admin/print-jobs/${order.id}/download/?inline=1`,
                    file_available: true
                }];
            order.files = files;

            if (files.length === 1) {
                // User has only 1 PDF: render single clean row with direct view and download buttons
                const singleRow = createSingleFileOrderRow(order);
                tableBody.appendChild(singleRow);
            } else {
                // User has MORE than 1 PDF uploaded in this single order!
                // Render order header with 'See More' arrow dropdown
                const isExpanded = expandedGroupKeys.has(order.id);
                const headerRow = createMultiFileOrderHeaderRow(order, isExpanded, () => {
                    if (expandedGroupKeys.has(order.id)) {
                        expandedGroupKeys.delete(order.id);
                    } else {
                        expandedGroupKeys.add(order.id);
                    }
                    renderOrdersTable(orders);
                });
                tableBody.appendChild(headerRow);

                // If expanded, render each PDF as a distinct sub-row with action buttons in front of each PDF
                if (isExpanded) {
                    files.forEach((fileItem, idx) => {
                        const subRow = createSubFileRow(order, fileItem, idx, files.length);
                        tableBody.appendChild(subRow);
                    });
                }
            }
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
