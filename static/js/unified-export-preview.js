/**
 * WORLD-CLASS Unified Export Preview System
 * ==========================================
 * 
 * Single, reusable preview system for ALL export types across the application.
 * 
 * Features:
 * - Preview any export before downloading (assets, reports, maintenance, etc.)
 * - Real-time data validation and quality metrics
 * - Column analysis with data types and statistics
 * - Estimated file size and export duration
 * - Visual data quality indicators
 * - Format-specific optimization hints
 * - Responsive modal UI with smooth animations
 * - Keyboard navigation and accessibility
 * - Smart caching for performance
 * 
 * Inspired by:
 * - ServiceNow ITAM: Export preview with filter summary and data validation
 * - IBM Maximo: Report preview with column analysis and quality metrics
 * - SAP EAM: Export confirmation with size estimates and performance hints
 * - Our own import preview: Consistent UX and validation patterns
 * 
 * Usage:
 *   const previewManager = new UnifiedExportPreviewManager();
 *   
 *   // Attach to buttons:
 *   <button data-export-preview data-report-type="asset_summary" data-format="xlsx">
 *     Export
 *   </button>
 *   
 *   // Or call programmatically:
 *   previewManager.showPreview({
 *     reportType: 'asset_summary',
 *     format: 'xlsx',
 *     filters: { status: 'active', branch: 123 }
 *   });
 * 
 * @version 2.0.0
 * @date November 2025
 * @author AssetMS Development Team
 */

class UnifiedExportPreviewManager {
    constructor() {
        this.modal = null;
        this.previewData = null;
        this.currentConfig = {};
        this.csrfToken = this.getCSRFToken();
        this.cache = new Map();
        this.cacheTTL = 300000; // 5 minutes
        
        this.init();
    }
    
