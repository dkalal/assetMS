/**
 * Enhanced Asset Registration Form
 * World-class implementation supporting all wizard field types
 * 
 * Features:
 * - Supports TEXT, NUMBER, DATE, SELECT, TEXTAREA, FILE fields
 * - Real-time validation with inline feedback
 * - Wizard integration button
 * - Dynamic user filtering by branch
 * - Professional error handling
 */

class AssetRegistrationForm {
    constructor() {
        this.categorySelect = document.getElementById('id_category');
        this.dynamicFieldsContainer = document.getElementById('dynamic-fields-container');
        this.branchSelect = document.getElementById('id_branch');
        this.assignedToSelect = document.getElementById('id_assigned_to');
        
        // CRITICAL FIX: Select the asset registration form specifically, not navbar search form
        // The asset form has method="post" and enctype="multipart/form-data"
        this.form = document.querySelector('form[method="post"][enctype="multipart/form-data"]');
        
        // Fallback: if no form with enctype, look for form with category field inside it
        if (!this.form && this.categorySelect) {
            this.form = this.categorySelect.closest('form');
        }
        
        // Final fallback: any POST form (but not GET search forms)
        if (!this.form) {
            this.form = document.querySelector('form[method="post"]');
        }
        
        if (!this.form) {
            console.error('❌ Asset Registration Form: Could not find asset registration form');
            return;
        }
        
        console.log('✅ Asset Registration Form: Found form', this.form);
        
        this.currentCategory = null;
        this.currentFields = {};
        this.validationRules = {};
        
        console.log('🚀 Enhanced Asset Registration Form - Initialized');
        this.init();
    }
    
    init() {
        // Category change handler
        if (this.categorySelect) {
            // Load on page load (for edit forms)
            if (this.categorySelect.value) {
                this.loadCategoryFields(this.categorySelect.value);
            }
            
            this.categorySelect.addEventListener('change', (e) => {
                this.loadCategoryFields(e.target.value);
            });
            
            // Add wizard integration button
            this.addWizardButton();
        }
        
        // Branch change handler - dynamically filter users by selected branch
        if (this.branchSelect && this.assignedToSelect) {
            this.branchSelect.addEventListener('change', (e) => {
                this.filterUsersByBranch(e.target.value);
            });
            
            // Trigger initial filtering if branch is pre-selected
            if (this.branchSelect.value) {
                this.filterUsersByBranch(this.branchSelect.value);
            }
        }
        
        // Form submission validation
        // CRITICAL FIX: Only validate if we have dynamic fields loaded
        // For edit forms, server-side validation is primary
        if (this.form) {
            this.form.addEventListener('submit', (e) => {
                // Only validate if we have dynamic fields to validate
                if (Object.keys(this.currentFields).length > 0) {
                    if (!this.validateForm()) {
                        e.preventDefault();
                        this.showGlobalError('Please fix the errors before submitting');
                        return false;
                    }
                }
                // If no dynamic fields, let form submit normally (server validates)
                console.log('✅ Form validation passed, submitting...');
            });
        }
        
        // Image preview (existing functionality)
        this.setupImagePreview();
    }
    
    async loadCategoryFields(categoryId) {
        if (!categoryId) {
            this.dynamicFieldsContainer.innerHTML = '';
            this.currentFields = {};
            return;
        }
        
        this.showLoading();
        
        try {
            const response = await fetch(
                `/assets/api/category-fields-enhanced/?category_id=${encodeURIComponent(categoryId)}`
            );
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            
            if (data.success) {
                this.currentCategory = data.category;
                this.currentFields = data.fields;
                this.renderFields(data.fields, data.category);
                console.log('✅ Category fields loaded:', Object.keys(data.fields).length, 'fields');
            } else {
                this.showError(data.error || 'Failed to load category fields');
            }
        } catch (error) {
            console.error('❌ Error loading fields:', error);
            this.showError(`Network error: ${error.message}. Please check your connection and try again.`);
        }
    }
    
