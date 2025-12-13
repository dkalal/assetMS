/**
 * Category Creation Wizard - World-Class Implementation
 * Multi-step wizard with template support for enterprise asset management
 * 
 * Features:
 * - Multi-step guided workflow
 * - Template-based quick start
 * - Custom field configuration
 * - Real-time validation
 * - State management
 * - Responsive design
 */

class CategoryWizard {
    constructor() {
        this.currentStep = 1;
        this.wizardPath = null; // 'template' or 'custom'
        this.selectedTemplate = null;
        this.categoryName = '';
        this.fields = [];
        this.templates = [];
        this.fieldIdCounter = 0;
        
        console.log('🧙 Category Wizard initialized');
    }
    
    // ==================== Wizard Control ====================
    
    openWizard() {
        console.log('🧙 Opening Category Wizard');
        this.reset();
        const modal = document.getElementById('categoryWizardModal');
        if (modal) {
            modal.classList.add('active');
            this.goToStep(1);
        }
    }
    
    closeWizard() {
        console.log('🔽 Closing Category Wizard');
        const modal = document.getElementById('categoryWizardModal');
        if (modal) {
            modal.classList.remove('active');
        }
        this.reset();
    }
    
    reset() {
        this.currentStep = 1;
        this.wizardPath = null;
        this.selectedTemplate = null;
        this.categoryName = '';
        this.fields = [];
        this.fieldIdCounter = 0;
        
        // Reset UI (safely check if elements exist)
        const nameInput = document.getElementById('wizard-category-name');
        if (nameInput) nameInput.value = '';
        
        const feedback = document.getElementById('wizard-feedback');
        if (feedback) feedback.innerHTML = '';
        
        console.log('🔄 Wizard reset complete');
    }
    
    // ==================== Step Navigation ====================
    
    goToStep(step) {
        console.log(`📍 Going to step ${step}`);
        console.log(`   Current categoryName: "${this.categoryName}"`);
        console.log(`   Current wizardPath: ${this.wizardPath}`);
        this.currentStep = step;
        
        // Hide all content sections
        document.querySelectorAll('.wizard-content').forEach(content => {
            content.style.display = 'none';
        });
        
        // Show current step content
        let stepKey = step;
        if (step === 2) {
            stepKey = this.wizardPath === 'template' ? '2a' : '2b';
        }
        
        const currentContent = document.querySelector(`.wizard-content[data-step="${stepKey}"]`);
        if (currentContent) {
            currentContent.style.display = 'block';
        }
        
        // Update progress indicator
        this.updateProgressIndicator();
        
        // Update buttons
        this.updateButtons();
        
        // Load data if needed
        if (step === 2 && this.wizardPath === 'template' && this.templates.length === 0) {
            this.loadTemplates();
        }
        
        if (step === 3) {
            this.renderFieldsList();
        }
        
        if (step === 4) {
            this.renderReview();
        }
    }
    
    wizardNextStep() {
        if (!this.validateCurrentStep()) {
            return;
        }
        
        // Special handling for step transitions
        if (this.currentStep === 1) {
            if (!this.wizardPath) {
                this.showFeedback('Please select a creation method', 'warning');
                return;
            }
            this.goToStep(2);
        } else if (this.currentStep === 2) {
            // Save category name (only for custom path - template already has it)
            if (this.wizardPath === 'custom') {
                const nameInput = document.getElementById('wizard-category-name');
                if (nameInput) {
                    this.categoryName = nameInput.value.trim();
                    console.log('✅ Category name captured from custom input:', this.categoryName);
                } else {
                    console.error('❌ Category name input not found!');
                }
            }
            
            // Validate category name exists
            if (!this.categoryName) {
                this.showFeedback('Please enter a category name', 'warning');
                return;
            }
            
            console.log('📝 Moving to step 3 with category name:', this.categoryName);
            this.goToStep(3);
        } else if (this.currentStep === 3) {
            this.goToStep(4);
        }
    }
    
    wizardPrevStep() {
        if (this.currentStep > 1) {
            if (this.currentStep === 3) {
                this.goToStep(2);
            } else if (this.currentStep === 2) {
                this.goToStep(1);
            } else {
                this.goToStep(this.currentStep - 1);
            }
        }
    }
    
    updateProgressIndicator() {
        document.querySelectorAll('.wizard-step').forEach(step => {
            const stepNum = parseInt(step.dataset.step);
            step.classList.remove('active', 'completed');
            
            if (stepNum < this.currentStep) {
                step.classList.add('completed');
            } else if (stepNum === this.currentStep) {
                step.classList.add('active');
            }
        });
    }
    
