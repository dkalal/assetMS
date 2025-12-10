/**
 * Admin Transfer Approval Dashboard
 * 
 * WORLD-CLASS: JavaScript for admin/manager approval workflow.
 * 
 * Features:
 * - List of pending transfer requests
 * - Detailed view of each request
 * - Asset-by-asset approval/rejection
 * - Bulk approval actions
 * - Complete audit trail
 * 
 * Inspired by:
 * - ServiceNow ITAM: Approval dashboard
 * - IBM Maximo: Review workflow
 * - SAP EAM: Multi-level approval
 */

class AdminTransferApprovalDashboard {
    constructor() {
        this.pendingTransfers = [];
        this.currentTransfer = null;
        this.modalElement = null;
        this.modal = null;
    }

    /**
     * Initialize dashboard
     */
    async init() {
        await this.loadPendingTransfers();
        this.render();
    }

    /**
     * Load pending transfers from API
     */
    async loadPendingTransfers() {
        try {
            const response = await fetch('/users/api/transfer/pending/', {
                method: 'GET',
                headers: {
                    'X-CSRFToken': this.getCSRFToken(),
                },
            });

            if (!response.ok) {
                throw new Error('Failed to load pending transfers');
            }

            const data = await response.json();
            if (!data.success) {
                throw new Error(data.error || 'Failed to load transfers');
            }

            this.pendingTransfers = data.data.pending_approval || [];
        } catch (error) {
            console.error('Error loading pending transfers:', error);
            this.showToast('Failed to load pending transfers', 'danger');
        }
    }

    /**
     * Render dashboard
     */
    render() {
        const container = document.getElementById('transferApprovalsContainer');
        if (!container) {
            console.error('Container #transferApprovalsContainer not found');
            return;
        }

        if (this.pendingTransfers.length === 0) {
            container.innerHTML = this.renderEmptyState();
            return;
        }

        container.innerHTML = this.renderTransfersList();
    }

    /**
     * Render empty state
     */
    renderEmptyState() {
        return `
            <div class="text-center py-5">
                <i class="bi bi-check-circle display-1 text-success"></i>
                <h4 class="mt-3">All Caught Up!</h4>
                <p class="text-muted">No pending transfer approvals at the moment.</p>
            </div>
        `;
    }

    /**
     * Render transfers list
     */
    renderTransfersList() {
        return `
            <div class="row">
                <div class="col-12 mb-3">
                    <h5 class="mb-0">
                        <i class="bi bi-clock-history me-2"></i>
                        Pending Approvals (${this.pendingTransfers.length})
                    </h5>
                </div>
                
                ${this.pendingTransfers.map(transfer => this.renderTransferCard(transfer)).join('')}
            </div>
        `;
    }

    /**
     * Render single transfer card
     */
    renderTransferCard(transfer) {
        const daysAgo = this.getDaysAgo(transfer.timestamps.user_selection_at);
        const isUrgent = daysAgo > 2;

        return `
            <div class="col-md-6 col-lg-4 mb-4">
                <div class="card h-100 ${isUrgent ? 'border-warning' : ''}">
                    <div class="card-body">
                        ${isUrgent ? '<span class="badge bg-warning text-dark mb-2"><i class="bi bi-exclamation-triangle me-1"></i>Urgent</span>' : ''}
                        
                        <h6 class="card-title mb-3">
                            ${transfer.user.full_name}
                        </h6>

                        <div class="mb-3">
                            <small class="text-muted d-block">Transfer:</small>
                            <div class="d-flex align-items-center">
                                <span class="badge bg-secondary">${transfer.from_branch ? transfer.from_branch.name : 'N/A'}</span>
                                <i class="bi bi-arrow-right mx-2"></i>
                                <span class="badge bg-primary">${transfer.to_branch.name}</span>
                            </div>
                        </div>

                        <div class="mb-3">
                            <small class="text-muted">Reason:</small>
                            <p class="small mb-0">${this.truncate(transfer.initiation_reason, 100)}</p>
                        </div>

                        <div class="row text-center mb-3">
                            <div class="col-6">
                                <small class="text-muted">Selected</small>
                                <div class="fw-bold text-success">${transfer.statistics.selected_by_user}</div>
                            </div>
                            <div class="col-6">
                                <small class="text-muted">To Return</small>
                                <div class="fw-bold text-warning">${transfer.statistics.total_assets - transfer.statistics.selected_by_user}</div>
                            </div>
                        </div>

                        <div class="text-muted small mb-3">
                            <i class="bi bi-calendar me-1"></i>
                            Submitted ${daysAgo === 0 ? 'today' : daysAgo === 1 ? 'yesterday' : daysAgo + ' days ago'}
                        </div>

                        <button class="btn btn-primary w-100" onclick="adminTransferDashboard.showApprovalModal(${transfer.id})">
                            <i class="bi bi-eye me-1"></i> Review Transfer
                        </button>
                    </div>
                </div>
            </div>
        `;
    }

