/**
 * User Branch Transfer - Asset Selection Modal
 * 
 * WORLD-CLASS: JavaScript for user-facing asset selection workflow.
 * 
 * Features:
 * - Asset selection modal with checkboxes
 * - Search and filter functionality
 * - Reason input for each selected asset
 * - Real-time selection counter
 * - Submit selections to backend
 * - Beautiful, accessible UI
 * 
 * Inspired by:
 * - ServiceNow ITAM: Clean selection interface
 * - IBM Maximo: Reason documentation
 * - SAP EAM: Professional modals
 */

class UserBranchTransferModal {
    constructor() {
        this.transferRequest = null;
        this.assets = [];
        this.selections = new Map(); // asset_id => { selected: boolean, reason: string }
        this.modal = null;
        this.modalElement = null;
    }

    /**
     * Initialize and show modal for transfer request
     */
    async showModal(transferRequestId) {
        try {
            // Fetch transfer request details
            const response = await fetch(`/users/api/transfer/${transferRequestId}/`, {
                method: 'GET',
                headers: {
                    'X-CSRFToken': this.getCSRFToken(),
                },
            });

            if (!response.ok) {
                throw new Error('Failed to load transfer request');
            }

            const data = await response.json();
            if (!data.success) {
                throw new Error(data.error || 'Failed to load transfer request');
            }

            this.transferRequest = data.data;
            this.assets = this.transferRequest.asset_selections || [];
            
            // Initialize selections map
            this.selections.clear();
            this.assets.forEach(selection => {
                this.selections.set(selection.asset.id, {
                    selected: selection.selected_by_user || false,
                    reason: selection.user_selection_reason || ''
                });
            });

            // Render modal
            this.renderModal();
            this.showBootstrapModal();
        } catch (error) {
            console.error('Error loading transfer request:', error);
            this.showToast('Failed to load transfer request', 'danger');
        }
    }