    updateButtons() {
        const backBtn = document.getElementById('wizard-back-btn');
        const nextBtn = document.getElementById('wizard-next-btn');
        const finishBtn = document.getElementById('wizard-finish-btn');
        
        // Show/hide back button
        if (backBtn) {
            backBtn.style.display = this.currentStep > 1 ? 'block' : 'none';
        }
        
        // Show/hide next vs finish button
        if (this.currentStep === 4) {
            if (nextBtn) nextBtn.style.display = 'none';
            if (finishBtn) finishBtn.style.display = 'block';
        } else {
            if (nextBtn) nextBtn.style.display = 'block';
            if (finishBtn) finishBtn.style.display = 'none';
        }
    }
    
    // ==================== Step 1: Path Selection ====================
    
    selectWizardPath(path) {
        console.log(`🛤️ Selected path: ${path}`);
        this.wizardPath = path;
        
        // Visual feedback
        document.querySelectorAll('.wizard-path-card').forEach(card => {
            card.style.borderColor = '#e9ecef';
        });
        event.currentTarget.style.borderColor = '#0d6efd';
        
        // Auto-advance after selection
        setTimeout(() => {
            this.wizardNextStep();
        }, 300);
    }
    
    // ==================== Step 2a: Template Selection ====================
    
    async loadTemplates() {
        console.log('📋 Loading templates...');
        const container = document.getElementById('template-grid');
        
        try {
            const response = await fetch('/api/category-templates/');
            const data = await response.json();
            
            if (data.success) {
                this.templates = data.templates;
                this.renderTemplates();
            } else {
                this.showFeedback('Failed to load templates', 'danger');
            }
        } catch (error) {
            console.error('❌ Error loading templates:', error);
            this.showFeedback('Network error loading templates', 'danger');
        }
    }
    
    renderTemplates() {
        const container = document.getElementById('template-grid');
        if (!container) return;
        
        const html = this.templates.map(template => `
            <div class="col-md-4">
                <div class="template-card ${this.selectedTemplate?.key === template.key ? 'selected' : ''}" 
                     onclick="wizard.selectTemplate('${template.key}')">
                    <div class="template-icon" style="background: ${template.color}20; color: ${template.color};">
                        <i class="${template.icon}"></i>
                    </div>
                    <h6 class="fw-bold mb-2">${this.escapeHtml(template.name)}</h6>
                    <p class="text-muted small mb-2">${this.escapeHtml(template.description)}</p>
                    <div class="badge bg-secondary">${template.field_count} fields</div>
                </div>
            </div>
        `).join('');
        
        container.innerHTML = html;
    }
    
    async selectTemplate(templateKey) {
        console.log(`📋 Selected template: ${templateKey}`);
        
        try {
            const response = await fetch(`/api/category-template/${templateKey}/`);
            const data = await response.json();
            
            if (data.success) {
                this.selectedTemplate = data.template;
                this.selectedTemplate.key = templateKey;
                
                // Set category name from template (CRITICAL: This persists)
                this.categoryName = data.template.name;
                console.log('✅ Category name set from template:', this.categoryName);
                console.log('✅ Template object:', this.selectedTemplate);
                console.log('✅ this.categoryName after assignment:', this.categoryName);
                console.log('✅ typeof this.categoryName:', typeof this.categoryName);
                
                // Load fields from template
                this.fields = data.template.fields.map((field, index) => ({
                    id: this.fieldIdCounter++,
                    ...field
                }));
                
                console.log('✅ Loaded', this.fields.length, 'fields from template');
                console.log('✅ Category name still set:', this.categoryName);
                
                // Update UI
                this.renderTemplates();
                
                // Show template preview
                document.getElementById('selected-template-name').textContent = data.template.name;
                document.getElementById('selected-template-desc').textContent = data.template.description;
                document.getElementById('template-preview').style.display = 'block';
                
                // Auto-advance
                setTimeout(() => {
                    this.wizardNextStep();
                }, 500);
            }
        } catch (error) {
            console.error('❌ Error loading template:', error);
            this.showFeedback('Failed to load template details', 'danger');
        }
    }
    
    // ==================== Step 3: Field Configuration ====================
    