    /**
     * Show approval modal for specific transfer
     */
    async showApprovalModal(transferId) {
        try {
            // Fetch full transfer details
            const response = await fetch(`/users/api/transfer/${transferId}/`, {
                method: 'GET',
                headers: {
                    'X-CSRFToken': this.getCSRFToken(),
                },
            });

            if (!response.ok) {
                throw new Error('Failed to load transfer details');
            }

            const data = await response.json();
            if (!data.success) {
                throw new Error(data.error || 'Failed to load transfer');
            }

            this.currentTransfer = data.data;
            this.renderApprovalModal();
            this.showBootstrapModal();
        } catch (error) {
            console.error('Error loading transfer details:', error);
            this.showToast('Failed to load transfer details', 'danger');
        }
    }

    /**
     * Render approval modal
     */
    renderApprovalModal() {
        const transfer = this.currentTransfer;
        const selectedAssets = transfer.asset_selections.filter(s => s.selected_by_user);
        const unselectedAssets = transfer.asset_selections.filter(s => !s.selected_by_user);

        const html = `
            <div class="modal fade" id="transferApprovalModal" tabindex="-1" data-bs-backdrop="static">
                <div class="modal-dialog modal-xl modal-dialog-scrollable">
                    <div class="modal-content">
                        <!-- Header -->
                        <div class="modal-header bg-gradient-primary text-white">
                            <div>
                                <h5 class="modal-title mb-1">
                                    <i class="bi bi-clipboard-check me-2"></i>
                                    Transfer Approval: ${transfer.user.full_name}
                                </h5>
                                <p class="mb-0 small opacity-75">
                                    ${transfer.from_branch ? transfer.from_branch.name : 'N/A'} → ${transfer.to_branch.name}
                                </p>
                            </div>
                            <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
                        </div>

                        <!-- Body -->
                        <div class="modal-body">
                            <!-- Transfer Details -->
                            <div class="card mb-4">
                                <div class="card-body">
                                    <h6 class="card-title">Transfer Details</h6>
                                    <dl class="row mb-0">
                                        <dt class="col-sm-3">User:</dt>
                                        <dd class="col-sm-9">${transfer.user.full_name} (${transfer.user.email})</dd>

                                        <dt class="col-sm-3">Initiated by:</dt>
                                        <dd class="col-sm-9">${transfer.initiated_by ? transfer.initiated_by.full_name : 'N/A'}</dd>

                                        <dt class="col-sm-3">Reason:</dt>
                                        <dd class="col-sm-9">${transfer.initiation_reason}</dd>

                                        ${transfer.user_selection_notes ? `
                                            <dt class="col-sm-3">User Notes:</dt>
                                            <dd class="col-sm-9">${transfer.user_selection_notes}</dd>
                                        ` : ''}
                                    </dl>
                                </div>
                            </div>

                            <!-- Selected Assets -->
                            <div class="card mb-4">
                                <div class="card-header bg-success text-white">
                                    <h6 class="mb-0">
                                        <i class="bi bi-check-square me-2"></i>
                                        Assets Selected for Transfer (${selectedAssets.length})
                                    </h6>
                                </div>
                                <div class="card-body">
                                    ${selectedAssets.length === 0 ? `
                                        <p class="text-muted mb-0">No assets selected for transfer</p>
                                    ` : `
                                        <div class="table-responsive">
                                            <table class="table table-sm table-hover mb-0">
                                                <thead>
                                                    <tr>
                                                        <th>Asset</th>
                                                        <th>Category</th>
                                                        <th>Serial Number</th>
                                                        <th>User's Reason</th>
                                                        <th>Action</th>
                                                    </tr>
                                                </thead>
                                                <tbody>
                                                    ${selectedAssets.map(selection => {
                                                        const assetId = selection.asset.identifier || selection.asset.serial_number || selection.asset.asset_tag || `Asset #${selection.asset.id}`;
                                                        return `
                                                        <tr>
                                                            <td>${selection.asset.category} - ${assetId}</td>
                                                            <td><span class="badge bg-secondary">${selection.asset.category}</span></td>
                                                            <td>${selection.asset.serial_number || 'N/A'}</td>
                                                            <td><small class="text-muted">${selection.user_selection_reason || '-'}</small></td>
                                                            <td>
                                                                <button class="btn btn-sm btn-success" disabled>
                                                                    <i class="bi bi-check"></i> Approve
                                                                </button>
                                                            </td>
                                                        </tr>
                                                    `;
                                                    }).join('')}
                                                </tbody>
                                            </table>
                                        </div>
                                    `}
                                </div>
                            </div>

                            <!-- Unselected Assets -->
                            <div class="card mb-4">
                                <div class="card-header bg-warning">
                                    <h6 class="mb-0 text-dark">
                                        <i class="bi bi-square me-2"></i>
                                        Assets to be Returned (${unselectedAssets.length})
                                    </h6>
                                </div>
                                <div class="card-body">
                                    ${unselectedAssets.length === 0 ? `
                                        <p class="text-muted mb-0">All assets selected for transfer</p>
                                    ` : `
                                        <div class="table-responsive">
                                            <table class="table table-sm mb-0">
                                                <thead>
                                                    <tr>
                                                        <th>Asset</th>
                                                        <th>Category</th>
                                                        <th>Serial Number</th>
                                                        <th>Branch</th>
                                                    </tr>
                                                </thead>
                                                <tbody>
                                                    ${unselectedAssets.map(selection => {
                                                        const assetId = selection.asset.identifier || selection.asset.serial_number || selection.asset.asset_tag || `Asset #${selection.asset.id}`;
                                                        return `
                                                        <tr>
                                                            <td>${selection.asset.category} - ${assetId}</td>
                                                            <td><span class="badge bg-secondary">${selection.asset.category}</span></td>
                                                            <td>${selection.asset.serial_number || 'N/A'}</td>
                                                            <td>${selection.asset.branch ? selection.asset.branch.name : 'N/A'}</td>
                                                        </tr>
                                                    `;
                                                    }).join('')}
                                                </tbody>
                                            </table>
                                        </div>
                                    `}
                                    <small class="text-muted">
                                        <i class="bi bi-info-circle me-1"></i>
                                        These assets will be unassigned from the user and returned to ${transfer.from_branch ? transfer.from_branch.name : 'their branch'}.
                                    </small>
                                </div>
                            </div>

                            <!-- Approval Decision -->
                            <div class="card">
                                <div class="card-body">
                                    <h6 class="card-title">Your Decision</h6>
                                    <div class="mb-3">
                                        <label class="form-label">Approval/Rejection Notes</label>
                                        <textarea class="form-control" id="approvalNotes" rows="3" 
                                                  placeholder="Add notes about your decision..."></textarea>
                                    </div>
                                </div>
                            </div>
                        </div>

                        <!-- Footer -->
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">
                                Close
                            </button>
                            <button type="button" class="btn btn-danger" onclick="adminTransferDashboard.rejectTransfer()">
                                <i class="bi bi-x-circle me-1"></i> Reject Transfer
                            </button>
                            <button type="button" class="btn btn-success" onclick="adminTransferDashboard.approveTransfer()">
                                <i class="bi bi-check-circle me-1"></i> Approve All (${selectedAssets.length})
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;

        // Remove existing modal
        const existing = document.getElementById('transferApprovalModal');
        if (existing) {
            existing.remove();
        }

        // Add to body
        document.body.insertAdjacentHTML('beforeend', html);
        this.modalElement = document.getElementById('transferApprovalModal');
    }

    /**
     * Approve transfer
     */
    async approveTransfer() {
        const notes = document.getElementById('approvalNotes')?.value.trim() || '';

        if (!confirm(`Are you sure you want to approve this transfer? ${this.currentTransfer.statistics.selected_by_user} assets will be transferred to ${this.currentTransfer.to_branch.name}.`)) {
            return;
        }

        try {
            const response = await fetch(`/users/api/transfer/${this.currentTransfer.id}/approve/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken(),
                },
                body: JSON.stringify({
                    approval_reason: notes || 'Approved',
                    auto_execute: true
                })
            });

            const data = await response.json();

            if (!response.ok || !data.success) {
                throw new Error(data.error || 'Failed to approve transfer');
            }

            this.showToast('Transfer approved successfully!', 'success');
            this.hideBootstrapModal();
            
            // Reload dashboard
            setTimeout(() => {
                this.init();
            }, 1000);

        } catch (error) {
            console.error('Error approving transfer:', error);
            this.showToast(error.message || 'Failed to approve transfer', 'danger');
        }
    }

    /**
     * Reject transfer
     */
    async rejectTransfer() {
        const notes = document.getElementById('approvalNotes')?.value.trim();

        if (!notes) {
            this.showToast('Please provide a reason for rejection', 'warning');
            return;
        }

        if (!confirm('Are you sure you want to reject this transfer? The user will remain in their current branch.')) {
            return;
        }

        try {
            const response = await fetch(`/users/api/transfer/${this.currentTransfer.id}/reject/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken(),
                },
                body: JSON.stringify({
                    rejection_reason: notes
                })
            });

            const data = await response.json();

            if (!response.ok || !data.success) {
                throw new Error(data.error || 'Failed to reject transfer');
            }

            this.showToast('Transfer rejected', 'info');
            this.hideBootstrapModal();
            
            // Reload dashboard
            setTimeout(() => {
                this.init();
            }, 1000);

        } catch (error) {
            console.error('Error rejecting transfer:', error);
            this.showToast(error.message || 'Failed to reject transfer', 'danger');
        }
    }

    /**
     * Utility: Get days ago
     */
    getDaysAgo(dateString) {
        if (!dateString) return 0;
        const date = new Date(dateString);
        const now = new Date();
        const diff = now - date;
        return Math.floor(diff / (1000 * 60 * 60 * 24));
    }

    /**
     * Utility: Truncate text
     */
    truncate(text, length) {
        if (!text) return '';
        return text.length > length ? text.substring(0, length) + '...' : text;
    }

    /**
     * Show Bootstrap modal
     */
    showBootstrapModal() {
        this.modal = new bootstrap.Modal(this.modalElement);
        this.modal.show();
    }

    /**
     * Hide Bootstrap modal
     */
    hideBootstrapModal() {
        if (this.modal) {
            this.modal.hide();
        }
    }

    /**
     * Get CSRF token
     */
    getCSRFToken() {
        return document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';
    }

    /**
     * Show toast notification
     */
    showToast(message, type = 'info') {
        let container = document.getElementById('toastContainer');
        if (!container) {
            container = document.createElement('div');
            container.id = 'toastContainer';
            container.className = 'toast-container position-fixed top-0 end-0 p-3';
            container.style.zIndex = '11000';
            document.body.appendChild(container);
        }

        const toastId = 'toast_' + Date.now();
        const toastHTML = `
            <div id="${toastId}" class="toast align-items-center text-white bg-${type} border-0" role="alert">
                <div class="d-flex">
                    <div class="toast-body">${message}</div>
                    <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
                </div>
            </div>
        `;

        container.insertAdjacentHTML('beforeend', toastHTML);
        const toastElement = document.getElementById(toastId);
        const toast = new bootstrap.Toast(toastElement, { delay: 5000 });
        toast.show();

        toastElement.addEventListener('hidden.bs.toast', () => {
            toastElement.remove();
        });
    }
}

// Global instance
const adminTransferDashboard = new AdminTransferApprovalDashboard();

// Auto-init on page load
document.addEventListener('DOMContentLoaded', () => {
    if (document.getElementById('transferApprovalsContainer')) {
        adminTransferDashboard.init();
    }
});
