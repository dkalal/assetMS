/**
 * Asset Transfer Management Dashboard
 * World-class transfer approval interface with real-time updates
 */

(function () {
    'use strict';

    // Configuration
    const CONFIG = {
        POLL_INTERVAL: 30000, // 30 seconds
        API_BASE: '/assets/api/transfers',
    };

    // Utility Functions
    function getCSRFToken() {
        return document.querySelector('[name=csrfmiddlewaretoken]')?.value ||
               document.cookie.split('; ').find(row => row.startsWith('csrftoken='))?.split('=')[1] ||
               '';
    }

    function formatDate(isoString) {
        if (!isoString) return 'N/A';
        const date = new Date(isoString);
        return date.toLocaleDateString('en-US', { 
            year: 'numeric', 
            month: 'short', 
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    }

    function formatRelativeTime(isoString) {
        if (!isoString) return '';
        const date = new Date(isoString);
        const now = new Date();
        const diffMs = now - date;
        const diffMins = Math.round(diffMs / 60000);
        
        if (diffMins < 1) return 'Just now';
        if (diffMins < 60) return `${diffMins}min ago`;
        const diffHours = Math.round(diffMins / 60);
        if (diffHours < 24) return `${diffHours}h ago`;
        const diffDays = Math.round(diffHours / 24);
        return `${diffDays}d ago`;
    }

    function showToast(message, type = 'info') {
        // Use existing toast system if available
        if (window.showToast) {
            window.showToast(message, type);
            return;
        }
        
        // Fallback to alert
        alert(message);
    }

    // Transfer Dashboard Manager
    class TransferDashboard {
        constructor() {
            this.transfers = [];
            this.filteredTransfers = [];
            this.currentUser = this.getUserInfo();
            this.modals = this.initializeModals();
            
            this.bindEvents();
            this.loadInitialData();
            this.startPolling();
        }

        getUserInfo() {
            const userMeta = document.querySelector('[data-user-role]');
            return {
                id: parseInt(userMeta?.dataset.userId || '0', 10),
                role: (userMeta?.dataset.userRole || 'user').toLowerCase()
            };
        }

        initializeModals() {
            // WORLD-CLASS: Fix accessibility issue with aria-hidden on focused elements
            const modals = {
                detail: new bootstrap.Modal(document.getElementById('transferDetailModal')),
                decision: new bootstrap.Modal(document.getElementById('decisionModal'))
            };
            
            // Fix aria-hidden accessibility warning
            // Remove aria-hidden when modal is shown, add it back when hidden
            Object.values(modals).forEach(modal => {
                const modalEl = modal._element;
                if (modalEl) {
                    modalEl.addEventListener('shown.bs.modal', function() {
                        this.removeAttribute('aria-hidden');
                    });
                    
                    modalEl.addEventListener('hidden.bs.modal', function() {
                        this.setAttribute('aria-hidden', 'true');
                    });
                }
            });
            
            // Also fix for initiate and bulk transfer modals
            ['initiateTransferModal', 'bulkTransferModal'].forEach(modalId => {
                const modalEl = document.getElementById(modalId);
                if (modalEl) {
                    modalEl.addEventListener('shown.bs.modal', function() {
                        this.removeAttribute('aria-hidden');
                    });
                    
                    modalEl.addEventListener('hidden.bs.modal', function() {
                        this.setAttribute('aria-hidden', 'true');
                    });
                }
            });
            
            return modals;
        }

        bindEvents() {
            // Search and filters
            document.getElementById('searchInput')?.addEventListener('input', 
                this.debounce(() => this.applyFilters(), 300));
            
            document.getElementById('filterStatus')?.addEventListener('change', 
                () => this.applyFilters());
            
            document.getElementById('filterRole')?.addEventListener('change', 
                () => this.applyFilters());
            
            document.getElementById('filterDate')?.addEventListener('change', 
                () => this.applyFilters());
            
            document.getElementById('clearFilters')?.addEventListener('click', 
                () => this.clearFilters());

            // Tab switching
            document.querySelectorAll('[data-bs-toggle="tab"]').forEach(tab => {
                tab.addEventListener('shown.bs.tab', (e) => {
                    const target = e.target.getAttribute('data-bs-target');
                    this.renderTab(target);
                });
            });
        }

        debounce(func, wait) {
            let timeout;
            return function executedFunction(...args) {
                const later = () => {
                    clearTimeout(timeout);
                    func(...args);
                };
                clearTimeout(timeout);
                timeout = setTimeout(later, wait);
            };
        }

        async loadInitialData() {
            try {
                await this.fetchTransfers();
                this.updateStatistics();
                this.renderTab('#pending'); // Render initial tab
            } catch (error) {
                console.error('Failed to load transfers:', error);
                showToast('Failed to load transfers. Please refresh the page.', 'danger');
            }
        }

        async fetchTransfers() {
            // In production, this would call the actual API
            // For now, simulate API call
            const response = await fetch(`${CONFIG.API_BASE}/list/`, {
                headers: {
                    'Accept': 'application/json',
                    'X-CSRFToken': getCSRFToken()
                }
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

            const data = await response.json();
            this.transfers = data.transfers || [];
            this.filteredTransfers = [...this.transfers];
        }

        updateStatistics() {
            const stats = {
                total: this.transfers.length,
                pending: this.transfers.filter(t => this.isPending(t)).length,
                completed: this.transfers.filter(t => t.state === 'completed').length,
                rejected: this.transfers.filter(t => 
                    t.state === 'receiver_rejected' || t.state === 'cancelled'
                ).length
            };

            document.getElementById('stat-total').textContent = stats.total;
            document.getElementById('stat-pending').textContent = stats.pending;
            document.getElementById('stat-completed').textContent = stats.completed;
            document.getElementById('stat-rejected').textContent = stats.rejected;
            document.getElementById('badge-pending').textContent = stats.pending;
        }

        isPending(transfer) {
            const { state, to_user_id } = transfer;
            const isReceiver = to_user_id === this.currentUser.id;
            const isAdmin = ['admin', 'manager'].includes(this.currentUser.role);
            
            return (state === 'pending_receiver' && isReceiver) ||
                   (state === 'awaiting_admin' && isAdmin);
        }

        applyFilters() {
            const search = document.getElementById('searchInput')?.value.toLowerCase() || '';
            const status = document.getElementById('filterStatus')?.value || '';
            const role = document.getElementById('filterRole')?.value || '';
            const dateRange = document.getElementById('filterDate')?.value || '';

            this.filteredTransfers = this.transfers.filter(transfer => {
                // Search filter
                if (search) {
                    const searchText = `
                        ${transfer.asset?.name || ''}
                        ${transfer.from_user?.name || ''}
                        ${transfer.to_user?.name || ''}
                        ${transfer.reason || ''}
                    `.toLowerCase();
                    
                    if (!searchText.includes(search)) return false;
                }

                // Status filter
                if (status && transfer.state !== status) return false;

                // Role filter
                if (role) {
                    if (role === 'receiver' && transfer.to_user_id !== this.currentUser.id) return false;
                    if (role === 'initiator' && transfer.initiator_id !== this.currentUser.id) return false;
                    if (role === 'admin' && transfer.state !== 'awaiting_admin') return false;
                }

                // Date filter
                if (dateRange) {
                    const now = new Date();
                    const createdAt = new Date(transfer.created_at);
                    const diffDays = (now - createdAt) / (1000 * 60 * 60 * 24);
                    
                    if (dateRange === 'today' && diffDays > 1) return false;
                    if (dateRange === 'week' && diffDays > 7) return false;
                    if (dateRange === 'month' && diffDays > 30) return false;
                }

                return true;
            });

            this.renderCurrentTab();
        }

        clearFilters() {
            document.getElementById('searchInput').value = '';
            document.getElementById('filterStatus').value = '';
            document.getElementById('filterRole').value = '';
            document.getElementById('filterDate').value = '';
            this.applyFilters();
        }

        renderCurrentTab() {
            const activeTab = document.querySelector('.nav-link.active');
            const target = activeTab?.getAttribute('data-bs-target');
            if (target) {
                this.renderTab(target);
            }
        }

        renderTab(target) {
            switch (target) {
                case '#pending':
                    this.renderPendingTransfers();
                    break;
                case '#all':
                    this.renderAllTransfers();
                    break;
                case '#history':
                    this.renderHistoryTransfers();
                    break;
            }
        }

        renderPendingTransfers() {
            const container = document.getElementById('pending-transfers-list');
            const pending = this.filteredTransfers.filter(t => this.isPending(t));

            if (!pending.length) {
                container.innerHTML = `
                    <div class="empty-state">
                        <i class="bi bi-check-circle"></i>
                        <h5>All caught up!</h5>
                        <p>No pending transfers requiring your action.</p>
                    </div>
                `;
                return;
            }

            container.innerHTML = pending.map(t => this.renderTransferCard(t, true)).join('');
        }

        renderAllTransfers() {
            const container = document.getElementById('all-transfers-list');
            
            if (!this.filteredTransfers.length) {
                container.innerHTML = `
                    <div class="empty-state">
                        <i class="bi bi-inbox"></i>
                        <h5>No transfers found</h5>
                        <p>Try adjusting your filters.</p>
                    </div>
                `;
                return;
            }

            container.innerHTML = this.filteredTransfers.map(t => this.renderTransferCard(t, false)).join('');
        }

        renderHistoryTransfers() {
            const container = document.getElementById('history-transfers-list');
            const history = this.filteredTransfers.filter(t => 
                t.state === 'completed' || t.state === 'receiver_rejected' || t.state === 'cancelled'
            );

            if (!history.length) {
                container.innerHTML = `
                    <div class="empty-state">
                        <i class="bi bi-clock-history"></i>
                        <h5>No transfer history</h5>
                        <p>Completed and rejected transfers will appear here.</p>
                    </div>
                `;
                return;
            }

            container.innerHTML = history.map(t => this.renderTransferCard(t, false)).join('');
        }

        renderTransferCard(transfer, showActions) {
            const stateClass = this.getStateClass(transfer.state);
            const stateIcon = this.getStateIcon(transfer.state);
            const canApprove = this.canApprove(transfer);
            const canReject = this.canReject(transfer);

            return `
                <div class="transfer-card">
                    <div class="row align-items-start">
                        <div class="col-md-8">
                            <div class="d-flex align-items-start gap-3 mb-3">
                                <div class="flex-shrink-0">
                                    <div class="timeline-icon ${stateClass}">
                                        <i class="bi bi-${stateIcon}"></i>
                                    </div>
                                </div>
                                <div class="flex-grow-1">
                                    <h5 class="mb-1">
                                        <strong>${transfer.asset?.name || `Asset #${transfer.asset_id}`}</strong>
                                    </h5>
                                    <div class="text-muted small mb-2">
                                        <i class="bi bi-arrow-right me-1"></i>
                                        From <strong>${transfer.from_user?.name || (transfer.from_branch?.name || 'Head Office')}</strong>
                                        to <strong>${transfer.to_user?.name || (transfer.to_branch?.name || 'N/A')}</strong>
                                    </div>
                                    ${transfer.reason ? `
                                        <div class="small text-secondary mb-2">
                                            <i class="bi bi-chat-quote me-1"></i>
                                            <em>"${transfer.reason}"</em>
                                        </div>
                                    ` : ''}
                                    <span class="transfer-badge ${stateClass}">
                                        <i class="bi bi-${stateIcon}"></i>
                                        ${this.getStateLabel(transfer.state)}
                                    </span>
                                </div>
                            </div>
                            
                            <!-- Timeline -->
                            <div class="ms-5">
                                ${this.renderTimeline(transfer)}
                            </div>
                        </div>
                        
                        <div class="col-md-4">
                            <div class="text-muted small mb-3">
                                <div><strong>Created:</strong> ${formatRelativeTime(transfer.created_at)}</div>
                                <div><strong>ID:</strong> #${transfer.id}</div>
                                ${transfer.from_branch ? `<div><strong>From:</strong> ${transfer.from_branch.name}</div>` : ''}
                                ${transfer.to_branch ? `<div><strong>To:</strong> ${transfer.to_branch.name}</div>` : ''}
                            </div>
                            
                            ${showActions && (canApprove || canReject) ? `
                                <div class="action-buttons">
                                    ${canApprove ? `
                                        <button class="btn btn-success btn-action" 
                                                onclick="transferDashboard.handleDecision(${transfer.id}, 'approved')">
                                            <i class="bi bi-check-circle me-1"></i>Approve
                                        </button>
                                    ` : ''}
                                    ${canReject ? `
                                        <button class="btn btn-danger btn-action"
                                                onclick="transferDashboard.handleDecision(${transfer.id}, 'rejected')">
                                            <i class="bi bi-x-circle me-1"></i>Reject
                                        </button>
                                    ` : ''}
                                </div>
                            ` : ''}
                            
                            <button class="btn btn-outline-secondary btn-sm w-100 mt-2"
                                    onclick="transferDashboard.showDetail(${transfer.id})">
                                <i class="bi bi-eye me-1"></i>View Details
                            </button>
                        </div>
                    </div>
                </div>
            `;
        }

        renderTimeline(transfer) {
            const steps = [];
            
            // Initiated
            steps.push({
                label: 'Transfer Initiated',
                date: transfer.created_at,
                user: transfer.initiator?.name,
                icon: 'play-circle',
                state: 'completed'
            });

            // Receiver decision
            if (transfer.receiver_decided_at) {
                steps.push({
                    label: transfer.receiver_decision === 'approved' ? 'Receiver Approved' : 'Receiver Rejected',
                    date: transfer.receiver_decided_at,
                    user: transfer.to_user?.name,
                    comment: transfer.receiver_comment,
                    icon: transfer.receiver_decision === 'approved' ? 'check-circle' : 'x-circle',
                    state: transfer.receiver_decision === 'approved' ? 'completed' : 'rejected'
                });
            } else if (transfer.state === 'pending_receiver') {
                steps.push({
                    label: 'Awaiting Receiver Approval',
                    icon: 'hourglass-split',
                    state: 'pending'
                });
            }

            // Admin decision
            if (transfer.admin_decided_at) {
                steps.push({
                    label: transfer.admin_decision === 'approved' ? 'Admin Approved' : 'Admin Rejected',
                    date: transfer.admin_decided_at,
                    user: transfer.approved_by?.name,
                    comment: transfer.admin_comment,
                    icon: transfer.admin_decision === 'approved' ? 'shield-check' : 'shield-x',
                    state: transfer.admin_decision === 'approved' ? 'completed' : 'rejected'
                });
            } else if (transfer.state === 'awaiting_admin') {
                steps.push({
                    label: 'Awaiting Admin Approval',
                    icon: 'hourglass-split',
                    state: 'awaiting'
                });
            }

            return steps.map((step, idx) => `
                <div class="timeline-step ${idx < steps.length - 1 ? 'has-next' : ''}">
                    <div class="timeline-icon ${step.state}">
                        <i class="bi bi-${step.icon}"></i>
                    </div>
                    <div>
                        <div class="fw-semibold">${step.label}</div>
                        ${step.date ? `<div class="text-muted small">${formatDate(step.date)}</div>` : ''}
                        ${step.user ? `<div class="text-muted small">by ${step.user}</div>` : ''}
                        ${step.comment ? `<div class="small text-secondary fst-italic mt-1">"${step.comment}"</div>` : ''}
                    </div>
                </div>
            `).join('');
        }

        getStateClass(state) {
            const map = {
                'pending_receiver': 'pending',
                'receiver_approved': 'approved',
                'receiver_rejected': 'rejected',
                'awaiting_admin': 'awaiting',
                'completed': 'completed',
                'cancelled': 'rejected'
            };
            return map[state] || 'pending';
        }

        getStateIcon(state) {
            const map = {
                'pending_receiver': 'hourglass-split',
                'receiver_approved': 'check-circle',
                'receiver_rejected': 'x-circle',
                'awaiting_admin': 'hourglass',
                'completed': 'check-circle-fill',
                'cancelled': 'x-octagon'
            };
            return map[state] || 'circle';
        }

        getStateLabel(state) {
            return state.split('_').map(word => 
                word.charAt(0).toUpperCase() + word.slice(1)
            ).join(' ');
        }

        canApprove(transfer) {
            const { state, to_user_id } = transfer;
            const isReceiver = to_user_id === this.currentUser.id;
            const isAdmin = ['admin', 'manager'].includes(this.currentUser.role);
            
            return (state === 'pending_receiver' && isReceiver) ||
                   (state === 'awaiting_admin' && isAdmin);
        }

        canReject(transfer) {
            return this.canApprove(transfer);
        }

        handleDecision(transferId, decision) {
            const transfer = this.transfers.find(t => t.id === transferId);
            if (!transfer) return;

            const isApproval = decision === 'approved';
            const modalTitle = isApproval ? 'Approve Transfer' : 'Reject Transfer';
            const modalMessage = isApproval 
                ? 'This will move the asset to the next approval stage.'
                : 'This will cancel the transfer request. The initiator will be notified.';
            
            const modal = this.modals.decision;
            document.getElementById('decisionModalTitle').textContent = modalTitle;
            document.getElementById('decisionMessage').textContent = modalMessage;
            document.getElementById('decisionComment').value = '';
            
            const confirmBtn = document.getElementById('confirmDecisionBtn');
            confirmBtn.className = `btn ${isApproval ? 'btn-success' : 'btn-danger'}`;
            confirmBtn.textContent = isApproval ? 'Approve' : 'Reject';
            
            confirmBtn.onclick = () => {
                this.submitDecision(transfer, decision);
                modal.hide();
            };
            
            modal.show();
        }

        async submitDecision(transfer, decision) {
            const comment = document.getElementById('decisionComment').value;
            const isReceiver = transfer.state === 'pending_receiver';
            const endpoint = isReceiver ? '/receiver-decision/' : '/admin-review/';
            
            try {
                const response = await fetch(`${CONFIG.API_BASE}${endpoint}`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': getCSRFToken(),
                        'Accept': 'application/json'
                    },
                    body: JSON.stringify({
                        transfer_id: transfer.id,
                        decision: decision,
                        comment: comment
                    })
                });

                const data = await response.json();
                
                if (!response.ok || !data.success) {
                    throw new Error(data.error || `HTTP ${response.status}`);
                }

                showToast(`Transfer ${decision} successfully!`, 'success');
                await this.fetchTransfers();
                this.updateStatistics();
                this.renderCurrentTab();
                
            } catch (error) {
                console.error('Decision failed:', error);
                showToast(`Failed to ${decision} transfer: ${error.message}`, 'danger');
            }
        }

        showDetail(transferId) {
            const transfer = this.transfers.find(t => t.id === transferId);
            if (!transfer) return;

            const modalBody = document.getElementById('transferDetailBody');
            modalBody.innerHTML = this.renderDetailView(transfer);
            this.modals.detail.show();
        }

        renderDetailView(transfer) {
            return `
                <div class="row g-3">
                    <div class="col-12">
                        <h6 class="text-muted mb-3">Transfer Information</h6>
                        <table class="table table-sm">
                            <tr><th width="30%">Transfer ID</th><td>#${transfer.id}</td></tr>
                            <tr><th>Asset</th><td>${transfer.asset?.name || `#${transfer.asset_id}`}</td></tr>
                            <tr><th>Asset UUID</th><td><code>${transfer.asset?.uuid || 'N/A'}</code></td></tr>
                            <tr><th>Status</th><td><span class="transfer-badge ${this.getStateClass(transfer.state)}">${this.getStateLabel(transfer.state)}</span></td></tr>
                            <tr><th>Created</th><td>${formatDate(transfer.created_at)}</td></tr>
                        </table>
                    </div>
                    
                    <div class="col-md-6">
                        <h6 class="text-muted mb-3">From</h6>
                        <div class="card bg-light">
                            <div class="card-body">
                                ${transfer.from_user ? `<div><strong>User:</strong> ${transfer.from_user.name}</div>` : ''}
                                ${transfer.from_branch ? `<div><strong>Branch:</strong> ${transfer.from_branch.name}</div>` : '<div><strong>Location:</strong> Head Office</div>'}
                            </div>
                        </div>
                    </div>
                    
                    <div class="col-md-6">
                        <h6 class="text-muted mb-3">To</h6>
                        <div class="card bg-light">
                            <div class="card-body">
                                ${transfer.to_user ? `<div><strong>User:</strong> ${transfer.to_user.name}</div>` : ''}
                                ${transfer.to_branch ? `<div><strong>Branch:</strong> ${transfer.to_branch.name}</div>` : '<div><strong>Location:</strong> Head Office</div>'}
                            </div>
                        </div>
                    </div>
                    
                    ${transfer.reason ? `
                        <div class="col-12">
                            <h6 class="text-muted mb-2">Business Justification</h6>
                            <div class="alert alert-info mb-0">
                                <i class="bi bi-chat-quote me-2"></i>${transfer.reason}
                            </div>
                        </div>
                    ` : ''}
                    
                    <div class="col-12">
                        <h6 class="text-muted mb-3">Timeline</h6>
                        ${this.renderTimeline(transfer)}
                    </div>
                </div>
            `;
        }

        startPolling() {
            setInterval(async () => {
                try {
                    await this.fetchTransfers();
                    this.updateStatistics();
                } catch (error) {
                    console.error('Polling failed:', error);
                }
            }, CONFIG.POLL_INTERVAL);
        }
    }

    // Initialize on DOM ready
    document.addEventListener('DOMContentLoaded', () => {
        window.transferDashboard = new TransferDashboard();
        
        // Character counters
        const initReasonTextarea = document.getElementById('initTransferReason');
        const bulkReasonTextarea = document.getElementById('bulkTransferReason');
        
        if (initReasonTextarea) {
            initReasonTextarea.addEventListener('input', function() {
                document.getElementById('initReasonCharCount').textContent = this.value.length;
            });
        }
        
        if (bulkReasonTextarea) {
            bulkReasonTextarea.addEventListener('input', function() {
                document.getElementById('bulkReasonCharCount').textContent = this.value.length;
            });
        }
    });

    // ========== WORLD-CLASS: TRANSFER INITIATION FUNCTIONS ==========

    /**
     * Open Initiate Transfer Modal
     */
    window.openInitiateTransferModal = async function() {
        const modal = new bootstrap.Modal(document.getElementById('initiateTransferModal'));
        modal.show();
        
        // Load assets and branches
        await Promise.all([
            loadAssetsForTransfer(),
            loadBranchesForTransfer('init')
        ]);
    };

    /**
     * Open Bulk Transfer Modal
     */
    window.openBulkTransferModal = async function() {
        const modal = new bootstrap.Modal(document.getElementById('bulkTransferModal'));
        modal.show();
        
        // Load assets and branches
        await Promise.all([
            loadAssetsForBulkTransfer(),
            loadBranchesForTransfer('bulk')
        ]);
    };

    /**
     * Load active assets for transfer
     */
    async function loadAssetsForTransfer() {
        const select = document.getElementById('initAssetSelect');
        select.innerHTML = '<option value="">Loading assets...</option>';
        
        try {
            const response = await fetch('/assets/api/list/?status=active&limit=500', {
                headers: { 'X-CSRFToken': getCSRFToken() },
                credentials: 'same-origin'
            });
            
            const data = await response.json();
            
            if (data.success && data.assets) {
                select.innerHTML = '<option value="">-- Select an asset --</option>';
                data.assets.forEach(asset => {
                    const option = document.createElement('option');
                    option.value = asset.id;
                    option.textContent = `${asset.name} (${asset.category}) - ${asset.branch || 'No Branch'}`;
                    option.dataset.assetId = asset.id;
                    select.appendChild(option);
                });
            } else {
                select.innerHTML = '<option value="">No assets available</option>';
            }
        } catch (error) {
            console.error('Error loading assets:', error);
            select.innerHTML = '<option value="">Error loading assets</option>';
        }
    }

    /**
     * Load assets for bulk transfer with checkboxes
     */
    async function loadAssetsForBulkTransfer() {
        const container = document.getElementById('bulkAssetCheckboxes');
        container.innerHTML = '<div class="text-center py-3"><div class="spinner-border spinner-border-sm"></div> Loading...</div>';
        
        try {
            const response = await fetch('/assets/api/list/?status=active&limit=500', {
                headers: { 'X-CSRFToken': getCSRFToken() },
                credentials: 'same-origin'
            });
            
            const data = await response.json();
            
            if (data.success && data.assets) {
                container.innerHTML = '';
                data.assets.forEach(asset => {
                    const div = document.createElement('div');
                    div.className = 'form-check mb-2';
                    div.innerHTML = `
                        <input class="form-check-input bulk-asset-checkbox" type="checkbox" value="${asset.id}" id="asset-${asset.id}">
                        <label class="form-check-label" for="asset-${asset.id}">
                            <strong>${asset.name}</strong> - ${asset.category} 
                            <span class="text-muted">(${asset.branch || 'No Branch'})</span>
                        </label>
                    `;
                    container.appendChild(div);
                });
                
                // Update counter on checkbox change
                document.querySelectorAll('.bulk-asset-checkbox').forEach(cb => {
                    cb.addEventListener('change', updateBulkSelectedCount);
                });
            } else {
                container.innerHTML = '<div class="text-center text-muted py-3">No assets available</div>';
            }
        } catch (error) {
            console.error('Error loading assets:', error);
            container.innerHTML = '<div class="text-center text-danger py-3">Error loading assets</div>';
        }
    }

    /**
     * Update bulk selected count
     */
    function updateBulkSelectedCount() {
        const checked = document.querySelectorAll('.bulk-asset-checkbox:checked').length;
        document.getElementById('bulkSelectedCount').textContent = `${checked} selected`;
        document.getElementById('bulkBtnCount').textContent = checked;
    }

    /**
     * Load branches for transfer
     */
    async function loadBranchesForTransfer(type) {
        const selectId = type === 'init' ? 'initBranchSelect' : 'bulkBranchSelect';
        const select = document.getElementById(selectId);
        select.innerHTML = '<option value="">Loading branches...</option>';
        
        try {
            const response = await fetch('/settings/api/branches/', {
                headers: { 'X-CSRFToken': getCSRFToken() },
                credentials: 'same-origin'
            });
            
            const data = await response.json();
            
            if (data.success && data.branches) {
                select.innerHTML = '<option value="">-- Select destination branch --</option>';
                data.branches.forEach(branch => {
                    const option = document.createElement('option');
                    option.value = branch.id;
                    option.textContent = branch.name;
                    select.appendChild(option);
                });
            } else {
                select.innerHTML = '<option value="">No branches available</option>';
            }
        } catch (error) {
            console.error('Error loading branches:', error);
            select.innerHTML = '<option value="">Error loading branches</option>';
        }
    }

    /**
     * Load users for init transfer (cascading)
     */
    window.loadUsersForInitTransfer = async function() {
        const branchId = document.getElementById('initBranchSelect').value;
        const userSelect = document.getElementById('initUserSelect');
        const loadingState = document.getElementById('initUserLoadingState');
        const userCountBadge = document.getElementById('initUserCountBadge');
        const userSelectPrompt = document.getElementById('initUserSelectPrompt');
        const userCount = document.getElementById('initUserCount');
        
        userSelect.disabled = true;
        userSelect.innerHTML = '<option value="">Loading...</option>';
        userCountBadge.classList.add('d-none');
        userSelectPrompt.classList.add('d-none');
        
        if (!branchId) {
            userSelect.innerHTML = '<option value="">Select a branch first...</option>';
            userSelectPrompt.classList.remove('d-none');
            return;
        }
        
        loadingState.classList.remove('d-none');
        
        try {
            const response = await fetch(`/assets/api/users-by-branch/?branch_id=${branchId}`, {
                headers: { 'X-CSRFToken': getCSRFToken() },
                credentials: 'same-origin'
            });
            
            const data = await response.json();
            loadingState.classList.add('d-none');
            
            if (!data.success) {
                throw new Error(data.error || 'Failed to load users');
            }
            
            if (data.users.length === 0) {
                userSelect.innerHTML = '<option value="">No users in this branch</option>';
                return;
            }
            
            // Populate grouped users
            userSelect.innerHTML = '<option value="">-- Select a user --</option>';
            const grouped = data.grouped;
            
            ['administrators', 'managers', 'users'].forEach(role => {
                if (grouped[role] && grouped[role].length > 0) {
                    const optgroup = document.createElement('optgroup');
                    optgroup.label = role === 'administrators' ? '👑 Administrators' : 
                                     role === 'managers' ? '💼 Managers' : '👤 Users';
                    grouped[role].forEach(user => {
                        const option = document.createElement('option');
                        option.value = user.id;
                        option.textContent = `${user.full_name} (${user.email})`;
                        optgroup.appendChild(option);
                    });
                    userSelect.appendChild(optgroup);
                }
            });
            
            userSelect.disabled = false;
            userCount.textContent = data.users.length;
            userCountBadge.classList.remove('d-none');
            
        } catch (error) {
            console.error('Error loading users:', error);
            loadingState.classList.add('d-none');
            userSelect.innerHTML = '<option value="">Error loading users</option>';
            showToast('Failed to load users. Please try again.', 'danger');
        }
    };

    /**
     * Load users for bulk transfer (cascading)
     */
    window.loadUsersForBulkTransfer = async function() {
        const branchId = document.getElementById('bulkBranchSelect').value;
        const userSelect = document.getElementById('bulkUserSelect');
        const loadingState = document.getElementById('bulkUserLoadingState');
        
        userSelect.disabled = true;
        userSelect.innerHTML = '<option value="">Loading...</option>';
        
        if (!branchId) {
            userSelect.innerHTML = '<option value="">Select a branch first...</option>';
            return;
        }
        
        loadingState.classList.remove('d-none');
        
        try {
            const response = await fetch(`/assets/api/users-by-branch/?branch_id=${branchId}`, {
                headers: { 'X-CSRFToken': getCSRFToken() },
                credentials: 'same-origin'
            });
            
            const data = await response.json();
            loadingState.classList.add('d-none');
            
            if (!data.success || data.users.length === 0) {
                userSelect.innerHTML = '<option value="">No users in this branch</option>';
                return;
            }
            
            // Populate grouped users
            userSelect.innerHTML = '<option value="">-- Select a user --</option>';
            const grouped = data.grouped;
            
            ['administrators', 'managers', 'users'].forEach(role => {
                if (grouped[role] && grouped[role].length > 0) {
                    const optgroup = document.createElement('optgroup');
                    optgroup.label = role === 'administrators' ? '👑 Administrators' : 
                                     role === 'managers' ? '💼 Managers' : '👤 Users';
                    grouped[role].forEach(user => {
                        const option = document.createElement('option');
                        option.value = user.id;
                        option.textContent = `${user.full_name} (${user.email})`;
                        optgroup.appendChild(option);
                    });
                    userSelect.appendChild(optgroup);
                }
            });
            
            userSelect.disabled = false;
            
        } catch (error) {
            console.error('Error loading users:', error);
            loadingState.classList.add('d-none');
            userSelect.innerHTML = '<option value="">Error loading users</option>';
        }
    };

    /**
     * Execute individual transfer
     */
    window.executeInitiateTransfer = async function() {
        const assetId = document.getElementById('initAssetSelect').value;
        const branchId = document.getElementById('initBranchSelect').value;
        const userId = document.getElementById('initUserSelect').value;
        const reason = document.getElementById('initTransferReason').value;
        const priority = document.getElementById('initTransferPriority').value;
        const btn = document.getElementById('executeInitTransferBtn');
        const progress = document.getElementById('initTransferProgress');
        
        // Validation
        if (!assetId || !branchId || !userId || !reason || reason.length < 10) {
            showToast('Please fill all required fields correctly', 'danger');
            return;
        }
        
        // Confirmation
        const selectedAsset = document.getElementById('initAssetSelect').selectedOptions[0]?.textContent;
        const selectedUser = document.getElementById('initUserSelect').selectedOptions[0]?.textContent;
        if (!confirm(`Transfer "${selectedAsset}" to ${selectedUser}?`)) {
            return;
        }
        
        btn.disabled = true;
        progress.classList.remove('d-none');
        
        try {
            const response = await fetch('/assets/api/transfers/initiate/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCSRFToken()
                },
                credentials: 'same-origin',
                body: JSON.stringify({
                    asset_id: parseInt(assetId),
                    to_user_id: parseInt(userId),
                    to_branch_id: parseInt(branchId),
                    initiator_comment: reason,
                    context: { priority }
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                showToast('✅ Transfer initiated successfully!', 'success');
                bootstrap.Modal.getInstance(document.getElementById('initiateTransferModal')).hide();
                setTimeout(() => window.location.reload(), 1500);
            } else {
                showToast('❌ ' + (data.error || 'Transfer failed'), 'danger');
                btn.disabled = false;
            }
        } catch (error) {
            showToast('❌ Network error: ' + error.message, 'danger');
            btn.disabled = false;
        } finally {
            progress.classList.add('d-none');
        }
    };

    /**
     * Execute bulk transfer
     */
    window.executeBulkTransfer = async function() {
        const selectedAssets = Array.from(document.querySelectorAll('.bulk-asset-checkbox:checked')).map(cb => parseInt(cb.value));
        const branchId = document.getElementById('bulkBranchSelect').value;
        const userId = document.getElementById('bulkUserSelect').value;
        const reason = document.getElementById('bulkTransferReason').value;
        const btn = document.getElementById('executeBulkTransferBtn');
        const progress = document.getElementById('bulkTransferProgress');
        const progressBar = document.getElementById('bulkProgressBar');
        const progressText = document.getElementById('bulkProgressText');
        
        // Validation
        if (selectedAssets.length === 0) {
            showToast('Please select at least one asset', 'warning');
            return;
        }
        
        if (!branchId || !userId || !reason || reason.length < 10) {
            showToast('Please fill all required fields correctly', 'danger');
            return;
        }
        
        // Confirmation
        if (!confirm(`Transfer ${selectedAssets.length} asset(s)?`)) {
            return;
        }
        
        btn.disabled = true;
        progress.classList.remove('d-none');
        
        let completed = 0;
        const total = selectedAssets.length;
        
        try {
            for (const assetId of selectedAssets) {
                progressText.textContent = `Processing ${completed + 1} of ${total}...`;
                progressBar.style.width = `${(completed / total) * 100}%`;
                
                const response = await fetch('/assets/api/transfers/initiate/', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': getCSRFToken()
                    },
                    credentials: 'same-origin',
                    body: JSON.stringify({
                        asset_id: assetId,
                        to_user_id: parseInt(userId),
                        to_branch_id: parseInt(branchId),
                        initiator_comment: reason,
                        context: { bulk: true }
                    })
                });
                
                const data = await response.json();
                if (!data.success) {
                    console.error(`Failed to transfer asset ${assetId}:`, data.error);
                }
                
                completed++;
            }
            
            progressBar.style.width = '100%';
            showToast(`✅ Successfully initiated ${completed} transfer(s)!`, 'success');
            bootstrap.Modal.getInstance(document.getElementById('bulkTransferModal')).hide();
            setTimeout(() => window.location.reload(), 1500);
            
        } catch (error) {
            showToast('❌ Bulk transfer error: ' + error.message, 'danger');
            btn.disabled = false;
        } finally {
            progress.classList.add('d-none');
        }
    };

})();