    renderFieldsList() {
        const container = document.getElementById('wizard-fields-list');
        if (!container) return;
        
        if (this.fields.length === 0) {
            container.innerHTML = `
                <div class="text-center py-4 text-muted">
                    <i class="bi bi-inbox fs-1 d-block mb-2"></i>
                    <p>No fields added yet. Click "Add Field" to get started.</p>
                </div>
            `;
            return;
        }
        
        const html = this.fields.map((field, index) => `
            <div class="wizard-field-item" data-field-id="${field.id}">
                <div class="d-flex align-items-center">
                    <div class="field-drag-handle me-3">
                        <i class="bi bi-grip-vertical"></i>
                    </div>
                    <div class="flex-grow-1">
                        <div class="fw-semibold">${this.escapeHtml(field.label)}</div>
                        <small class="text-muted">
                            ${field.key} • ${field.type}
                            ${field.required ? '<span class="badge bg-danger ms-1">Required</span>' : ''}
                        </small>
                    </div>
                    <div class="d-flex gap-2">
                        <button type="button" class="btn btn-sm btn-outline-primary" 
                                onclick="wizard.editField(${field.id})">
                            <i class="bi bi-pencil"></i>
                        </button>
                        <button type="button" class="btn btn-sm btn-outline-danger" 
                                onclick="wizard.deleteField(${field.id})">
                            <i class="bi bi-trash"></i>
                        </button>
                    </div>
                </div>
            </div>
        `).join('');
        
        container.innerHTML = html;
    }
    
    addWizardField() {
        const field = {
            id: this.fieldIdCounter++,
            label: '',
            key: '',
            type: 'text',
            required: false,
            placeholder: '',
            help_text: ''
        };
        
        this.fields.push(field);
        this.renderFieldsList();
        this.editField(field.id);
    }
    
    editField(fieldId) {
        const field = this.fields.find(f => f.id === fieldId);
        if (!field) return;
        
        // Create inline edit form
        const fieldItem = document.querySelector(`[data-field-id="${fieldId}"]`);
        if (!fieldItem) return;
        
        fieldItem.classList.add('editing');
        fieldItem.innerHTML = `
            <div class="row g-3">
                <div class="col-md-6">
                    <label class="form-label small fw-semibold">Field Label *</label>
                    <input type="text" class="form-control form-control-sm" 
                           value="${this.escapeHtml(field.label)}" 
                           id="edit-label-${fieldId}" 
                           placeholder="e.g., Serial Number"
                           oninput="wizard.autoGenerateKey(${fieldId})">
                    <div class="form-text" style="font-size: 0.75rem;">
                        <i class="bi bi-info-circle me-1"></i>Key will be auto-generated
                    </div>
                </div>
                <div class="col-md-6">
                    <label class="form-label small fw-semibold">Type</label>
                    <select class="form-select form-select-sm" id="edit-type-${fieldId}">
                        <option value="text" ${field.type === 'text' ? 'selected' : ''}>Text</option>
                        <option value="number" ${field.type === 'number' ? 'selected' : ''}>Number</option>
                        <option value="date" ${field.type === 'date' ? 'selected' : ''}>Date</option>
                        <option value="textarea" ${field.type === 'textarea' ? 'selected' : ''}>Textarea</option>
                        <option value="select" ${field.type === 'select' ? 'selected' : ''}>Select</option>
                        <option value="checkbox" ${field.type === 'checkbox' ? 'selected' : ''}>Checkbox</option>
                    </select>
                </div>
                <div class="col-md-12">
                    <label class="form-label small fw-semibold d-flex align-items-center">
                        <input type="checkbox" class="form-check-input me-2" 
                               id="edit-required-${fieldId}" 
                               ${field.required ? 'checked' : ''}>
                        Required Field
                    </label>
                </div>
                <div class="col-12">
                    <div class="d-flex justify-content-end gap-2">
                        <button type="button" class="btn btn-sm btn-secondary" 
                                onclick="wizard.cancelEditField(${fieldId})">
                            Cancel
                        </button>
                        <button type="button" class="btn btn-sm btn-primary" 
                                onclick="wizard.saveField(${fieldId})">
                            <i class="bi bi-check-lg me-1"></i>Save
                        </button>
                    </div>
                </div>
            </div>
        `;
    }
    
    saveField(fieldId) {
        const field = this.fields.find(f => f.id === fieldId);
        if (!field) return;
        
        // Get values from form
        field.label = document.getElementById(`edit-label-${fieldId}`).value.trim();
        field.type = document.getElementById(`edit-type-${fieldId}`).value;
        field.required = document.getElementById(`edit-required-${fieldId}`).checked;
        
        // Validate label
        if (!field.label) {
            this.showFeedback('Field label is required', 'warning');
            return;
        }
        
        // Auto-generate key and placeholder from label
        field.key = this.generateKeyFromLabel(field.label);
        field.placeholder = `Enter ${field.label.toLowerCase()}`;
        
        this.renderFieldsList();
    }
    