    /**
     * Render modal HTML
     */
    renderModal() {
        const html = `
            <div class="modal fade" id="assetSelectionModal" tabindex="-1" data-bs-backdrop="static">
                <div class="modal-dialog modal-xl modal-dialog-scrollable">
                    <div class="modal-content">
                        <!-- Header -->
                        <div class="modal-header bg-gradient-primary text-white">
                            <div>
                                <h5 class="modal-title mb-1">
                                    <i class="bi bi-arrow-left-right me-2"></i>
                                    Branch Transfer: Select Assets
                                </h5>
                                <p class="mb-0 small opacity-75">
                                    ${this.transferRequest.from_branch ? this.transferRequest.from_branch.name : 'Current Branch'} → ${this.transferRequest.to_branch.name}
                                </p>
                            </div>
                            <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
                        </div>

                        <!-- Instructions -->
                        <div class="modal-body">
                            <div class="alert alert-info mb-4">
                                <i class="bi bi-info-circle me-2"></i>
                                <strong>Important:</strong> Select which assets you want to transfer to ${this.transferRequest.to_branch.name}. 
                                Assets you don't select will be returned to ${this.transferRequest.from_branch ? this.transferRequest.from_branch.name : 'your current branch'} 
                                for reassignment.
                            </div>

                            <!-- Search Bar -->
                            <div class="row mb-4">
                                <div class="col-md-8">
                                    <div class="input-group">
                                        <span class="input-group-text">
                                            <i class="bi bi-search"></i>
                                        </span>
                                        <input type="text" class="form-control" id="assetSearchInput" 
                                               placeholder="Search assets by name, serial number, category..." />
                                    </div>
                                </div>
                                <div class="col-md-4 text-end">
                                    <button class="btn btn-outline-primary me-2" id="selectAllBtn">
                                        <i class="bi bi-check-square me-1"></i> Select All
                                    </button>
                                    <button class="btn btn-outline-secondary" id="deselectAllBtn">
                                        <i class="bi bi-square me-1"></i> Deselect All
                                    </button>
                                </div>
                            </div>

                            <!-- Selection Counter -->
                            <div class="mb-3 p-3 bg-light rounded">
                                <div class="row text-center">
                                    <div class="col-md-4">
                                        <h6 class="text-muted mb-1">Total Assets</h6>
                                        <h4 class="mb-0">${this.assets.length}</h4>
                                    </div>
                                    <div class="col-md-4">
                                        <h6 class="text-success mb-1">To Transfer</h6>
                                        <h4 class="mb-0 text-success" id="selectedCount">0</h4>
                                    </div>
                                    <div class="col-md-4">
                                        <h6 class="text-warning mb-1">To Return</h6>
                                        <h4 class="mb-0 text-warning" id="unselectedCount">${this.assets.length}</h4>
                                    </div>
                                </div>
                            </div>

                            <!-- Assets List -->
                            <div id="assetsListContainer">
                                ${this.renderAssetsList()}
                            </div>

                            <!-- Overall Notes -->
                            <div class="mt-4">
                                <label class="form-label fw-bold">Overall Notes (optional)</label>
                                <textarea class="form-control" id="overallNotes" rows="3" 
                                          placeholder="Add any additional notes about your selections..."></textarea>
                            </div>
                        </div>

                        <!-- Footer -->
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">
                                Cancel
                            </button>
                            <button type="button" class="btn btn-primary" id="submitSelectionsBtn">
                                <i class="bi bi-check-circle me-1"></i>
                                Submit Selections (<span id="footerSelectedCount">0</span>)
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;

        // Remove existing modal if any
        const existing = document.getElementById('assetSelectionModal');
        if (existing) {
            existing.remove();
        }

        // Add to body
        document.body.insertAdjacentHTML('beforeend', html);
        this.modalElement = document.getElementById('assetSelectionModal');

        // Attach event listeners
        this.attachEventListeners();
    }

    /**
     * Render assets list
     */
    renderAssetsList() {
        if (this.assets.length === 0) {
            return `
                <div class="text-center py-5 text-muted">
                    <i class="bi bi-inbox display-1"></i>
                    <p class="mt-3">No assets found</p>
                </div>
            `;
        }

        // Group by category for better UX
        const byCategory = {};
        this.assets.forEach(selection => {
            const category = selection.asset.category;
            if (!byCategory[category]) {
                byCategory[category] = [];
            }
            byCategory[category].push(selection);
        });

        let html = '';
        
        Object.keys(byCategory).sort().forEach(category => {
            html += `
                <div class="asset-category-group mb-4">
                    <h6 class="text-muted text-uppercase mb-3">
                        <i class="bi bi-folder me-2"></i>${category}
                    </h6>
                    ${byCategory[category].map(selection => this.renderAssetCard(selection)).join('')}
                </div>
            `;
        });

        return html;
    }

    /**
     * Render single asset card
     */
    renderAssetCard(selection) {
        const asset = selection.asset;
        const assetId = asset.id;
        const isSelected = this.selections.get(assetId)?.selected || false;
        const reason = this.selections.get(assetId)?.reason || '';

        // Build asset identifier (Asset model has no 'name' field)
        const assetIdentifier = asset.identifier || asset.serial_number || asset.asset_tag || `Asset #${asset.id}`;

        // Determine if portable (recommended to transfer)
        const portableCategories = ['laptop', 'phone', 'tablet', 'mobile'];
        const isPortable = portableCategories.some(cat => 
            asset.category.toLowerCase().includes(cat)
        );

        return `
            <div class="asset-card mb-3 p-3 border rounded ${isSelected ? 'border-success bg-light' : ''}" 
                 data-asset-id="${assetId}"
                 data-asset-identifier="${assetIdentifier}"
                 data-asset-category="${asset.category}"
                 data-asset-serial="${asset.serial_number || ''}"
                 >
                <div class="d-flex align-items-start">
                    <!-- Checkbox -->
                    <div class="form-check me-3 mt-1">
                        <input class="form-check-input asset-checkbox" type="checkbox" 
                               id="asset_${assetId}" 
                               data-asset-id="${assetId}"
                               ${isSelected ? 'checked' : ''}>
                    </div>

                    <!-- Asset Info -->
                    <div class="flex-grow-1">
                        <div class="d-flex justify-content-between align-items-start mb-2">
                            <div>
                                <h6 class="mb-1">
                                    <label for="asset_${assetId}" class="form-check-label cursor-pointer">
                                        ${asset.category} - ${assetIdentifier}
                                    </label>
                                    ${isPortable ? '<span class="badge bg-success ms-2"><i class="bi bi-check-circle me-1"></i>Portable</span>' : ''}
                                </h6>
                                <div class="small text-muted">
                                    ${asset.serial_number ? `<span class="me-3"><i class="bi bi-hash"></i> ${asset.serial_number}</span>` : ''}
                                    ${asset.asset_tag ? `<span class="me-3"><i class="bi bi-tag"></i> ${asset.asset_tag}</span>` : ''}
                                    ${asset.branch ? `<span><i class="bi bi-building"></i> ${asset.branch.name}</span>` : ''}
                                </div>
                            </div>
                            <div class="text-end">
                                <span class="badge bg-secondary">${asset.status_display}</span>
                                ${asset.estimated_value > 0 ? `<div class="small text-muted mt-1">$${asset.estimated_value.toFixed(2)}</div>` : ''}
                            </div>
                        </div>

                        <!-- Reason Input (shown when selected) -->
                        <div class="reason-input-container ${isSelected ? '' : 'd-none'}" id="reasonContainer_${assetId}">
                            <label class="form-label small text-muted mb-1">
                                Why are you transferring this asset?
                            </label>
                            <input type="text" class="form-control form-control-sm asset-reason-input" 
                                   data-asset-id="${assetId}"
                                   placeholder="e.g., Primary work device, Need for new role..." 
                                   value="${reason}" />
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    /**
     * Attach event listeners
     */
    attachEventListeners() {
        // Search functionality
        const searchInput = document.getElementById('assetSearchInput');
        if (searchInput) {
            searchInput.addEventListener('input', (e) => {
                this.filterAssets(e.target.value);
            });
        }

        // Select all / Deselect all
        document.getElementById('selectAllBtn')?.addEventListener('click', () => {
            this.selectAll(true);
        });

        document.getElementById('deselectAllBtn')?.addEventListener('click', () => {
            this.selectAll(false);
        });

        // Asset checkboxes
        document.querySelectorAll('.asset-checkbox').forEach(checkbox => {
            checkbox.addEventListener('change', (e) => {
                this.handleAssetSelection(e.target);
            });
        });

        // Reason inputs
        document.querySelectorAll('.asset-reason-input').forEach(input => {
            input.addEventListener('input', (e) => {
                const assetId = parseInt(e.target.dataset.assetId);
                const selection = this.selections.get(assetId);
                if (selection) {
                    selection.reason = e.target.value;
                }
            });
        });

        // Submit button
        document.getElementById('submitSelectionsBtn')?.addEventListener('click', () => {
            this.submitSelections();
        });
    }

    /**
     * Handle asset checkbox change
     */
    handleAssetSelection(checkbox) {
        const assetId = parseInt(checkbox.dataset.assetId);
        const isSelected = checkbox.checked;

        // Update selection
        const selection = this.selections.get(assetId);
        if (selection) {
            selection.selected = isSelected;
        }

        // Show/hide reason input
        const reasonContainer = document.getElementById(`reasonContainer_${assetId}`);
        if (reasonContainer) {
            if (isSelected) {
                reasonContainer.classList.remove('d-none');
            } else {
                reasonContainer.classList.add('d-none');
            }
        }

        // Update card styling
        const card = checkbox.closest('.asset-card');
        if (card) {
            if (isSelected) {
                card.classList.add('border-success', 'bg-light');
            } else {
                card.classList.remove('border-success', 'bg-light');
            }
        }

        // Update counters
        this.updateCounters();
    }

    /**
     * Select all / Deselect all
     */
    selectAll(select) {
        // Update all visible checkboxes
        document.querySelectorAll('.asset-checkbox:not([style*="display: none"])').forEach(checkbox => {
            checkbox.checked = select;
            this.handleAssetSelection(checkbox);
        });
    }

    /**
     * Filter assets by search term
     */
    filterAssets(searchTerm) {
        const term = searchTerm.toLowerCase().trim();

        document.querySelectorAll('.asset-card').forEach(card => {
            const identifier = card.dataset.assetIdentifier?.toLowerCase() || '';
            const category = card.dataset.assetCategory?.toLowerCase() || '';
            const serial = card.dataset.assetSerial?.toLowerCase() || '';

            const matches = identifier.includes(term) || category.includes(term) || serial.includes(term);

            if (matches) {
                card.style.display = '';
            } else {
                card.style.display = 'none';
            }
        });

        // Also hide/show category groups
        document.querySelectorAll('.asset-category-group').forEach(group => {
            const visibleCards = group.querySelectorAll('.asset-card:not([style*="display: none"])').length;
            group.style.display = visibleCards > 0 ? '' : 'none';
        });
    }

    /**
     * Update selection counters
     */
    updateCounters() {
        const selectedCount = Array.from(this.selections.values()).filter(s => s.selected).length;
        const unselectedCount = this.assets.length - selectedCount;

        document.getElementById('selectedCount').textContent = selectedCount;
        document.getElementById('unselectedCount').textContent = unselectedCount;
        document.getElementById('footerSelectedCount').textContent = selectedCount;
    }

    /**
     * Submit selections to backend
     */
    async submitSelections() {
        try {
            // Get selected assets
            const selectedAssets = Array.from(this.selections.entries())
                .filter(([_, data]) => data.selected)
                .map(([id, _]) => id);

            // Get reasons
            const reasons = {};
            this.selections.forEach((data, assetId) => {
                if (data.selected && data.reason) {
                    reasons[assetId] = data.reason;
                }
            });

            // Get overall notes
            const notes = document.getElementById('overallNotes')?.value.trim() || '';

            // Disable submit button
            const submitBtn = document.getElementById('submitSelectionsBtn');
            const originalText = submitBtn.innerHTML;
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Submitting...';

            // Submit to backend
            const response = await fetch(`/users/api/transfer/${this.transferRequest.id}/submit-selections/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken(),
                },
                body: JSON.stringify({
                    selected_asset_ids: selectedAssets,
                    selection_reasons: reasons,
                    notes: notes
                })
            });

            const data = await response.json();

            if (!response.ok || !data.success) {
                throw new Error(data.error || 'Failed to submit selections');
            }

            // Success!
            this.showToast(
                `Selections submitted successfully! ${data.data.selected_count} assets to transfer, ${data.data.not_selected_count} to return. Waiting for admin approval.`,
                'success'
            );

            // Close modal and reload page
            this.hideBootstrapModal();
            setTimeout(() => {
                window.location.reload();
            }, 1500);

        } catch (error) {
            console.error('Error submitting selections:', error);
            this.showToast(error.message || 'Failed to submit selections', 'danger');

            // Re-enable button
            const submitBtn = document.getElementById('submitSelectionsBtn');
            submitBtn.disabled = false;
            submitBtn.innerHTML = originalText;
        }
    }

    /**
     * Show Bootstrap modal
     */
    showBootstrapModal() {
        this.modal = new bootstrap.Modal(this.modalElement);
        this.modal.show();
        this.updateCounters();
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
        // Create toast container if doesn't exist
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

        // Remove after hidden
        toastElement.addEventListener('hidden.bs.toast', () => {
            toastElement.remove();
        });
    }
}

// Global instance
window.userBranchTransferModal = new UserBranchTransferModal();

/**
 * Convenience function to show modal
 */
function showAssetSelectionModal(transferRequestId) {
    window.userBranchTransferModal.showModal(transferRequestId);
}
