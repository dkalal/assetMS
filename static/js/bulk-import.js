/**
 * ============================================================================
 * BULK IMPORT SYSTEM - World-Class Asset Import
 * ============================================================================
 * 
 * Features:
 * - CSV/Excel file parsing
 * - Column mapping interface
 * - Data preview with validation
 * - Error highlighting (row-level)
 * - Batch import with progress bar
 * - Import history
 * - Template download
 * - Duplicate detection
 * - Multi-tenancy enforcement
 * 
 * Inspired by: Salesforce Data Loader, ServiceNow Import Sets, IBM Maximo
 * 
 * @version 1.0.0
 * @author Asset Management System
 * @license MIT
 */

class BulkImporter {
    /**
     * Initialize the bulk importer
     * @param {Object} options - Configuration options
     */
    constructor(options = {}) {
        this.options = {
            fileInputId: 'bulk-import-file',
            maxFileSize: 10 * 1024 * 1024, // 10MB
            maxRows: 1000,
            allowedTypes: ['.csv', '.xlsx', '.xls'],
            apiEndpoint: '/assets/api/bulk-import/',
            templateEndpoint: '/assets/api/bulk-import-template/',
            validationEndpoint: '/assets/api/validate-bulk-data/',
            ...options
        };

        this.parsedData = null;
        this.mappedData = null;
        this.validationResults = null;
        this.currentStep = 1;
        
        this.init();
    }

    /**
     * Initialize the importer
     */
    init() {
        console.log('🚀 Initializing Bulk Importer...');
        this.setupFileInput();
        this.setupEventListeners();
        this.loadImportHistory();
        console.log('✅ Bulk Importer Ready');
    }

    /**
     * Setup file input handling
     */
    setupFileInput() {
        const fileInput = document.getElementById(this.options.fileInputId);
        if (!fileInput) {
            console.error('File input not found:', this.options.fileInputId);
            return;
        }

        // File selection handler
        fileInput.addEventListener('change', (e) => {
            const file = e.target.files[0];
            if (file) {
                this.handleFileUpload(file);
            }
        });

        // Drag and drop
        const dropZone = document.getElementById('drop-zone');
        if (dropZone) {
            dropZone.addEventListener('dragover', (e) => {
                e.preventDefault();
                dropZone.classList.add('drag-over');
            });

            dropZone.addEventListener('dragleave', () => {
                dropZone.classList.remove('drag-over');
            });

            dropZone.addEventListener('drop', (e) => {
                e.preventDefault();
                dropZone.classList.remove('drag-over');
                
                const file = e.dataTransfer.files[0];
                if (file) {
                    fileInput.files = e.dataTransfer.files;
                    this.handleFileUpload(file);
                }
            });
        }
    }

    /**
     * Setup event listeners
     */
    setupEventListeners() {
        // Download template button
        const downloadBtn = document.getElementById('download-template-btn');
        if (downloadBtn) {
            downloadBtn.addEventListener('click', () => this.downloadTemplate());
        }

        // Next/Previous buttons
        const nextBtn = document.getElementById('next-step-btn');
        const prevBtn = document.getElementById('prev-step-btn');
        const importBtn = document.getElementById('import-btn');

        if (nextBtn) {
            nextBtn.addEventListener('click', () => this.nextStep());
        }

        if (prevBtn) {
            prevBtn.addEventListener('click', () => this.previousStep());
        }

        if (importBtn) {
            importBtn.addEventListener('click', () => this.executeImport());
        }
    }

    /**
     * Handle file upload
     * @param {File} file - The uploaded file
     */
    async handleFileUpload(file) {
        console.log('📂 File selected:', file.name);

        // Validate file
        const validation = this.validateFile(file);
        if (!validation.valid) {
            this.showError(validation.error);
            return;
        }

        // Show loading state
        this.showLoading('Parsing file...');

        try {
            // Parse file based on type
            if (file.name.endsWith('.csv')) {
                await this.parseCSV(file);
            } else if (file.name.endsWith('.xlsx') || file.name.endsWith('.xls')) {
                await this.parseExcel(file);
            }

            // Move to column mapping step
            this.currentStep = 2;
            this.renderColumnMapping();
            this.hideLoading();

        } catch (error) {
            console.error('Parse error:', error);
            this.showError('Failed to parse file: ' + error.message);
            this.hideLoading();
        }
    }

