/**
 * Asset Status Change - Dynamic Fields Handler
 * World-Class UI/UX for Status Transitions
 * 
 * Inspired by: ServiceNow ITAM, IBM Maximo, SAP EAM
 * Features:
 * - Dynamic field visibility based on status selection
 * - Real-time validation feedback
 * - Confirmation modals for critical transitions
 * - Character counters and helpful hints
 * - Accessibility compliant (WCAG 2.1 AA)
 */

(function() {
    'use strict';
    
    // ========================================
    // CONFIGURATION
    // ========================================
    
    const CONFIG = {
        selectors: {
            statusSelect: '#id_status',
            dynamicContainer: '#dynamic-fields-container',
            form: 'form[method="post"]'
        },
        statusFields: {
            in_maintenance: ['status_change_reason', 'maintenance_type'],
            retired: ['status_change_reason', 'disposal_method', 'salvage_value'],
            lost: ['status_change_reason', 'loss_date', 'loss_reason', 'loss_details', 'last_known_location', 'police_report_number'],
            deleted: ['status_change_reason']
        },
        criticalStatuses: ['lost', 'retired', 'deleted'],
        minReasonLength: 10,
        minDetailsLength: 20
    };
    
    // ========================================
    // FIELD TEMPLATES
    // ========================================
    
    const FIELD_TEMPLATES = {
        status_change_reason: {
            label: 'Reason for Status Change',
            type: 'textarea',
            required: true,
            icon: 'chat-left-text',
            placeholder: 'Explain why you are changing the status (minimum 10 characters)...',
            helpText: 'This will be recorded in the audit log and may trigger notifications.',
            rows: 3,
            minLength: 10
        },
        maintenance_type: {
            label: 'Maintenance Type',
            type: 'select',
            required: true,
            icon: 'tools',
            options: [
                { value: '', label: '-- Select Maintenance Type --' },
                { value: 'preventive', label: 'Preventive Maintenance' },
                { value: 'corrective', label: 'Corrective Maintenance' },
                { value: 'emergency', label: 'Emergency Maintenance' }
            ],
            helpText: 'Select the type of maintenance being performed.'
        },
        disposal_method: {
            label: 'Disposal Method',
            type: 'select',
            required: true,
            icon: 'recycle',
            options: [
                { value: '', label: '-- Select Disposal Method --' },
                { value: 'sell', label: 'Sell' },
                { value: 'donate', label: 'Donate' },
                { value: 'scrap', label: 'Scrap' },
                { value: 'recycle', label: 'Recycle' },
                { value: 'transfer', label: 'Transfer to another entity' }
            ],
            helpText: 'How will this asset be disposed of?'
        },
        salvage_value: {
            label: 'Salvage Value (Optional)',
            type: 'number',
            required: false,
            icon: 'currency-dollar',
            placeholder: '0.00',
            helpText: 'Estimated resale or salvage value',
            step: '0.01',
            min: '0'
        },
        loss_date: {
            label: 'Date Lost/Stolen',
            type: 'date',
            required: true,
            icon: 'calendar-event',
            helpText: 'When was the asset lost or stolen?'
        },
        loss_reason: {
            label: 'Loss Reason',
            type: 'select',
            required: true,
            icon: 'exclamation-triangle',
            options: [
                { value: '', label: '-- Select Loss Reason --' },
                { value: 'lost', label: 'Lost/Misplaced' },
                { value: 'stolen', label: 'Stolen' },
                { value: 'damaged_beyond_repair', label: 'Damaged Beyond Repair' }
            ],
            helpText: 'Select the reason for loss.'
        },
        loss_details: {
            label: 'Loss Details',
            type: 'textarea',
            required: true,
            icon: 'file-text',
            placeholder: 'Provide detailed description of circumstances (minimum 20 characters)...',
            helpText: 'Include all relevant details: location, time, witnesses, etc.',
            rows: 4,
            minLength: 20
        },
        last_known_location: {
            label: 'Last Known Location',
            type: 'text',
            required: false,
            icon: 'geo-alt',
            placeholder: 'e.g., Building A, Floor 3, Room 301',
            helpText: 'Where was the asset last seen?'
        },
        police_report_number: {
            label: 'Police Report Number',
            type: 'text',
            required: false,
            icon: 'shield-check',
            placeholder: 'e.g., PR-2025-001234',
            helpText: 'Required if asset was stolen',
            conditional: { field: 'loss_reason', value: 'stolen' }
        }
    };
    
    // ========================================
    // MAIN CLASS
    // ========================================
    
    class AssetStatusFieldsManager {
        constructor() {
            this.statusSelect = document.querySelector(CONFIG.selectors.statusSelect);
            this.dynamicContainer = document.querySelector(CONFIG.selectors.dynamicContainer);
            this.form = document.querySelector(CONFIG.selectors.form);
            this.originalStatus = null;
            this.currentFields = {};
            
            if (!this.statusSelect || !this.dynamicContainer) {
                console.warn('Asset status fields manager: Required elements not found');
                return;
            }
            
            this.init();
        }
        
        init() {
            // Store original status
            this.originalStatus = this.statusSelect.value;
            this.statusSelect.dataset.originalStatus = this.originalStatus;
            
            // Bind events
            this.statusSelect.addEventListener('change', this.handleStatusChange.bind(this));
            
            // Handle conditional fields (e.g., police report for stolen assets)
            this.dynamicContainer.addEventListener('change', this.handleConditionalFields.bind(this));
            
            // Form validation
            if (this.form) {
                this.form.addEventListener('submit', this.handleFormSubmit.bind(this));
            }
            
            // Initialize with current status
            this.renderFields(this.statusSelect.value, false);
            
            console.log('✅ Asset Status Fields Manager initialized');
        }
        
        handleStatusChange(e) {
            const newStatus = e.target.value;
            const oldStatus = this.originalStatus;
            
            // Check if this is a critical status change
            if (CONFIG.criticalStatuses.includes(newStatus) && oldStatus !== newStatus) {
                if (!this.confirmCriticalChange(newStatus, oldStatus)) {
                    e.target.value = oldStatus;
                    this.renderFields(oldStatus, false);
                    return;
                }
            }
            
            // Render appropriate fields
            this.renderFields(newStatus, true);
        }
        
        confirmCriticalChange(newStatus, oldStatus) {
            const statusLabels = {
                lost: 'Lost',
                retired: 'Retired',
                deleted: 'Deleted'
            };
            
            const warnings = {
                lost: [
                    'Trigger high-priority alert to administrators',
                    'Require detailed explanation and circumstances',
                    'May require police report if stolen',
                    'Initiate asset recovery procedures'
                ],
                retired: [
                    'Permanently remove asset from active inventory',
                    'Require disposal method and reason',
                    'Cancel all scheduled maintenance',
                    'Unassign from current user'
                ],
                deleted: [
                    'Soft-delete asset (30-day recovery window)',
                    'Remove from all active workflows',
                    'Require administrator approval',
                    'Permanently delete after 30 days'
                ]
            };
            
            const message = 
                `⚠️ CRITICAL STATUS CHANGE WARNING\n\n` +
                `You are about to mark this asset as "${statusLabels[newStatus]}".\n\n` +
                `This action will:\n` +
                warnings[newStatus].map(w => `  • ${w}`).join('\n') +
                `\n\nThis change will be permanently recorded in the audit log.\n\n` +
                `Are you absolutely sure you want to continue?`;
            
            return confirm(message);
        }
        
        renderFields(status, animate = true) {
            const fieldsToShow = CONFIG.statusFields[status] || [];
            
            // Clear existing fields
            this.dynamicContainer.innerHTML = '';
            this.currentFields = {};
            
            // WORLD-CLASS: Handle "transferred" status with informative message
            if (status === 'transferred') {
                const infoCard = document.createElement('div');
                infoCard.className = 'alert alert-info border-info';
                infoCard.innerHTML = `
                    <div class="d-flex align-items-start">
                        <i class="bi bi-info-circle-fill fs-4 me-3"></i>
                        <div>
                            <h6 class="alert-heading mb-2">
                                <i class="bi bi-arrow-left-right me-1"></i>
                                Transfer Workflow
                            </h6>
                            <p class="mb-2">
                                The "Transferred" status indicates this asset is currently in the transfer workflow.
                            </p>
                            <p class="mb-2">
                                <strong>To initiate a transfer:</strong>
                            </p>
                            <ol class="mb-2 ps-3">
                                <li>Keep status as "Active"</li>
                                <li>Save the asset</li>
                                <li>Go to asset detail page</li>
                                <li>Click "Transfer Asset" button</li>
                                <li>Select recipient and destination branch</li>
                            </ol>
                            <p class="mb-0 small">
                                <i class="bi bi-shield-check me-1"></i>
                                <strong>Note:</strong> Transfers require 2-level approval (Receiver → Admin) for security and accountability.
                            </p>
                        </div>
                    </div>
                `;
                this.dynamicContainer.appendChild(infoCard);
                return;
            }
            
            if (fieldsToShow.length === 0) {
                return;
            }
            
            // Create card container
            const card = this.createCard(status);
            
            // Render each field
            fieldsToShow.forEach(fieldName => {
                const template = FIELD_TEMPLATES[fieldName];
                if (!template) return;
                
                const fieldElement = this.createField(fieldName, template);
                card.querySelector('.card-body').appendChild(fieldElement);
                this.currentFields[fieldName] = fieldElement;
            });
            
            this.dynamicContainer.appendChild(card);
            
            // Animate entrance
            if (animate) {
                card.style.opacity = '0';
                card.style.transform = 'translateY(-10px)';
                setTimeout(() => {
                    card.style.transition = 'all 0.3s ease';
                    card.style.opacity = '1';
                    card.style.transform = 'translateY(0)';
                }, 10);
            }
            
            // Focus first required field
            const firstRequired = card.querySelector('[required]');
            if (firstRequired && animate) {
                setTimeout(() => firstRequired.focus(), 350);
            }
        }
        
        createCard(status) {
            const statusLabels = {
                in_maintenance: { title: 'Maintenance Details', icon: 'tools', color: 'warning' },
                retired: { title: 'Retirement Details', icon: 'archive', color: 'secondary' },
                lost: { title: 'Loss Report Details', icon: 'exclamation-triangle', color: 'danger' },
                deleted: { title: 'Deletion Details', icon: 'trash', color: 'danger' }
            };
            
            const config = statusLabels[status] || { title: 'Additional Details', icon: 'info-circle', color: 'info' };
            
            const card = document.createElement('div');
            card.className = 'card border-' + config.color + ' shadow-sm';
            card.innerHTML = `
                <div class="card-header bg-${config.color} text-white">
                    <h6 class="mb-0">
                        <i class="bi bi-${config.icon} me-2"></i>
                        ${config.title}
                        <span class="badge bg-white text-${config.color} ms-2">Required</span>
                    </h6>
                </div>
                <div class="card-body"></div>
            `;
            
            return card;
        }
        
        createField(fieldName, template) {
            const wrapper = document.createElement('div');
            wrapper.className = 'mb-3';
            wrapper.dataset.fieldName = fieldName;
            
            // Label
            const label = document.createElement('label');
            label.className = 'form-label fw-semibold';
            label.htmlFor = `id_${fieldName}`;
            label.innerHTML = `
                <i class="bi bi-${template.icon} me-1 text-primary"></i>
                ${template.label}
                ${template.required ? '<span class="text-danger">*</span>' : ''}
            `;
            wrapper.appendChild(label);
            
            // Input/Select/Textarea
            let input;
            
            if (template.type === 'textarea') {
                input = document.createElement('textarea');
                input.rows = template.rows || 3;
            } else if (template.type === 'select') {
                input = document.createElement('select');
                template.options.forEach(opt => {
                    const option = document.createElement('option');
                    option.value = opt.value;
                    option.textContent = opt.label;
                    input.appendChild(option);
                });
            } else {
                input = document.createElement('input');
                input.type = template.type;
                if (template.step) input.step = template.step;
                if (template.min) input.min = template.min;
            }
            
            input.id = `id_${fieldName}`;
            input.name = fieldName;
            input.className = template.type === 'select' ? 'form-select' : 'form-control';
            
            if (template.placeholder) input.placeholder = template.placeholder;
            if (template.required) input.required = true;
            if (template.minLength) input.dataset.minLength = template.minLength;
            
            wrapper.appendChild(input);
            
            // Help text
            if (template.helpText) {
                const helpText = document.createElement('div');
                helpText.className = 'form-text';
                helpText.innerHTML = `<i class="bi bi-info-circle me-1"></i>${template.helpText}`;
                wrapper.appendChild(helpText);
            }
            
            // Character counter for textareas
            if (template.type === 'textarea' && template.minLength) {
                const counter = document.createElement('div');
                counter.className = 'form-text text-end';
                counter.id = `${fieldName}_counter`;
                wrapper.appendChild(counter);
                
                input.addEventListener('input', () => {
                    const length = input.value.length;
                    const min = template.minLength;
                    counter.textContent = `${length} characters`;
                    
                    if (length < min) {
                        counter.classList.add('text-danger', 'fw-bold');
                        counter.textContent = `${length} / ${min} characters (${min - length} more needed)`;
                    } else {
                        counter.classList.remove('text-danger', 'fw-bold');
                        counter.classList.add('text-success');
                        counter.textContent = `${length} characters ✓`;
                    }
                });
                
                // Trigger initial update
                input.dispatchEvent(new Event('input'));
            }
            
            // Real-time validation
            input.addEventListener('blur', () => this.validateField(input, template));
            input.addEventListener('input', () => {
                if (input.classList.contains('is-invalid')) {
                    this.validateField(input, template);
                }
            });
            
            return wrapper;
        }
        
        handleConditionalFields(e) {
            const target = e.target;
            
            // Handle police report requirement for stolen assets
            if (target.name === 'loss_reason') {
                const policeReportField = this.currentFields['police_report_number'];
                if (policeReportField) {
                    const input = policeReportField.querySelector('input');
                    if (target.value === 'stolen') {
                        input.required = true;
                        policeReportField.querySelector('.form-label').innerHTML = policeReportField.querySelector('.form-label').innerHTML.replace('(Optional)', '').trim() + ' <span class="text-danger">*</span>';
                        policeReportField.querySelector('.form-text').innerHTML = '<i class="bi bi-exclamation-triangle-fill text-danger me-1"></i><strong>Required</strong> for stolen assets';
                    } else {
                        input.required = false;
                        policeReportField.querySelector('.form-label').innerHTML = policeReportField.querySelector('.form-label').innerHTML.replace('<span class="text-danger">*</span>', '');
                        policeReportField.querySelector('.form-text').innerHTML = '<i class="bi bi-info-circle me-1"></i>Required if asset was stolen';
                    }
                }
            }
        }
        
        validateField(input, template) {
            let isValid = true;
            let errorMessage = '';
            
            // Required check
            if (template.required && !input.value.trim()) {
                isValid = false;
                errorMessage = `${template.label} is required.`;
            }
            
            // Min length check
            if (template.minLength && input.value.trim().length < template.minLength) {
                isValid = false;
                errorMessage = `Please provide at least ${template.minLength} characters.`;
            }
            
            // Update UI
            if (isValid) {
                input.classList.remove('is-invalid');
                input.classList.add('is-valid');
                this.removeFieldError(input);
            } else {
                input.classList.remove('is-valid');
                input.classList.add('is-invalid');
                this.showFieldError(input, errorMessage);
            }
            
            return isValid;
        }
        
        showFieldError(input, message) {
            this.removeFieldError(input);
            
            const errorDiv = document.createElement('div');
            errorDiv.className = 'invalid-feedback d-block';
            errorDiv.textContent = message;
            input.parentNode.appendChild(errorDiv);
        }
        
        removeFieldError(input) {
            const existingError = input.parentNode.querySelector('.invalid-feedback');
            if (existingError) {
                existingError.remove();
            }
        }
        
        handleFormSubmit(e) {
            const currentStatus = this.statusSelect.value;
            const fieldsToValidate = CONFIG.statusFields[currentStatus] || [];
            
            let isValid = true;
            const errors = [];
            
            fieldsToValidate.forEach(fieldName => {
                const template = FIELD_TEMPLATES[fieldName];
                const fieldWrapper = this.currentFields[fieldName];
                
                if (!fieldWrapper || !template) return;
                
                const input = fieldWrapper.querySelector('input, select, textarea');
                if (!input) return;
                
                if (!this.validateField(input, template)) {
                    isValid = false;
                    errors.push(template.label);
                }
            });
            
            if (!isValid) {
                e.preventDefault();
                
                alert(
                    `⚠️ Validation Error\n\n` +
                    `Please correct the following fields:\n` +
                    errors.map(e => `  • ${e}`).join('\n')
                );
                
                // Focus first invalid field
                const firstInvalid = this.dynamicContainer.querySelector('.is-invalid');
                if (firstInvalid) {
                    firstInvalid.focus();
                    firstInvalid.scrollIntoView({ behavior: 'smooth', block: 'center' });
                }
                
                return false;
            }
        }
    }
    
    // ========================================
    // INITIALIZATION
    // ========================================
    
    // Wait for DOM to be ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => {
            new AssetStatusFieldsManager();
        });
    } else {
        new AssetStatusFieldsManager();
    }
    
})();