    renderFields(fields, category) {
        if (!fields || Object.keys(fields).length === 0) {
            this.dynamicFieldsContainer.innerHTML = `
                <div class="alert alert-info shadow-sm">
                    <i class="bi bi-info-circle me-2"></i>
                    <strong>No additional fields</strong> required for this category.
                </div>
            `;
            return;
        }
        
        const html = `
            <div class="card border-primary mb-3 shadow-sm">
                <div class="card-header bg-primary text-white d-flex justify-content-between align-items-center">
                    <span>
                        <i class="bi bi-list-check me-2"></i>
                        <strong>${this.escapeHtml(category.name)}</strong> - Category Fields
                    </span>
                    ${category.template_name ? 
                        `<span class="badge bg-light text-primary px-3">
                            <i class="bi bi-magic me-1"></i>Template: ${this.escapeHtml(category.template_name)}
                        </span>` : 
                        ''}
                </div>
                <div class="card-body">
                    <div class="row g-3" id="dynamic-fields-grid">
                        ${Object.entries(fields).map(([key, field]) => 
                            this.renderFieldInput(key, field)
                        ).join('')}
                    </div>
                </div>
                <div class="card-footer small text-muted">
                    <i class="bi bi-info-circle me-1"></i>
                    Fields marked with <span class="text-danger">*</span> are required
                </div>
            </div>
        `;
        
        this.dynamicFieldsContainer.innerHTML = html;
        
        // Setup validation listeners
        this.setupFieldValidation();
        
        // Prefill for edit forms
        this.prefillDynamicFields();
        
        console.log('✅ Fields rendered:', Object.keys(fields).length);
    }
    
    renderFieldInput(key, field) {
        const fieldId = `id_dyn_${key}`;
        const fieldName = `dyn_${key}`;
        const required = field.required;
        const requiredMark = required ? '<span class="text-danger" title="Required">*</span>' : '';
        
        // Determine column width based on field type
        let colClass = 'col-md-6'; // Default: half width
        if (field.type === 'textarea' || field.type === 'file') {
            colClass = 'col-12'; // Full width for textarea and file
        }
        
        // Build input HTML
        let inputHTML = '';
        const baseClass = (field.type === 'select') ? 'form-select' : 'form-control';
        const commonAttrs = `
            name="${fieldName}"
            id="${fieldId}"
            class="${baseClass}"
            ${required ? 'required' : ''}
            ${field.placeholder ? `placeholder="${this.escapeHtml(field.placeholder)}"` : ''}
            aria-label="${this.escapeHtml(field.label)}"
            data-field-type="${field.type}"
        `.trim();
        
        switch (field.type) {
            case 'text':
                inputHTML = `
                    <input type="text" ${commonAttrs}
                           maxlength="${field.max_length || 255}"
                           autocomplete="off">
                `;
                break;
            
            case 'textarea':
                inputHTML = `
                    <textarea ${commonAttrs}
                              rows="3"
                              maxlength="${field.max_length || 1000}"></textarea>
                `;
                break;
            
            case 'number':
                inputHTML = `
                    <input type="number" ${commonAttrs}
                           ${field.min_value !== null && field.min_value !== undefined ? `min="${field.min_value}"` : ''}
                           ${field.max_value !== null && field.max_value !== undefined ? `max="${field.max_value}"` : ''}
                           step="any"
                           autocomplete="off">
                `;
                break;
            
            case 'date':
                inputHTML = `
                    <input type="date" ${commonAttrs}
                           autocomplete="off">
                `;
                break;
            
            case 'select':
                const options = field.options || [];
                inputHTML = `
                    <select ${commonAttrs}>
                        <option value="">-- Select ${this.escapeHtml(field.label)} --</option>
                        ${options.map(opt => 
                            `<option value="${this.escapeHtml(opt)}">${this.escapeHtml(opt)}</option>`
                        ).join('')}
                    </select>
                `;
                break;
            
            case 'file':
                inputHTML = `
                    <input type="file" ${commonAttrs}>
                    <small class="form-text text-muted d-block mt-1">
                        <i class="bi bi-info-circle me-1"></i>
                        ${field.help_text || 'Max size: 5MB'}
                    </small>
                `;
                break;
            
            default:
                inputHTML = `<input type="text" ${commonAttrs} autocomplete="off">`;
        }
        
        return `
            <div class="${colClass}">
                <label for="${fieldId}" class="form-label fw-semibold">
                    ${this.escapeHtml(field.label)} ${requiredMark}
                </label>
                ${inputHTML}
                ${field.help_text && field.type !== 'file' ? 
                    `<small class="form-text text-muted d-block mt-1">
                        <i class="bi bi-info-circle me-1"></i>${this.escapeHtml(field.help_text)}
                    </small>` : 
                    ''}
                <div class="invalid-feedback" id="${fieldId}-error"></div>
            </div>
        `;
    }
    