    autoGenerateKey(fieldId) {
        // This function is kept for compatibility but no longer shows key visually
        // Key is generated when saving the field
    }
    
    generateKeyFromLabel(label) {
        if (!label) return '';
        
        // Convert to lowercase, replace spaces and special chars with underscore
        return label
            .toLowerCase()
            .trim()
            .replace(/[^a-z0-9]+/g, '_')  // Replace non-alphanumeric with underscore
            .replace(/^_+|_+$/g, '')       // Remove leading/trailing underscores
            .replace(/_+/g, '_')           // Replace multiple underscores with single
            .substring(0, 50);             // Limit length
    }
    
    cancelEditField(fieldId) {
        const field = this.fields.find(f => f.id === fieldId);
        if (!field) return;
        
        // If field is empty (no label), remove it
        if (!field.label) {
            this.deleteField(fieldId);
        } else {
            this.renderFieldsList();
        }
    }
    
    deleteField(fieldId) {
        if (confirm('Are you sure you want to delete this field?')) {
            this.fields = this.fields.filter(f => f.id !== fieldId);
            this.renderFieldsList();
        }
    }
    
    // ==================== Step 4: Review ====================
    
    renderReview() {
        console.log('📋 Rendering review...');
        console.log('   Category name for review:', this.categoryName);
        console.log('   Fields count for review:', this.fields.length);
        console.log('   Wizard path:', this.wizardPath);
        
        // Category name
        document.getElementById('review-category-name').textContent = this.categoryName;
        
        // Field count
        document.getElementById('review-field-count').textContent = this.fields.length;
        
        // Fields list
        const container = document.getElementById('review-fields-list');
        if (!container) return;
        
        if (this.fields.length === 0) {
            container.innerHTML = '<p class="text-muted mb-0">No fields configured</p>';
            return;
        }
        
        const html = this.fields.map(field => `
            <div class="review-field-item">
                <div class="d-flex justify-content-between align-items-start">
                    <div>
                        <div class="fw-semibold">${this.escapeHtml(field.label)}</div>
                        <small class="text-muted">${field.key}</small>
                    </div>
                    <div class="text-end">
                        <span class="field-type-badge badge bg-secondary">${field.type}</span>
                        ${field.required ? '<span class="badge bg-danger ms-1">Required</span>' : ''}
                    </div>
                </div>
            </div>
        `).join('');
        
        container.innerHTML = html;
    }
    
    // ==================== Validation ====================
    
    validateCurrentStep() {
        if (this.currentStep === 1) {
            if (!this.wizardPath) {
                this.showFeedback('Please select a creation method', 'warning');
                return false;
            }
        }
        
        if (this.currentStep === 2 && this.wizardPath === 'custom') {
            const nameInput = document.getElementById('wizard-category-name');
            if (!nameInput) {
                console.error('❌ Category name input not found in DOM!');
                this.showFeedback('System error: Input field not found', 'danger');
                return false;
            }
            
            const name = nameInput.value.trim();
            if (!name) {
                this.showFeedback('Category name is required', 'warning');
                nameInput.focus();
                return false;
            }
            
            console.log('✅ Validated category name:', name);
        }
        
        if (this.currentStep === 2 && this.wizardPath === 'template') {
            if (!this.selectedTemplate) {
                this.showFeedback('Please select a template', 'warning');
                return false;
            }
            
            if (!this.categoryName) {
                console.error('❌ Template selected but category name not set!');
                this.showFeedback('System error: Template name not loaded', 'danger');
                return false;
            }
            
            console.log('✅ Validated template with category name:', this.categoryName);
        }
        
        return true;
    }
    
    // ==================== Finish & Submit ====================
    
