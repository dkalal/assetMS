/**
 * WORLD-CLASS Export Preview System
 * 
 * Features:
 * - Preview first 50 rows before export
 * - Show total count and filters applied
 * - Confirm before actual export
 * - Support for Excel, CSV, and PDF formats
 * - Multi-tenancy aware
 * - Accessible and responsive UI
 * 
 * Inspired by:
 * - ServiceNow ITAM: Export preview with filter summary
 * - IBM Maximo: Data preview before report generation
 * - SAP EAM: Export confirmation with row count
 * 
 * @version 1.0.0
 * @date 2025-01-18
 */

class ExportPreviewManager {
    constructor() {
        this.modal = null;
        this.previewData = null;
        this.currentFormat = 'xlsx';
        this.currentFilters = {};
        this.csrfToken = this.getCSRFToken();
        
        this.init();
    }
    
    /**
     * Initialize export preview system
     */
    init() {
        console.log('🚀 Initializing Export Preview System...');
        
        // Create modal if not exists
        this.createModal();
        
        // Attach event listeners to export buttons
        this.attachExportListeners();
        
        console.log('✅ Export Preview System Ready!');
    }
    
    /**
     * Get CSRF token from cookie
     */
    getCSRFToken() {
        const name = 'csrftoken';
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }
    