    setupFieldValidation() {
        Object.entries(this.currentFields).forEach(([key, field]) => {
            const input = document.getElementById(`id_dyn_${key}`);
            if (!input) return;
            
            // Validate on blur
            input.addEventListener('blur', () => {
                this.validateField(input, field);
            });
            
            // Real-time validation for specific types
            if (field.type === 'number') {
                input.addEventListener('input', () => {
                    this.validateNumberField(input, field);
                });
            }
            
            if (field.type === 'select') {
                input.addEventListener('change', () => {
                    this.validateField(input, field);
                });
            }
            
            // Character counter for text/textarea with max_length
            if ((field.type === 'text' || field.type === 'textarea') && field.max_length) {
                this.setupCharacterCounter(input, field.max_length);
            }
        });
    }
    
    setupCharacterCounter(input, maxLength) {
        const counterId = `${input.id}-counter`;
        const label = input.closest('.col-md-6, .col-12')?.querySelector('label');
        
        if (label && !document.getElementById(counterId)) {
            const counter = document.createElement('small');
            counter.id = counterId;
            counter.className = 'text-muted ms-2';
            counter.textContent = `(0/${maxLength})`;
            label.appendChild(counter);
            
            input.addEventListener('input', () => {
                const length = input.value.length;
                counter.textContent = `(${length}/${maxLength})`;
                counter.className = length > maxLength * 0.9 ? 'text-warning ms-2' : 'text-muted ms-2';
            });
        }
    }
    
    validateField(input, field) {
        const value = input.value.trim();
        
        // Clear previous state
        input.classList.remove('is-invalid', 'is-valid');
        const errorDiv = document.getElementById(`${input.id}-error`);
        if (errorDiv) errorDiv.textContent = '';
        
        // Required validation
        if (field.required && !value) {
            this.showFieldError(input, `${field.label} is required`);
            return false;
        }
        
        // Type-specific validation
        if (value) {
            if (field.type === 'number') {
                return this.validateNumberField(input, field);
            }
            
            if (field.type === 'select' && value === '') {
                if (field.required) {
                    this.showFieldError(input, `Please select a ${field.label}`);
                    return false;
                }
            }
        }
        
        // Show success
        if (field.required || value) {
            input.classList.add('is-valid');
        }
        
        return true;
    }
    
    validateNumberField(input, field) {
        const value = input.value.trim();
        
        if (!value) {
            if (field.required) {
                this.showFieldError(input, `${field.label} is required`);
                return false;
            }
            return true;
        }
        
        const num = parseFloat(value);
        
        if (isNaN(num)) {
            this.showFieldError(input, 'Please enter a valid number');
            return false;
        }
        
        if (field.min_value !== null && field.min_value !== undefined && num < field.min_value) {
            this.showFieldError(input, `Value must be at least ${field.min_value}`);
            return false;
        }
        
        if (field.max_value !== null && field.max_value !== undefined && num > field.max_value) {
            this.showFieldError(input, `Value must not exceed ${field.max_value}`);
            return false;
        }
        
        input.classList.remove('is-invalid');
        input.classList.add('is-valid');
        const errorDiv = document.getElementById(`${input.id}-error`);
        if (errorDiv) errorDiv.textContent = '';
        
        return true;
    }
    