    async wizardFinish() {
        console.log('🎉 Finishing wizard...');
        console.log('🔍 Wizard path:', this.wizardPath);
        console.log('📝 Category name (before check):', this.categoryName);
        console.log('📊 Fields count:', this.fields.length);
        
        // For custom path, try to capture name one more time
        if (this.wizardPath === 'custom') {
            const nameInput = document.getElementById('wizard-category-name');
            if (nameInput) {
                const inputValue = nameInput.value.trim();
                if (inputValue) {
                    this.categoryName = inputValue;
                    console.log('✅ Re-captured category name from input:', this.categoryName);
                }
            }
        }
        
        // Final validation
        if (!this.categoryName || this.categoryName.trim() === '') {
            console.error('❌ CRITICAL: Category name is empty!');
            console.error('   - Wizard path:', this.wizardPath);
            console.error('   - Selected template:', this.selectedTemplate);
            this.showFeedback('Category name is required. Please go back and enter a name.', 'danger');
            this.goToStep(this.wizardPath === 'template' ? 2 : 2);
            return;
        }
        
        console.log('✅ Final category name:', this.categoryName);
        
        // Show loading
        const finishBtn = document.getElementById('wizard-finish-btn');
        const originalText = finishBtn.innerHTML;
        finishBtn.disabled = true;
        finishBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Creating...';
        
        try {
            // Step 1: Create category
            const requestPayload = {
                name: this.categoryName.trim()
            };
            
            console.log('📤 Sending to API:', requestPayload);
            console.log('📤 Category name being sent:', requestPayload.name);
            console.log('📤 Category name length:', requestPayload.name.length);
            console.log('📤 Is empty?', requestPayload.name === '');
            
            const categoryResponse = await fetch('/api/create-category/', {
                method: 'POST',
                headers: {
                    'X-CSRFToken': this.getCSRFToken(),
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(requestPayload)
            });
            
            console.log('📡 Category creation response status:', categoryResponse.status);
            
            const categoryData = await categoryResponse.json();
            
            if (!categoryData.success) {
                throw new Error(categoryData.error || 'Failed to create category');
            }
            
            const categoryId = categoryData.category_id;
            
            // Step 2: Create fields (ENHANCED with error handling)
            if (this.fields.length > 0) {
                console.log(`📋 Creating ${this.fields.length} fields...`);
                let fieldSuccessCount = 0;
                let fieldFailCount = 0;
                
                for (const field of this.fields) {
                    try {
                        console.log(`📤 Creating field: ${field.label} (${field.key}) - Type: ${field.type}`);
                        
                        const fieldResponse = await fetch(`/api/category/${categoryId}/fields/create/`, {
                            method: 'POST',
                            headers: {
                                'X-CSRFToken': this.getCSRFToken(),
                                'Content-Type': 'application/json',
                            },
                            body: JSON.stringify({
                                label: field.label,
                                key: field.key,
                                type: field.type,
                                required: field.required,
                                placeholder: field.placeholder || '',
                                help_text: field.help_text || ''
                            })
                        });
                        
                        const fieldData = await fieldResponse.json();
                        
                        if (fieldData.success) {
                            fieldSuccessCount++;
                            console.log(`✅ Field created: ${field.label}`);
                        } else {
                            fieldFailCount++;
                            console.error(`❌ Field creation failed: ${field.label}`, fieldData.error);
                        }
                    } catch (error) {
                        fieldFailCount++;
                        console.error(`❌ Error creating field ${field.label}:`, error);
                    }
                }
                
                console.log(`📊 Field creation summary: ${fieldSuccessCount} succeeded, ${fieldFailCount} failed`);
            } else {
                console.log('ℹ️ No fields to create for this category');
            }
            
            // Success!
            this.showFeedback(`Category "${this.categoryName}" created successfully with ${this.fields.length} field(s)!`, 'success');
            
            // Close wizard and refresh
            setTimeout(() => {
                this.closeWizard();
                if (window.adminTools) {
                    adminTools.loadCategoriesWithAnalytics();
                }
            }, 1500);
            
        } catch (error) {
            console.error('❌ Error creating category:', error);
            this.showFeedback(error.message || 'Failed to create category', 'danger');
            finishBtn.disabled = false;
            finishBtn.innerHTML = originalText;
        }
    }
    
    // ==================== Utilities ====================
    
    showFeedback(message, type = 'info') {
        const container = document.getElementById('wizard-feedback');
        if (!container) return;
        
        container.innerHTML = `
            <div class="alert alert-${type} alert-dismissible fade show" role="alert">
                ${message}
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            </div>
        `;
        
        // Auto-dismiss after 5 seconds
        setTimeout(() => {
            container.innerHTML = '';
        }, 5000);
    }
    
    getCSRFToken() {
        return document.querySelector('[name=csrfmiddlewaretoken]')?.value || 
               document.cookie.split('; ').find(row => row.startsWith('csrftoken='))?.split('=')[1] || '';
    }
    
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// Initialize wizard and expose globally
window.wizard = new CategoryWizard();

console.log('✅ Category Wizard loaded successfully');