    /**
     * Initialize the preview system
     */
    init() {
        
        // Create modal
        this.createModal();
        
        // Attach event listeners
        this.attachExportListeners();
        
        // Keyboard shortcuts
        this.setupKeyboardShortcuts();
        
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
     * Create the modal HTML structure
     */
    createModal() {
        // Check if modal already exists
        if (document.getElementById('unifiedExportPreviewModal')) {
            this.modal = new bootstrap.Modal(document.getElementById('unifiedExportPreviewModal'));
            return;
        }
        
        const modalHTML = `
            <div class="modal fade" id="unifiedExportPreviewModal" tabindex="-1" 
                 aria-labelledby="exportPreviewLabel" aria-hidden="true" data-bs-backdrop="static">
                <div class="modal-dialog modal-xl modal-dialog-scrollable modal-dialog-centered">
                    <div class="modal-content" style="border-radius: 12px; box-shadow: 0 10px 40px rgba(0,0,0,0.2);">
                        <!-- Header -->
                        <div class="modal-header" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border-radius: 12px 12px 0 0;">
                            <h5 class="modal-title" id="exportPreviewLabel">
                                <i class="bi bi-eye me-2"></i>Export Preview
                            </h5>
                            <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal" aria-label="Close"></button>
                        </div>
                        
                        <!-- Body -->
                        <div class="modal-body" style="background-color: #f8f9fa;">
                            <!-- Loading State -->
                            <div id="previewLoading" class="text-center py-5">
                                <div class="spinner-border text-primary mb-3" role="status" style="width: 3rem; height: 3rem;">
                                    <span class="visually-hidden">Generating preview...</span>
                                </div>
                                <h5 class="text-muted">Analyzing data...</h5>
                                <p class="text-muted small">This should only take a moment</p>
                            </div>
                            
                            <!-- Error State -->
                            <div id="previewError" class="alert alert-danger d-none" role="alert">
                                <div class="d-flex align-items-start">
                                    <i class="bi bi-exclamation-triangle-fill fs-3 me-3"></i>
                                    <div>
                                        <h6 class="alert-heading mb-2">Preview Generation Failed</h6>
                                        <p id="errorMessage" class="mb-0"></p>
                                    </div>
                                </div>
                            </div>
                            
                            <!-- Preview Content -->
                            <div id="previewContent" class="d-none">
                                <!-- Summary Stats Row -->
                                <div class="row g-3 mb-4">
                                    <div class="col-md-3">
                                        <div class="card h-100 border-0 shadow-sm">
                                            <div class="card-body text-center">
                                                <i class="bi bi-file-earmark-text text-primary fs-1 mb-2"></i>
                                                <h2 class="mb-0 text-primary" id="totalRows">0</h2>
                                                <small class="text-muted">Total Rows</small>
                                            </div>
                                        </div>
                                    </div>
                                    <div class="col-md-3">
                                        <div class="card h-100 border-0 shadow-sm">
                                            <div class="card-body text-center">
                                                <i class="bi bi-columns-gap text-info fs-1 mb-2"></i>
                                                <h2 class="mb-0 text-info" id="totalColumns">0</h2>
                                                <small class="text-muted">Columns</small>
                                            </div>
                                        </div>
                                    </div>
                                    <div class="col-md-3">
                                        <div class="card h-100 border-0 shadow-sm">
                                            <div class="card-body text-center">
                                                <i class="bi bi-file-earmark-arrow-down text-success fs-1 mb-2"></i>
                                                <h2 class="mb-0 text-success" id="fileSize">0 KB</h2>
                                                <small class="text-muted">Est. File Size</small>
                                            </div>
                                        </div>
                                    </div>
                                    <div class="col-md-3">
                                        <div class="card h-100 border-0 shadow-sm">
                                            <div class="card-body text-center">
                                                <i class="bi bi-speedometer2 text-warning fs-1 mb-2"></i>
                                                <h2 class="mb-0 text-warning" id="exportTime">0s</h2>
                                                <small class="text-muted">Est. Export Time</small>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                                
                                <!-- Data Quality Score -->
                                <div class="card border-0 shadow-sm mb-4" id="qualityCard">
                                    <div class="card-body">
                                        <h6 class="card-title mb-3">
                                            <i class="bi bi-clipboard-check me-2"></i>Data Quality Score
                                        </h6>
                                        <div class="d-flex align-items-center">
                                            <div class="flex-grow-1">
                                                <div class="progress" style="height: 30px; border-radius: 15px;">
                                                    <div class="progress-bar" id="qualityBar" 
                                                         role="progressbar" style="width: 0%;" 
                                                         aria-valuenow="0" aria-valuemin="0" aria-valuemax="100">
                                                        <strong id="qualityScore">0%</strong>
                                                    </div>
                                                </div>
                                            </div>
                                            <div class="ms-3">
                                                <span class="badge fs-6" id="qualityBadge">-</span>
                                            </div>
                                        </div>
                                        <p class="text-muted small mt-2 mb-0">
                                            Based on data completeness, uniqueness, and consistency
                                        </p>
                                    </div>
                                </div>
                                
                                <!-- Warnings & Errors -->
                                <div id="warningsContainer" class="d-none mb-4"></div>
                                
                                <!-- Filters Applied -->
                                <div id="filtersApplied" class="card border-0 shadow-sm mb-4 d-none">
                                    <div class="card-body">
                                        <h6 class="card-title">
                                            <i class="bi bi-funnel me-2"></i>Active Filters
                                        </h6>
                                        <div id="filtersList" class="d-flex flex-wrap gap-2"></div>
                                    </div>
                                </div>
                                
                                <!-- Column Analysis -->
                                <div class="card border-0 shadow-sm mb-4">
                                    <div class="card-header bg-white">
                                        <h6 class="mb-0">
                                            <i class="bi bi-list-columns me-2"></i>Column Analysis
                                        </h6>
                                    </div>
                                    <div class="card-body p-0">
                                        <div class="table-responsive" style="max-height: 200px;">
                                            <table class="table table-sm table-hover mb-0">
                                                <thead class="table-light sticky-top">
                                                    <tr>
                                                        <th>Column</th>
                                                        <th>Type</th>
                                                        <th class="text-end">Null %</th>
                                                        <th class="text-end">Unique Values</th>
                                                        <th>Sample Values</th>
                                                    </tr>
                                                </thead>
                                                <tbody id="columnAnalysisBody"></tbody>
                                            </table>
                                        </div>
                                    </div>
                                </div>
                                
                                <!-- Data Preview Table -->
                                <div class="card border-0 shadow-sm">
                                    <div class="card-header bg-white d-flex justify-content-between align-items-center">
                                        <h6 class="mb-0">
                                            <i class="bi bi-table me-2"></i>Data Preview
                                            <span class="badge bg-secondary ms-2" id="previewRowsBadge">0 rows</span>
                                        </h6>
                                        <div id="moreRowsIndicator" class="d-none">
                                            <i class="bi bi-info-circle text-warning me-1"></i>
                                            <small class="text-muted">
                                                Showing first <span id="previewedRows">0</span> of 
                                                <span id="totalExportRows">0</span> rows
                                            </small>
                                        </div>
                                    </div>
                                    <div class="card-body p-0">
                                        <div class="table-responsive" style="max-height: 400px;">
                                            <table class="table table-sm table-striped table-hover mb-0" id="previewTable">
                                                <thead class="table-dark sticky-top" id="previewTableHeader"></thead>
                                                <tbody id="previewTableBody"></tbody>
                                            </table>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                        
                        <!-- Footer -->
                        <div class="modal-footer bg-white">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">
                                <i class="bi bi-x-circle me-2"></i>Cancel
                            </button>
                            <button type="button" class="btn btn-success btn-lg" id="confirmExportBtn" disabled>
                                <i class="bi bi-download me-2"></i>Confirm & Export
                                <span class="badge bg-light text-success ms-2" id="confirmBadge">0 rows</span>
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        document.body.insertAdjacentHTML('beforeend', modalHTML);
        this.modal = new bootstrap.Modal(document.getElementById('unifiedExportPreviewModal'));
        
        // Attach confirm button listener
        document.getElementById('confirmExportBtn').addEventListener('click', () => {
            this.confirmExport();
        });
    }
    
    /**
     * Attach listeners to export buttons
     */
    attachExportListeners() {
        // Auto-attach to buttons with data-export-preview attribute
        document.querySelectorAll('[data-export-preview]').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.preventDefault();
                
                const config = {
                    reportType: btn.dataset.reportType || 'asset_summary',
                    format: btn.dataset.format || 'xlsx',
                    // Collect filters from page
                    filters: this.collectFilters()
                };
                
                this.showPreview(config);
            });
        });
        
    }
    
    /**
     * Setup keyboard shortcuts
     */
    setupKeyboardShortcuts() {
        document.addEventListener('keydown', (e) => {
            // ESC to close
            if (e.key === 'Escape' && this.modal && this.modal._isShown) {
                this.modal.hide();
            }
            
            // Ctrl+Enter to confirm
            if (e.ctrlKey && e.key === 'Enter' && this.modal && this.modal._isShown) {
                const confirmBtn = document.getElementById('confirmExportBtn');
                if (confirmBtn && !confirmBtn.disabled) {
                    this.confirmExport();
                }
            }
        });
    }
    
    /**
     * Collect current filters from page
     */
    collectFilters() {
        const filters = {};
        
        // Try common filter field names
        const filterFields = [
            { id: 'id_category', name: 'category' },
            { id: 'id_status', name: 'status' },
            { id: 'id_search', name: 'search' },
            { id: 'id_branch', name: 'branch_id' },
            { id: 'id_date_from', name: 'date_from' },
            { id: 'id_date_to', name: 'date_to' },
        ];
        
        filterFields.forEach(({ id, name }) => {
            const field = document.getElementById(id) || document.querySelector(`[name="${name}"]`);
            if (field && field.value) {
                filters[name] = field.value;
            }
        });
        
        // Check for selected assets (bulk export)
        const selectedCheckboxes = document.querySelectorAll('input[name="asset_ids"]:checked');
        if (selectedCheckboxes.length > 0) {
            filters.selected_ids = Array.from(new Set(
                Array.from(selectedCheckboxes).map(cb => cb.value)
            )).join(',');
        }
        
        return filters;
    }
    
    /**
     * Show export preview
     * @param {Object} config - { reportType, format, filters }
     */
    async showPreview(config) {
        this.currentConfig = config;
        
        // Show modal
        this.modal.show();
        
        // Show loading state
        this.showLoading();
        
        // Check cache
        const cacheKey = this.getCacheKey(config);
        const cached = this.getFromCache(cacheKey);
        if (cached) {
            this.renderPreview(cached);
            return;
        }
        
        // Fetch preview data
        try {
            const endpoint = config.reportType === 'assets' 
                ? '/assets/api/export-preview/'
                : '/reports/api/preview-export/';
            
            const response = await fetch(endpoint, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.csrfToken
                },
                body: JSON.stringify({
                    report_type: config.reportType,
                    format: config.format,
                    ...config.filters
                })
            });
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            
            if (data.success) {
                // Cache the result
                this.saveToCache(cacheKey, data);
                
                this.previewData = data;
                this.renderPreview(data);
            } else {
                this.showError(data.error || 'Failed to generate preview');
            }
        } catch (error) {
            console.error('Preview error:', error);
            this.showError(`Network error: ${error.message}`);
        }
    }
    
    /**
     * Show loading state
     */
    showLoading() {
        document.getElementById('previewLoading').classList.remove('d-none');
        document.getElementById('previewContent').classList.add('d-none');
        document.getElementById('previewError').classList.add('d-none');
        document.getElementById('confirmExportBtn').disabled = true;
    }
    
    /**
     * Show error state
     */
    showError(message) {
        document.getElementById('previewLoading').classList.add('d-none');
        document.getElementById('previewContent').classList.add('d-none');
        document.getElementById('previewError').classList.remove('d-none');
        document.getElementById('errorMessage').textContent = message;
        document.getElementById('confirmExportBtn').disabled = true;
    }
    
    /**
     * Render preview data
     */
    renderPreview(data) {
        // Hide loading, show content
        document.getElementById('previewLoading').classList.add('d-none');
        document.getElementById('previewError').classList.add('d-none');
        document.getElementById('previewContent').classList.remove('d-none');
        document.getElementById('confirmExportBtn').disabled = false;
        
        const metrics = data.metrics || {};
        const columnMetadata = data.column_metadata || [];
        
        // Update summary stats
        document.getElementById('totalRows').textContent = this.formatNumber(metrics.total_rows || 0);
        document.getElementById('totalColumns').textContent = metrics.total_columns || 0;
        document.getElementById('fileSize').textContent = this.formatFileSize(metrics.estimated_file_size_kb || 0);
        document.getElementById('exportTime').textContent = `${metrics.estimated_export_time_seconds || 0}s`;
        
        // Update data quality
        this.renderDataQuality(metrics.data_quality_score || 0);
        
        // Update confirm button badge
        document.getElementById('confirmBadge').textContent = `${this.formatNumber(metrics.total_rows || 0)} rows`;
        
        // Render warnings/errors
        this.renderWarnings(metrics.warnings || [], metrics.errors || []);
        
        // Render filters
        this.renderFilters(data.filters_applied || {});
        
        // Render column analysis
        this.renderColumnAnalysis(columnMetadata);
        
        // Render preview table
        this.renderPreviewTable(data.preview_data || [], data.columns || []);
        
        // Update "more rows" indicator
        if (metrics.has_more) {
            document.getElementById('moreRowsIndicator').classList.remove('d-none');
            document.getElementById('previewedRows').textContent = metrics.preview_rows || 0;
            document.getElementById('totalExportRows').textContent = this.formatNumber(metrics.total_rows || 0);
        } else {
            document.getElementById('moreRowsIndicator').classList.add('d-none');
        }
        
        document.getElementById('previewRowsBadge').textContent = `${metrics.preview_rows || 0} of ${this.formatNumber(metrics.total_rows || 0)} rows`;
    }
    
    /**
     * Render data quality score
     */
    renderDataQuality(score) {
        const scoreRounded = Math.round(score);
        const qualityBar = document.getElementById('qualityBar');
        const qualityScore = document.getElementById('qualityScore');
        const qualityBadge = document.getElementById('qualityBadge');
        
        qualityBar.style.width = `${scoreRounded}%`;
        qualityBar.setAttribute('aria-valuenow', scoreRounded);
        qualityScore.textContent = `${scoreRounded}%`;
        
        // Color coding
        let colorClass, badgeClass, badgeText;
        if (scoreRounded >= 90) {
            colorClass = 'bg-success';
            badgeClass = 'bg-success';
            badgeText = 'Excellent';
        } else if (scoreRounded >= 70) {
            colorClass = 'bg-primary';
            badgeClass = 'bg-primary';
            badgeText = 'Good';
        } else if (scoreRounded >= 50) {
            colorClass = 'bg-warning';
            badgeClass = 'bg-warning text-dark';
            badgeText = 'Fair';
        } else {
            colorClass = 'bg-danger';
            badgeClass = 'bg-danger';
            badgeText = 'Poor';
        }
        
        qualityBar.className = `progress-bar ${colorClass}`;
        qualityBadge.className = `badge fs-6 ${badgeClass}`;
        qualityBadge.textContent = badgeText;
    }
    
    /**
     * Render warnings and errors
     */
    renderWarnings(warnings, errors) {
        const container = document.getElementById('warningsContainer');
        
        if (warnings.length === 0 && errors.length === 0) {
            container.classList.add('d-none');
            return;
        }
        
        container.classList.remove('d-none');
        
        let html = '';
        
        if (errors.length > 0) {
            html += `
                <div class="alert alert-danger mb-2">
                    <h6 class="alert-heading"><i class="bi bi-exclamation-triangle me-2"></i>Errors</h6>
                    <ul class="mb-0">
                        ${errors.map(err => `<li>${this.escapeHtml(err)}</li>`).join('')}
                    </ul>
                </div>
            `;
        }
        
        if (warnings.length > 0) {
            html += `
                <div class="alert alert-warning mb-2">
                    <h6 class="alert-heading"><i class="bi bi-info-circle me-2"></i>Warnings</h6>
                    <ul class="mb-0">
                        ${warnings.map(warn => `<li>${this.escapeHtml(warn)}</li>`).join('')}
                    </ul>
                </div>
            `;
        }
        
        container.innerHTML = html;
    }
    
    /**
     * Render applied filters
     */
    renderFilters(filters) {
        if (Object.keys(filters).length === 0) {
            document.getElementById('filtersApplied').classList.add('d-none');
            return;
        }
        
        document.getElementById('filtersApplied').classList.remove('d-none');
        
        const filtersList = document.getElementById('filtersList');
        filtersList.innerHTML = Object.entries(filters)
            .map(([key, value]) => `
                <span class="badge bg-primary">
                    <i class="bi bi-funnel-fill me-1"></i>${key}: ${this.escapeHtml(value)}
                </span>
            `)
            .join('');
    }
    
    /**
     * Render column analysis
     */
    renderColumnAnalysis(columnMetadata) {
        const tbody = document.getElementById('columnAnalysisBody');
        
        tbody.innerHTML = columnMetadata.map(col => {
            const typeIcon = this.getDataTypeIcon(col.data_type);
            const nullBadge = col.null_percentage > 20 
                ? `<span class="badge bg-warning text-dark">${col.null_percentage}%</span>`
                : `<span class="badge bg-light text-dark">${col.null_percentage}%</span>`;
            
            return `
                <tr>
                    <td><strong>${this.escapeHtml(col.display_name)}</strong></td>
                    <td>
                        <i class="bi bi-${typeIcon} me-1"></i>${col.data_type}
                    </td>
                    <td class="text-end">${nullBadge}</td>
                    <td class="text-end">
                        ${col.is_unique ? '<i class="bi bi-key-fill text-warning me-1"></i>' : ''}
                        ${this.formatNumber(col.unique_count)}
                    </td>
                    <td>
                        <small class="text-muted">${col.sample_values.map(v => this.escapeHtml(v)).join(', ')}</small>
                    </td>
                </tr>
            `;
        }).join('');
    }
    
    /**
     * Render preview table
     */
    renderPreviewTable(previewData, columns) {
        const headerRow = document.getElementById('previewTableHeader');
        const tbody = document.getElementById('previewTableBody');
        
        // Render header
        headerRow.innerHTML = `
            <tr>
                ${columns.map(col => `<th>${this.formatColumnName(col)}</th>`).join('')}
            </tr>
        `;
        
        // Render body
        tbody.innerHTML = previewData.map(row => {
            const cells = columns
                .map(col => `<td>${this.escapeHtml(row[col] || '-')}</td>`)
                .join('');
            return `<tr>${cells}</tr>`;
        }).join('');
    }
    
    /**
     * Confirm and execute export
     */
    confirmExport() {
        if (!this.previewData) {
            alert('No preview data available');
            return;
        }
        
        const config = this.currentConfig;
        
        // Build export URL with parameters
        const params = new URLSearchParams({
            format: config.format,
            report_type: config.reportType,
            ...config.filters
        });
        
        // Determine export endpoint
        const exportEndpoint = config.reportType === 'assets'
            ? '/assets/export/'
            : '/reports/generate/';
        
        // Show loading state on button
        const confirmBtn = document.getElementById('confirmExportBtn');
        const originalText = confirmBtn.innerHTML;
        confirmBtn.disabled = true;
        confirmBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Exporting...';
        
        // Trigger download
        window.location.href = `${exportEndpoint}?${params.toString()}`;
        
        // Close modal after short delay
        setTimeout(() => {
            this.modal.hide();
            confirmBtn.disabled = false;
            confirmBtn.innerHTML = originalText;
            
            // Show success toast
            this.showToast(
                'Export Started',
                `Exporting ${this.formatNumber(this.previewData.metrics.total_rows)} rows as ${config.format.toUpperCase()}...`,
                'success'
            );
        }, 1000);
    }
    
    // ======================
    // UTILITY FUNCTIONS
    // ======================
    
    formatNumber(num) {
        return new Intl.NumberFormat().format(num);
    }
    
    formatFileSize(kb) {
        if (kb < 1024) return `${kb} KB`;
        return `${(kb / 1024).toFixed(1)} MB`;
    }
    
    formatColumnName(name) {
        return name.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
    }
    
    getDataTypeIcon(type) {
        const icons = {
            'string': 'alphabet',
            'number': '123',
            'date': 'calendar3',
            'boolean': 'toggle-on'
        };
        return icons[type] || 'question-circle';
    }
    
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
    
    getCacheKey(config) {
        return JSON.stringify({
            type: config.reportType,
            format: config.format,
            filters: config.filters
        });
    }
    
    getFromCache(key) {
        const cached = this.cache.get(key);
        if (!cached) return null;
        
        // Check if expired
        if (Date.now() - cached.timestamp > this.cacheTTL) {
            this.cache.delete(key);
            return null;
        }
        
        return cached.data;
    }
    
    saveToCache(key, data) {
        this.cache.set(key, {
            data: data,
            timestamp: Date.now()
        });
        
        // Limit cache size
        if (this.cache.size > 10) {
            const firstKey = this.cache.keys().next().value;
            this.cache.delete(firstKey);
        }
    }
    
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
            <div id="${toastId}" class="toast align-items-center text-white ${bgClass} border-0" 
                 role="alert" aria-live="assertive" aria-atomic="true">
                <div class="d-flex">
                    <div class="toast-body">
                        <strong>${title}</strong><br>${message}
                    </div>
                    <button type="button" class="btn-close btn-close-white me-2 m-auto" 
                            data-bs-dismiss="toast" aria-label="Close"></button>
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

// Auto-initialize on DOM ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        window.unifiedExportPreviewManager = new UnifiedExportPreviewManager();
    });
} else {
    window.unifiedExportPreviewManager = new UnifiedExportPreviewManager();
}