    validateForm() {
        let isValid = true;
        
        // Validate all dynamic fields
        Object.entries(this.currentFields).forEach(([key, field]) => {
            const input = document.getElementById(`id_dyn_${key}`);
            if (input && !this.validateField(input, field)) {
                isValid = false;
            }
        });
        
        return isValid;
    }
    
    showFieldError(input, message) {
        input.classList.add('is-invalid');
        input.classList.remove('is-valid');
        const errorDiv = document.getElementById(`${input.id}-error`);
        if (errorDiv) {
            errorDiv.textContent = message;
        }
    }
    
    showGlobalError(message) {
        const alertHTML = `
            <div class="alert alert-danger alert-dismissible fade show shadow-sm" role="alert">
                <i class="bi bi-exclamation-triangle-fill me-2"></i>
                <strong>Validation Error:</strong> ${this.escapeHtml(message)}
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            </div>
        `;
        this.dynamicFieldsContainer.insertAdjacentHTML('beforebegin', alertHTML);
        
        // Scroll to first error
        const firstError = document.querySelector('.is-invalid');
        if (firstError) {
            firstError.scrollIntoView({ behavior: 'smooth', block: 'center' });
            firstError.focus();
        }
    }
    
    prefillDynamicFields() {
        const initialDataScript = document.getElementById('asset-initial-dyn');
        if (!initialDataScript) return;
        
        try {
            const data = JSON.parse(initialDataScript.textContent);
            let prefilledCount = 0;
            
            Object.entries(data).forEach(([key, value]) => {
                const input = document.querySelector(`[name="dyn_${key}"]`);
                if (input && value !== null && value !== undefined) {
                    if (input.type === 'date' && typeof value === 'string') {
                        if (/^\d{4}-\d{2}-\d{2}$/.test(value)) {
                            input.value = value;
                            prefilledCount++;
                        }
                    } else {
                        input.value = value;
                        prefilledCount++;
                    }
                }
            });
            
            if (prefilledCount > 0) {
                console.log(`✅ Prefilled ${prefilledCount} dynamic fields for edit form`);
            }
        } catch (error) {
            console.warn('⚠️ Failed to prefill dynamic fields:', error);
        }
    }
    
    addWizardButton() {
        if (!window.wizard) {
            console.log('⚠️ Wizard not available, skipping button');
            return;
        }
        
        const categoryGroup = this.categorySelect?.closest('.col-md-6');
        if (!categoryGroup) return;
        
        // Check if button already exists
        if (document.getElementById('openWizardFromForm')) return;
        
        const btnHTML = `
            <button type="button" 
                    class="btn btn-outline-primary btn-sm mt-2 w-100"
                    id="openWizardFromForm">
                <i class="bi bi-magic me-1"></i>
                Create New Category (Wizard)
            </button>
        `;
        
        categoryGroup.insertAdjacentHTML('beforeend', btnHTML);
        
        document.getElementById('openWizardFromForm')?.addEventListener('click', () => {
            console.log('🧙 Opening category wizard from asset form');
            window.wizard.openWizard();
        });
        
        console.log('✅ Wizard integration button added');
    }
    