    /**
     * Create export preview modal
     */
    createModal() {
        // Check if modal already exists
        if (document.getElementById('exportPreviewModal')) {
            this.modal = new bootstrap.Modal(document.getElementById('exportPreviewModal'));
            return;
        }
        
        const modalHTML = `
            <div class="modal fade" id="exportPreviewModal" tabindex="-1" aria-labelledby="exportPreviewModalLabel" aria-hidden="true">
                <div class="modal-dialog modal-xl modal-dialog-scrollable">
                    <div class="modal-content">
                        <div class="modal-header bg-primary text-white">
                            <h5 class="modal-title" id="exportPreviewModalLabel">
                                <i class="bi bi-eye me-2"></i>Export Preview
                            </h5>
                            <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal" aria-label="Close"></button>
                        </div>
                        <div class="modal-body">
                            <!-- Loading State -->
                            <div id="previewLoading" class="text-center py-5">
                                <div class="spinner-border text-primary" role="status">
                                    <span class="visually-hidden">Loading preview...</span>
                                </div>
                                <p class="mt-3 text-muted">Generating preview...</p>
                            </div>
                            
                            <!-- Preview Content -->
                            <div id="previewContent" style="display: none;">
                                <!-- Summary Stats -->
                                <div class="row mb-4">
                                    <div class="col-md-3">
                                        <div class="card border-primary">
                                            <div class="card-body text-center">
                                                <h3 class="mb-0 text-primary" id="totalCount">0</h3>
                                                <small class="text-muted">Total Assets</small>
                                            </div>
                                        </div>
                                    </div>
                                    <div class="col-md-3">
                                        <div class="card border-info">
                                            <div class="card-body text-center">
                                                <h3 class="mb-0 text-info" id="previewCount">0</h3>
                                                <small class="text-muted">Preview Rows</small>
                                            </div>
                                        </div>
                                    </div>
                                    <div class="col-md-3">
                                        <div class="card border-success">
                                            <div class="card-body text-center">
                                                <h3 class="mb-0 text-success" id="formatType">XLSX</h3>
                                                <small class="text-muted">Format</small>
                                            </div>
                                        </div>
                                    </div>
                                    <div class="col-md-3">
                                        <div class="card border-secondary">
                                            <div class="card-body text-center">
                                                <h3 class="mb-0 text-secondary" id="columnCount">0</h3>
                                                <small class="text-muted">Columns</small>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                                
                                <!-- Filters Applied -->
                                <div id="filtersApplied" class="alert alert-info mb-3" style="display: none;">
                                    <h6 class="alert-heading"><i class="bi bi-funnel me-2"></i>Filters Applied:</h6>
                                    <div id="filtersList"></div>
                                </div>
                                
                                <!-- Preview Table -->
                                <div class="table-responsive">
                                    <table class="table table-sm table-striped table-hover" id="previewTable">
                                        <thead class="table-dark">
                                            <tr id="previewTableHeader"></tr>
                                        </thead>
                                        <tbody id="previewTableBody"></tbody>
                                    </table>
                                </div>
                                
                                <!-- More Rows Indicator -->
                                <div id="moreRowsIndicator" class="alert alert-warning mt-3" style="display: none;">
                                    <i class="bi bi-info-circle me-2"></i>
                                    <strong>Note:</strong> Showing first <span id="previewedRows">50</span> rows. 
                                    Export will include all <span id="totalExportRows">0</span> rows.
                                </div>
                            </div>
                            
                            <!-- Error State -->
                            <div id="previewError" class="alert alert-danger" style="display: none;">
                                <h6 class="alert-heading"><i class="bi bi-exclamation-triangle me-2"></i>Preview Error</h6>
                                <p id="errorMessage" class="mb-0"></p>
                            </div>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">
                                <i class="bi bi-x-circle me-2"></i>Cancel
                            </button>
                            <button type="button" class="btn btn-success" id="confirmExportBtn" disabled>
                                <i class="bi bi-download me-2"></i>Confirm & Export
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        document.body.insertAdjacentHTML('beforeend', modalHTML);
        this.modal = new bootstrap.Modal(document.getElementById('exportPreviewModal'));
        
        // Attach confirm export listener
        document.getElementById('confirmExportBtn').addEventListener('click', () => {
            this.confirmExport();
        });
    }
    
    /**
     * Attach listeners to export buttons
     */
    attachExportListeners() {
        // Find all export buttons with data-export-preview attribute
        document.querySelectorAll('[data-export-preview]').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.preventDefault();
                const format = btn.dataset.exportFormat || 'xlsx';
                this.showPreview(format);
            });
        });
        
        console.log('✅ Export preview listeners attached');
    }
    
    /**
     * Collect current filters from page
     */
    getCurrentFilters() {
        const filters = {};
        
        // Category filter
        const categorySelect = document.getElementById('id_category') || document.querySelector('select[name="category"]');
        if (categorySelect && categorySelect.value) {
            filters.category = categorySelect.value;
        }
        
        // Status filter
        const statusSelect = document.getElementById('id_status') || document.querySelector('select[name="status"]');
        if (statusSelect && statusSelect.value) {
            filters.status = statusSelect.value;
        }
        
        // Search filter
        const searchInput = document.getElementById('id_search') || document.querySelector('input[name="search"]');
        if (searchInput && searchInput.value.trim()) {
            filters.search = searchInput.value.trim();
        }
        
        // Branch filter
        const branchSelect = document.getElementById('id_branch') || document.querySelector('select[name="branch"]');
        if (branchSelect && branchSelect.value) {
            filters.branch = branchSelect.value;
        }
        
        // Selected IDs (bulk export)
        const selectedAssets = this.getSelectedAssetIds();
        if (selectedAssets.length > 0) {
            filters.selected_ids = selectedAssets.join(',');
        }
        
        return filters;
    }
    
    /**
     * Get selected asset IDs from checkboxes
     */
    getSelectedAssetIds() {
        const checkboxes = document.querySelectorAll('input[name="asset_ids"]:checked');
        return Array.from(checkboxes).map(cb => cb.value);
    }
    
    /**
     * Show export preview
     */
    async showPreview(format = 'xlsx') {
        this.currentFormat = format;
        this.currentFilters = this.getCurrentFilters();
        
        // Show modal
        this.modal.show();
        
        // Show loading state
        this.showLoading();
        
        // Fetch preview data
        try {
            const response = await fetch('/assets/api/export-preview/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.csrfToken
                },
                body: JSON.stringify({
                    format: format,
                    ...this.currentFilters
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.previewData = data;
                this.renderPreview(data);
            } else {
                this.showError(data.error || 'Failed to generate preview');
            }
        } catch (error) {
            console.error('Preview error:', error);
            this.showError('Network error: Could not fetch preview');
        }
    }
    
    /**
     * Show loading state
     */
    showLoading() {
        document.getElementById('previewLoading').style.display = 'block';
        document.getElementById('previewContent').style.display = 'none';
        document.getElementById('previewError').style.display = 'none';
        document.getElementById('confirmExportBtn').disabled = true;
    }
    
    /**
     * Show error state
     */
    showError(message) {
        document.getElementById('previewLoading').style.display = 'none';
        document.getElementById('previewContent').style.display = 'none';
        document.getElementById('previewError').style.display = 'block';
        document.getElementById('errorMessage').textContent = message;
        document.getElementById('confirmExportBtn').disabled = true;
    }
    
    /**
     * Render preview data
     */
    renderPreview(data) {
        // Hide loading, show content
        document.getElementById('previewLoading').style.display = 'none';
        document.getElementById('previewContent').style.display = 'block';
        document.getElementById('previewError').style.display = 'none';
        document.getElementById('confirmExportBtn').disabled = false;
        
        // Update stats
        document.getElementById('totalCount').textContent = data.total_count.toLocaleString();
        document.getElementById('previewCount').textContent = data.preview_count;
        document.getElementById('formatType').textContent = data.format.toUpperCase();
        document.getElementById('columnCount').textContent = data.columns.length;
        
        // Render filters
        if (Object.keys(data.filters_applied).length > 0) {
            document.getElementById('filtersApplied').style.display = 'block';
            const filtersList = document.getElementById('filtersList');
            filtersList.innerHTML = Object.entries(data.filters_applied)
                .map(([key, value]) => `<span class="badge bg-primary me-2">${key}: ${value}</span>`)
                .join('');
        } else {
            document.getElementById('filtersApplied').style.display = 'none';
        }
        
        // Render table header
        const headerRow = document.getElementById('previewTableHeader');
        headerRow.innerHTML = data.columns
            .map(col => `<th>${this.formatColumnName(col)}</th>`)
            .join('');
        
        // Render table body
        const tbody = document.getElementById('previewTableBody');
        tbody.innerHTML = data.preview_rows
            .map(row => {
                const cells = data.columns
                    .map(col => `<td>${this.escapeHtml(row[col] || '-')}</td>`)
                    .join('');
                return `<tr>${cells}</tr>`;
            })
            .join('');
        
        // Show "more rows" indicator if applicable
        if (data.has_more) {
            document.getElementById('moreRowsIndicator').style.display = 'block';
            document.getElementById('previewedRows').textContent = data.preview_count;
            document.getElementById('totalExportRows').textContent = data.total_count.toLocaleString();
        } else {
            document.getElementById('moreRowsIndicator').style.display = 'none';
        }
    }
    
    /**
     * Format column name for display
     */
    formatColumnName(name) {
        return name
            .replace(/_/g, ' ')
            .replace(/\b\w/g, l => l.toUpperCase());
    }
    
    /**
     * Escape HTML to prevent XSS
     */
    escapeHtml(text) {
        const map = {
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#039;'
        };
        return String(text).replace(/[&<>"']/g, m => map[m]);
    }
    
    /**
     * Confirm and execute export
     */
    confirmExport() {
        if (!this.previewData) {
            alert('No preview data available');
            return;
        }
        
        // Build export URL with parameters
        const params = new URLSearchParams({
            format: this.currentFormat,
            ...this.currentFilters
        });
        
        // Trigger download
        window.location.href = `/assets/export/?${params.toString()}`;
        
        // Close modal
        this.modal.hide();
        
        // Show success toast
        this.showToast('Export started', `Exporting ${this.previewData.total_count} assets as ${this.currentFormat.toUpperCase()}...`, 'success');
    }
    
    /**
     * Show toast notification
     */
    showToast(title, message, type = 'info') {
        // Check if toast container exists
        let toastContainer = document.getElementById('toastContainer');
        if (!toastContainer) {
            toastContainer = document.createElement('div');
            toastContainer.id = 'toastContainer';
            toastContainer.className = 'toast-container position-fixed bottom-0 end-0 p-3';
            toastContainer.style.zIndex = '11000';
            document.body.appendChild(toastContainer);
        }
        
        const toastId = 'toast_' + Date.now();
        const bgClass = {
            'success': 'bg-success',
            'error': 'bg-danger',
            'warning': 'bg-warning',
            'info': 'bg-info'
        }[type] || 'bg-info';
        
        const toastHTML = `
            <div id="${toastId}" class="toast align-items-center text-white ${bgClass} border-0" role="alert" aria-live="assertive" aria-atomic="true">
                <div class="d-flex">
                    <div class="toast-body">
                        <strong>${title}</strong><br>${message}
                    </div>
                    <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
                </div>
            </div>
        `;
        
        toastContainer.insertAdjacentHTML('beforeend', toastHTML);
        const toastElement = document.getElementById(toastId);
        const toast = new bootstrap.Toast(toastElement);
        toast.show();
        
        // Remove after hidden
        toastElement.addEventListener('hidden.bs.toast', () => {
            toastElement.remove();
        });
    }
}

// Initialize on DOM ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        window.exportPreviewManager = new ExportPreviewManager();
    });
} else {
    window.exportPreviewManager = new ExportPreviewManager();
}