    /**
     * Validate uploaded file
     * @param {File} file - The file to validate
     * @returns {Object} - Validation result
     */
    validateFile(file) {
        // Check file size
        if (file.size > this.options.maxFileSize) {
            return {
                valid: false,
                error: `File size exceeds ${this.options.maxFileSize / 1024 / 1024}MB limit`
            };
        }

        // Check file type
        const extension = '.' + file.name.split('.').pop().toLowerCase();
        if (!this.options.allowedTypes.includes(extension)) {
            return {
                valid: false,
                error: `File type ${extension} not allowed. Use: ${this.options.allowedTypes.join(', ')}`
            };
        }

        return { valid: true };
    }

    /**
     * Parse CSV file
     * @param {File} file - The CSV file
     */
    async parseCSV(file) {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();

            reader.onload = (e) => {
                try {
                    const text = e.target.result;
                    const rows = this.parseCSVText(text);

                    if (rows.length === 0) {
                        reject(new Error('Empty file'));
                        return;
                    }

                    if (rows.length > this.options.maxRows) {
                        reject(new Error(`File contains ${rows.length} rows. Maximum allowed is ${this.options.maxRows}`));
                        return;
                    }

                    // First row is headers
                    const headers = rows[0];
                    const data = rows.slice(1);

                    this.parsedData = {
                        headers: headers,
                        rows: data,
                        fileName: file.name,
                        rowCount: data.length
                    };

                    console.log('✅ CSV parsed:', this.parsedData.rowCount, 'rows');
                    resolve(this.parsedData);

                } catch (error) {
                    reject(error);
                }
            };

            reader.onerror = () => reject(new Error('Failed to read file'));
            reader.readAsText(file);
        });
    }

    /**
     * Parse CSV text into rows
     * @param {string} text - CSV text
     * @returns {Array} - Parsed rows
     */
    parseCSVText(text) {
        const rows = [];
        let currentRow = [];
        let currentCell = '';
        let inQuotes = false;

        for (let i = 0; i < text.length; i++) {
            const char = text[i];
            const nextChar = text[i + 1];

            if (char === '"') {
                if (inQuotes && nextChar === '"') {
                    // Escaped quote
                    currentCell += '"';
                    i++; // Skip next quote
                } else {
                    // Toggle quote state
                    inQuotes = !inQuotes;
                }
            } else if (char === ',' && !inQuotes) {
                // End of cell
                currentRow.push(currentCell.trim());
                currentCell = '';
            } else if ((char === '\n' || char === '\r') && !inQuotes) {
                // End of row
                if (currentCell || currentRow.length > 0) {
                    currentRow.push(currentCell.trim());
                    rows.push(currentRow);
                    currentRow = [];
                    currentCell = '';
                }
                // Skip \r\n combination
                if (char === '\r' && nextChar === '\n') {
                    i++;
                }
            } else {
                currentCell += char;
            }
        }

        // Add last cell and row
        if (currentCell || currentRow.length > 0) {
            currentRow.push(currentCell.trim());
            rows.push(currentRow);
        }

        // Filter empty rows
        return rows.filter(row => row.some(cell => cell !== ''));
    }

    /**
     * Parse Excel file
     * @param {File} file - The Excel file
     */
    async parseExcel(file) {
        // For Excel parsing, we'll use the SheetJS library (xlsx.js)
        // This requires including the library in the template
        if (typeof XLSX === 'undefined') {
            throw new Error('Excel parsing library not loaded. Please include xlsx.js');
        }

        return new Promise((resolve, reject) => {
            const reader = new FileReader();

            reader.onload = (e) => {
                try {
                    const data = new Uint8Array(e.target.result);
                    const workbook = XLSX.read(data, { type: 'array' });

                    // Get first sheet
                    const firstSheet = workbook.Sheets[workbook.SheetNames[0]];
                    const jsonData = XLSX.utils.sheet_to_json(firstSheet, { header: 1 });

                    if (jsonData.length === 0) {
                        reject(new Error('Empty Excel file'));
                        return;
                    }

                    if (jsonData.length > this.options.maxRows) {
                        reject(new Error(`File contains ${jsonData.length} rows. Maximum allowed is ${this.options.maxRows}`));
                        return;
                    }

                    const headers = jsonData[0];
                    const rows = jsonData.slice(1);

                    this.parsedData = {
                        headers: headers,
                        rows: rows,
                        fileName: file.name,
                        rowCount: rows.length
                    };

                    console.log('✅ Excel parsed:', this.parsedData.rowCount, 'rows');
                    resolve(this.parsedData);

                } catch (error) {
                    reject(error);
                }
            };

            reader.onerror = () => reject(new Error('Failed to read Excel file'));
            reader.readAsArrayBuffer(file);
        });
    }

    /**
     * Render column mapping interface
     */
    renderColumnMapping() {
        const container = document.getElementById('column-mapping-container');
        if (!container) return;

        container.innerHTML = '';

        // Required fields for asset import
        const requiredFields = [
            { key: 'category', label: 'Category', required: true },
            { key: 'branch', label: 'Branch', required: true },
            { key: 'name', label: 'Asset Name', required: false },
            { key: 'serial_number', label: 'Serial Number', required: false },
            { key: 'asset_tag', label: 'Asset Tag', required: false },
            { key: 'description', label: 'Description', required: false },
            { key: 'purchase_value', label: 'Purchase Value', required: false },
            { key: 'purchase_date', label: 'Purchase Date', required: false },
            { key: 'assigned_to', label: 'Assigned To (Email/ID)', required: false }
        ];

        const html = `
            <div class="alert alert-info">
                <i class="bi bi-info-circle me-2"></i>
                <strong>Map your columns:</strong> Match your file columns to the corresponding asset fields.
                Fields marked with <span class="text-danger">*</span> are required.
            </div>
            <div class="row g-3">
                ${requiredFields.map(field => `
                    <div class="col-md-6">
                        <label class="form-label fw-semibold">
                            ${field.label}
                            ${field.required ? '<span class="text-danger">*</span>' : ''}
                        </label>
                        <select class="form-select column-map" data-field="${field.key}">
                            <option value="">-- Skip this field --</option>
                            ${this.parsedData.headers.map((header, idx) => `
                                <option value="${idx}" ${this.autoMapColumn(field.key, header) ? 'selected' : ''}>
                                    ${header || `Column ${idx + 1}`}
                                </option>
                            `).join('')}
                        </select>
                    </div>
                `).join('')}
            </div>
            <div class="mt-4">
                <button type="button" class="btn btn-primary" id="validate-mapping-btn">
                    <i class="bi bi-check-circle me-2"></i>Validate & Preview
                </button>
            </div>
        `;

        container.innerHTML = html;

        // Add validation button listener
        document.getElementById('validate-mapping-btn').addEventListener('click', () => {
            this.validateMapping();
        });

        // Show mapping step
        document.getElementById('step-1-container').classList.add('d-none');
        document.getElementById('step-2-container').classList.remove('d-none');
        this.updateStepIndicator(2);
    }

    /**
     * Auto-map column based on header name
     * @param {string} fieldKey - The field key
     * @param {string} header - The column header
     * @returns {boolean} - Whether to auto-select this column
     */
    autoMapColumn(fieldKey, header) {
        if (!header) return false;

        const headerLower = header.toLowerCase().trim();
        const mappings = {
            'category': ['category', 'asset category', 'type'],
            'branch': ['branch', 'location', 'branch name'],
            'name': ['name', 'asset name', 'title'],
            'serial_number': ['serial', 'serial number', 'sn', 'serial_number'],
            'asset_tag': ['asset tag', 'tag', 'asset_tag', 'tag number'],
            'description': ['description', 'desc', 'notes'],
            'purchase_value': ['value', 'purchase value', 'cost', 'price'],
            'purchase_date': ['purchase date', 'date', 'purchased'],
            'assigned_to': ['assigned to', 'user', 'owner', 'assigned']
        };

        const keywords = mappings[fieldKey] || [];
        return keywords.some(keyword => headerLower.includes(keyword));
    }

    /**
     * Validate column mapping
     */
    async validateMapping() {
        console.log('🔍 Validating column mapping...');

        // Get mappings
        const mappings = {};
        document.querySelectorAll('.column-map').forEach(select => {
            const field = select.dataset.field;
            const columnIndex = select.value;
            if (columnIndex !== '') {
                mappings[field] = parseInt(columnIndex);
            }
        });

        // Check required fields
        const requiredFields = ['category', 'branch'];
        const missingRequired = requiredFields.filter(field => mappings[field] === undefined);

        if (missingRequired.length > 0) {
            this.showError(`Please map required fields: ${missingRequired.join(', ')}`);
            return;
        }

        // Map data
        this.mappedData = this.parsedData.rows.map((row, index) => {
            const mapped = { _rowNumber: index + 1 };
            Object.keys(mappings).forEach(field => {
                const columnIndex = mappings[field];
                mapped[field] = row[columnIndex] || '';
            });
            return mapped;
        });

        console.log('✅ Mapped', this.mappedData.length, 'rows');

        // Validate data with backend
        await this.validateData();
    }

    /**
     * Validate mapped data with backend
     */
    async validateData() {
        this.showLoading('Validating data...');

        try {
            const response = await fetch(this.options.validationEndpoint, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify({
                    data: this.mappedData
                })
            });

            if (!response.ok) {
                throw new Error('Validation failed');
            }

            this.validationResults = await response.json();

            console.log('✅ Validation complete');
            console.log('Valid rows:', this.validationResults.valid_count);
            console.log('Invalid rows:', this.validationResults.invalid_count);

            // Move to preview step
            this.currentStep = 3;
            this.renderPreview();
            this.hideLoading();

        } catch (error) {
            console.error('Validation error:', error);
            this.showError('Failed to validate data: ' + error.message);
            this.hideLoading();
        }
    }

    /**
     * Render data preview
     */
    renderPreview() {
        const container = document.getElementById('preview-container');
        if (!container) return;

        const results = this.validationResults;
        const validRows = results.rows.filter(r => r.valid);
        const invalidRows = results.rows.filter(r => !r.valid);

        const html = `
            <div class="row mb-4">
                <div class="col-md-4">
                    <div class="card">
                        <div class="card-body text-center">
                            <div class="display-4 text-success">${validRows.length}</div>
                            <div class="text-muted">Valid Rows</div>
                        </div>
                    </div>
                </div>
                <div class="col-md-4">
                    <div class="card">
                        <div class="card-body text-center">
                            <div class="display-4 text-danger">${invalidRows.length}</div>
                            <div class="text-muted">Invalid Rows</div>
                        </div>
                    </div>
                </div>
                <div class="col-md-4">
                    <div class="card">
                        <div class="card-body text-center">
                            <div class="display-4 text-primary">${this.mappedData.length}</div>
                            <div class="text-muted">Total Rows</div>
                        </div>
                    </div>
                </div>
            </div>

            ${invalidRows.length > 0 ? `
                <div class="alert alert-warning">
                    <i class="bi bi-exclamation-triangle me-2"></i>
                    <strong>${invalidRows.length} rows have errors.</strong>
                    You can fix these in the table below or proceed to import only valid rows.
                </div>
            ` : `
                <div class="alert alert-success">
                    <i class="bi bi-check-circle me-2"></i>
                    <strong>All rows are valid!</strong> You can proceed with the import.
                </div>
            `}

            <div class="table-responsive" style="max-height: 500px; overflow-y: auto;">
                <table class="table table-bordered table-hover">
                    <thead class="table-light sticky-top">
                        <tr>
                            <th width="50">#</th>
                            <th width="70">Status</th>
                            ${Object.keys(this.mappedData[0]).filter(k => k !== '_rowNumber').map(key => `
                                <th>${this.formatFieldName(key)}</th>
                            `).join('')}
                            <th width="200">Errors</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${results.rows.map((row, idx) => `
                            <tr class="${row.valid ? 'table-success' : 'table-danger'}">
                                <td>${idx + 1}</td>
                                <td class="text-center">
                                    <i class="bi ${row.valid ? 'bi-check-circle-fill text-success' : 'bi-x-circle-fill text-danger'}"></i>
                                </td>
                                ${Object.keys(this.mappedData[idx]).filter(k => k !== '_rowNumber').map(key => `
                                    <td>${this.mappedData[idx][key]}</td>
                                `).join('')}
                                <td>
                                    ${row.errors && row.errors.length > 0 ? `
                                        <ul class="mb-0 small">
                                            ${row.errors.map(err => `<li>${err}</li>`).join('')}
                                        </ul>
                                    ` : '<span class="text-success">✓ Valid</span>'}
                                </td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            </div>

            <div class="mt-4">
                ${validRows.length > 0 ? `
                    <button type="button" class="btn btn-success btn-lg" id="proceed-import-btn">
                        <i class="bi bi-upload me-2"></i>Import ${validRows.length} Valid Row${validRows.length !== 1 ? 's' : ''}
                    </button>
                ` : `
                    <button type="button" class="btn btn-secondary btn-lg" disabled>
                        <i class="bi bi-x-circle me-2"></i>No Valid Rows to Import
                    </button>
                `}
                <button type="button" class="btn btn-outline-secondary btn-lg" id="back-to-mapping-btn">
                    <i class="bi bi-arrow-left me-2"></i>Back to Mapping
                </button>
            </div>
        `;

        container.innerHTML = html;

        // Add event listeners
        const proceedBtn = document.getElementById('proceed-import-btn');
        if (proceedBtn) {
            proceedBtn.addEventListener('click', () => this.executeImport());
        }

        const backBtn = document.getElementById('back-to-mapping-btn');
        if (backBtn) {
            backBtn.addEventListener('click', () => {
                this.currentStep = 2;
                this.renderColumnMapping();
            });
        }

        // Show preview step
        document.getElementById('step-2-container').classList.add('d-none');
        document.getElementById('step-3-container').classList.remove('d-none');
        this.updateStepIndicator(3);
    }

    /**
     * Execute bulk import
     */
    async executeImport() {
        console.log('🚀 Executing bulk import...');

        // CRITICAL FIX: Map using original indices, not filtered indices
        const validRows = this.validationResults.rows
            .map((result, originalIdx) => ({
                result: result,
                originalIdx: originalIdx,
                data: this.mappedData[originalIdx]
            }))
            .filter(item => item.result.valid)
            .map(item => item.data);

        if (validRows.length === 0) {
            this.showError('No valid rows to import');
            return;
        }

        console.log(`📤 Sending ${validRows.length} valid rows to backend (out of ${this.mappedData.length} total rows)`);

        // Confirm import
        const confirmed = confirm(`Import ${validRows.length} asset${validRows.length !== 1 ? 's' : ''}?`);
        if (!confirmed) return;

        // Show progress
        this.showImportProgress(0, validRows.length);

        try {
            const response = await fetch(this.options.apiEndpoint, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify({
                    assets: validRows
                })
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.message || 'Import failed');
            }

            const result = await response.json();

            console.log('✅ Import complete');
            console.log('Created:', result.created_count);
            console.log('Failed:', result.failed_count);

            this.showImportProgress(result.created_count, validRows.length);
            
            // Show detailed results
            this.showImportResults(result);

            // If there were failures, show them
            if (result.failed_count > 0 && result.errors && result.errors.length > 0) {
                this.showFailedImports(result.errors);
            }

            // Success message
            if (result.created_count > 0) {
                this.showSuccess(`Successfully imported ${result.created_count} asset${result.created_count !== 1 ? 's' : ''}!`);
            }

            // If all succeeded, redirect after 3 seconds
            if (result.failed_count === 0) {
                setTimeout(() => {
                    window.location.href = '/assets/';
                }, 3000);
            }

        } catch (error) {
            console.error('Import error:', error);
            this.showError('Import failed: ' + error.message);
        }
    }

    /**
     * Download import template
     */
    async downloadTemplate() {
        console.log('📥 Downloading template...');

        try {
            const response = await fetch(this.options.templateEndpoint);
            const blob = await response.blob();
            
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'asset_import_template.csv';
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            window.URL.revokeObjectURL(url);

            console.log('✅ Template downloaded');
        } catch (error) {
            console.error('Download error:', error);
            this.showError('Failed to download template');
        }
    }

    /**
     * Load import history
     */
    async loadImportHistory() {
        // TODO: Implement import history loading from backend
        console.log('📜 Loading import history...');
    }

    /**
     * Update step indicator
     * @param {number} step - Current step
     */
    updateStepIndicator(step) {
        for (let i = 1; i <= 3; i++) {
            const indicator = document.getElementById(`step-${i}-indicator`);
            if (indicator) {
                if (i < step) {
                    indicator.classList.add('completed');
                    indicator.classList.remove('active');
                } else if (i === step) {
                    indicator.classList.add('active');
                    indicator.classList.remove('completed');
                } else {
                    indicator.classList.remove('active', 'completed');
                }
            }
        }
    }

    /**
     * Next step
     */
    nextStep() {
        if (this.currentStep < 3) {
            this.currentStep++;
            this.updateStepIndicator(this.currentStep);
        }
    }

    /**
     * Previous step
     */
    previousStep() {
        if (this.currentStep > 1) {
            this.currentStep--;
            this.updateStepIndicator(this.currentStep);
        }
    }

    /**
     * Show loading state
     * @param {string} message - Loading message
     */
    showLoading(message = 'Loading...') {
        const loading = document.getElementById('loading-overlay');
        if (loading) {
            loading.querySelector('.loading-text').textContent = message;
            loading.classList.remove('d-none');
        }
    }

    /**
     * Hide loading state
     */
    hideLoading() {
        const loading = document.getElementById('loading-overlay');
        if (loading) {
            loading.classList.add('d-none');
        }
    }

    /**
     * Show import progress
     * @param {number} current - Current progress
     * @param {number} total - Total items
     */
    showImportProgress(current, total) {
        const progress = document.getElementById('import-progress');
        if (progress) {
            const percentage = Math.round((current / total) * 100);
            progress.querySelector('.progress-bar').style.width = percentage + '%';
            progress.querySelector('.progress-bar').textContent = `${current} / ${total}`;
            progress.classList.remove('d-none');
        }
    }

    /**
     * Show import results summary
     * @param {Object} result - Import result object
     */
    showImportResults(result) {
        const container = document.getElementById('import-results');
        if (!container) return;

        const html = `
            <div class="alert alert-${result.failed_count === 0 ? 'success' : 'warning'} mt-4">
                <h5 class="alert-heading">
                    <i class="bi bi-${result.failed_count === 0 ? 'check-circle' : 'exclamation-triangle'}"></i>
                    Import Complete!
                </h5>
                <hr>
                <div class="row text-center">
                    <div class="col-md-4">
                        <div class="p-3">
                            <i class="bi bi-check-circle text-success" style="font-size: 2rem;"></i>
                            <h3 class="mt-2">${result.created_count}</h3>
                            <p class="text-muted mb-0">Assets Imported</p>
                        </div>
                    </div>
                    <div class="col-md-4">
                        <div class="p-3">
                            <i class="bi bi-x-circle text-danger" style="font-size: 2rem;"></i>
                            <h3 class="mt-2">${result.failed_count}</h3>
                            <p class="text-muted mb-0">Failed Rows</p>
                        </div>
                    </div>
                    <div class="col-md-4">
                        <div class="p-3">
                            <i class="bi bi-percent text-primary" style="font-size: 2rem;"></i>
                            <h3 class="mt-2">${Math.round((result.created_count / (result.created_count + result.failed_count)) * 100)}%</h3>
                            <p class="text-muted mb-0">Success Rate</p>
                        </div>
                    </div>
                </div>
            </div>
        `;

        container.innerHTML = html;
        container.classList.remove('d-none');
    }

    /**
     * Show failed imports with user-friendly errors
     * @param {Array} errors - Array of error objects
     */
    showFailedImports(errors) {
        const container = document.getElementById('failed-imports');
        if (!container) return;

        const errorRows = errors.map(err => `
            <tr>
                <td class="text-center">
                    <span class="badge bg-danger">${err.row}</span>
                </td>
                <td>
                    <div class="error-message">
                        <i class="bi bi-exclamation-circle text-danger me-2"></i>
                        ${err.error}
                    </div>
                    ${err.technical_error && err.technical_error !== err.error ? `
                        <details class="mt-2">
                            <summary class="text-muted small" style="cursor: pointer;">
                                <i class="bi bi-code-slash"></i> Technical Details
                            </summary>
                            <pre class="small text-muted mt-2 p-2 bg-light rounded">${err.technical_error}</pre>
                        </details>
                    ` : ''}
                </td>
            </tr>
        `).join('');

        const html = `
            <div class="card border-danger mt-4">
                <div class="card-header bg-danger text-white">
                    <h5 class="mb-0">
                        <i class="bi bi-exclamation-triangle"></i>
                        Failed Imports (${errors.length} row${errors.length !== 1 ? 's' : ''})
                    </h5>
                </div>
                <div class="card-body p-0">
                    <div class="table-responsive">
                        <table class="table table-hover mb-0">
                            <thead class="table-light">
                                <tr>
                                    <th style="width: 100px;" class="text-center">Row #</th>
                                    <th>Error Details</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${errorRows}
                            </tbody>
                        </table>
                    </div>
                </div>
                <div class="card-footer bg-light">
                    <div class="d-flex justify-content-between align-items-center">
                        <small class="text-muted">
                            <i class="bi bi-info-circle"></i>
                            Fix the errors in your file and try importing again
                        </small>
                        <button type="button" class="btn btn-sm btn-outline-primary" onclick="window.location.reload()">
                            <i class="bi bi-arrow-clockwise"></i> Start New Import
                        </button>
                    </div>
                </div>
            </div>
        `;

        container.innerHTML = html;
        container.classList.remove('d-none');

        // Scroll to failed imports
        container.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }

    /**
     * Show error message
     * @param {string} message - Error message
     */
    showError(message) {
        alert('Error: ' + message);
        // TODO: Use better notification system
    }

    /**
     * Show success message
     * @param {string} message - Success message
     */
    showSuccess(message) {
        alert(message);
        // TODO: Use better notification system
    }

    /**
     * Format field name for display
     * @param {string} fieldName - Field name
     * @returns {string} - Formatted name
     */
    formatFieldName(fieldName) {
        return fieldName
            .replace(/_/g, ' ')
            .replace(/\b\w/g, l => l.toUpperCase());
    }

    /**
     * Get CSRF token
     * @returns {string} - CSRF token
     */
    getCSRFToken() {
        return document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';
    }
}

// Auto-initialize if the page has bulk import container
document.addEventListener('DOMContentLoaded', function() {
    const bulkImportContainer = document.getElementById('bulk-import-container');
    if (bulkImportContainer) {
        window.bulkImporter = new BulkImporter();
        console.log('✅ Bulk Importer Auto-Initialized');
    }
});