    /**
     * Filter users by selected branch (AJAX)
     * @param {string} branchId - Selected branch ID
     */
    async filterUsersByBranch(branchId) {
        if (!branchId) {
            // No branch selected, show placeholder
            this.assignedToSelect.innerHTML = '<option value="">-- Select Branch First --</option>';
            this.assignedToSelect.disabled = true;
            return;
        }
        
        try {
            // Show loading state
            this.assignedToSelect.disabled = true;
            this.assignedToSelect.innerHTML = '<option value="">Loading users...</option>';
            
            // Fetch users for this branch
            const response = await fetch(`/assets/api/users-by-branch/?branch_id=${branchId}`);
            
            if (!response.ok) {
                throw new Error('Failed to fetch users');
            }
            
            const data = await response.json();
            
            // Clear dropdown
            this.assignedToSelect.innerHTML = '<option value="">-- Not Assigned --</option>';
            
            // Populate with users
            if (data.users && data.users.length > 0) {
                data.users.forEach(user => {
                    const option = document.createElement('option');
                    option.value = user.id;
                    option.textContent = user.display;
                    
                    // Add visual indicator for cross-branch users (admins only)
                    if (data.is_admin && !user.is_in_selected_branch) {
                        option.textContent += ' ⚠️ (Different Branch)';
                        option.style.color = '#ff9800';
                        option.style.fontWeight = 'bold';
                    }
                    
                    this.assignedToSelect.appendChild(option);
                });
                
                // Show warning for admins if cross-branch assignments possible
                if (data.is_admin) {
                    this.showCrossBranchWarning();
                }
            } else {
                this.assignedToSelect.innerHTML = '<option value="">No users in this branch</option>';
            }
            
            // Re-enable dropdown
            this.assignedToSelect.disabled = false;
            
            console.log(`✅ Loaded ${data.users.length} users for branch ${branchId}`);
            
        } catch (error) {
            console.error('❌ Failed to filter users by branch:', error);
            this.assignedToSelect.innerHTML = '<option value="">Error loading users</option>';
            this.assignedToSelect.disabled = false;
            
            // Show error message
            this.showError('Failed to load users. Please refresh the page and try again.');
        }
    }
    
    /**
     * Show warning for admins about cross-branch assignments
     */
    showCrossBranchWarning() {
        const existingWarning = document.getElementById('cross-branch-warning');
        if (existingWarning) return; // Already shown
        
        const warningHTML = `
            <div class="alert alert-warning alert-dismissible fade show mt-2" role="alert" id="cross-branch-warning">
                <i class="bi bi-exclamation-triangle-fill me-2"></i>
                <strong>Admin Notice:</strong> You can assign to users in other branches, 
                but this may cause operational confusion. Users marked with ⚠️ are in different branches.
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            </div>
        `;
        
        this.assignedToSelect.parentElement.insertAdjacentHTML('afterend', warningHTML);
    }
    
    setupImagePreview() {
        const imageInput = document.getElementById('id_images');
        const preview = document.getElementById('image-preview');
        
        if (imageInput && preview) {
            imageInput.addEventListener('change', (e) => {
                const file = e.target.files[0];
                if (file) {
                    const reader = new FileReader();
                    reader.onload = (e) => {
                        preview.src = e.target.result;
                        preview.classList.remove('d-none');
                    };
                    reader.readAsDataURL(file);
                }
            });
        }
    }
    
    showLoading() {
        this.dynamicFieldsContainer.innerHTML = `
            <div class="d-flex align-items-center justify-content-center py-5">
                <div class="spinner-border text-primary me-3" role="status">
                    <span class="visually-hidden">Loading...</span>
                </div>
                <div class="text-muted">
                    <div class="fw-bold">Loading category fields...</div>
                    <small>Please wait</small>
                </div>
            </div>
        `;
    }
    
    showError(message) {
        this.dynamicFieldsContainer.innerHTML = `
            <div class="alert alert-danger shadow-sm">
                <i class="bi bi-exclamation-triangle-fill me-2"></i>
                <strong>Error:</strong> ${this.escapeHtml(message)}
            </div>
        `;
    }
    
    escapeHtml(unsafe) {
        if (unsafe === null || unsafe === undefined) return '';
        const div = document.createElement('div');
        div.textContent = String(unsafe);
        return div.innerHTML;
    }
}

// Initialize on DOM ready
document.addEventListener('DOMContentLoaded', () => {
    console.log('🚀 Initializing Enhanced Asset Registration Form');
    window.assetRegistrationForm = new AssetRegistrationForm();
});
