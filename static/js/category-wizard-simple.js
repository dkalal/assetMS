/**
 * Category Creation Wizard - Simplified World-Class Implementation
 * 3-step wizard: Basic Info → Dynamic Fields → Review
 * 
 * Features:
 * - Clean 3-step workflow
 * - Real-time validation
 * - Dynamic field management
 * - Professional UX
 */

class CategoryWizard {
  constructor() {
    this.currentStep = 1;
    this.totalSteps = 3;
    this.categoryData = {
      name: '',
      description: '',
      fields: []
    };
    this.existingCategories = [];
    this.isSubmitting = false;
    this.editingFieldIndex = null;
    
    console.log('✅ Category Wizard initialized');
  }

  // ==================== Wizard Control ====================
  
  openWizard() {
    console.log('🧙 Opening wizard');
    this.reset();
    const modal = document.getElementById('categoryWizardModal');
    if (modal) {
      modal.classList.add('active');
      document.getElementById('wizard-category-name')?.focus();
    }
  }

  closeWizard() {
    if (this.isSubmitting) return;
    
    const modal = document.getElementById('categoryWizardModal');
    if (modal) {
      modal.classList.remove('active');
    }
    this.reset();
  }

  reset() {
    this.currentStep = 1;
    this.categoryData = { name: '', description: '', fields: [] };
    this.editingFieldIndex = null;
    this.isSubmitting = false;
    
    // Reset form
    const nameInput = document.getElementById('wizard-category-name');
    const descInput = document.getElementById('wizard-category-description');
    if (nameInput) nameInput.value = '';
    if (descInput) descInput.value = '';
    
    // Clear feedback
    const feedback = document.getElementById('wizard-feedback');
    if (feedback) feedback.innerHTML = '';
    
    // Reset validation
    this.clearValidation('wizard-name');
    
    // Reset counters
    this.updateCharCounter(nameInput, 'wizard-name-counter');
    this.updateCharCounter(descInput, 'wizard-desc-counter');
    
    this.goToStep(1);
  }

  // ==================== Step Navigation ====================
  
  nextStep() {
    if (!this.validateCurrentStep()) {
      return;
    }
    
    // Save current step data
    if (this.currentStep === 1) {
      this.categoryData.name = document.getElementById('wizard-category-name').value.trim();
      this.categoryData.description = document.getElementById('wizard-category-description').value.trim();
    }
    
    if (this.currentStep < this.totalSteps) {
      this.goToStep(this.currentStep + 1);
    }
  }

  prevStep() {
    if (this.currentStep > 1) {
      this.goToStep(this.currentStep - 1);
    }
  }

  goToStep(step) {
    this.currentStep = step;
    
    // Hide all steps
    document.querySelectorAll('.wizard-content').forEach(content => {
      content.classList.remove('active');
      content.style.display = 'none';
    });
    
    // Show current step
    const currentContent = document.querySelector(`.wizard-content[data-step="${step}"]`);
    if (currentContent) {
      currentContent.classList.add('active');
      currentContent.style.display = 'block';
    }
    
    // Update progress
    this.updateProgress();
    
    // Update buttons
    this.updateButtons();
    
    // Load step-specific data
    if (step === 2) {
      this.renderFieldsList();
    } else if (step === 3) {
      this.renderReview();
    }
  }

  updateProgress() {
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
    
    if (backBtn) backBtn.style.display = this.currentStep > 1 ? 'block' : 'none';
    
    if (this.currentStep === this.totalSteps) {
      if (nextBtn) nextBtn.style.display = 'none';
      if (finishBtn) finishBtn.style.display = 'block';
    } else {
      if (nextBtn) nextBtn.style.display = 'block';
      if (finishBtn) finishBtn.style.display = 'none';
    }
  }

  // ==================== Validation ====================
  
  validateCurrentStep() {
    if (this.currentStep === 1) {
      return this.validateStep1();
    }
    return true; // Steps 2 and 3 don't require validation to proceed
  }

  validateStep1() {
    const nameInput = document.getElementById('wizard-category-name');
    const name = nameInput.value.trim();
    
    if (!name) {
      this.showValidationError('wizard-name', 'Category name is required');
      nameInput.focus();
      return false;
    }
    
    if (name.length < 2) {
      this.showValidationError('wizard-name', 'Name must be at least 2 characters');
      nameInput.focus();
      return false;
    }
    
    // Check duplicates
    if (this.existingCategories.some(cat => cat.name.toLowerCase() === name.toLowerCase())) {
      this.showValidationError('wizard-name', 'A category with this name already exists');
      nameInput.focus();
      return false;
    }
    
    this.clearValidation('wizard-name');
    return true;
  }

  validateName(input) {
    const value = input.value.trim();
    const counter = document.getElementById('wizard-name-counter');
    const validation = document.getElementById('wizard-name-validation');
    
    // Update counter
    counter.textContent = `${value.length}/100`;
    counter.className = value.length > 90 ? 'text-warning fw-bold' : 'text-muted';
    
    // Clear previous validation
    validation.innerHTML = '';
    input.classList.remove('is-invalid', 'is-valid');
    
    if (value.length === 0) return;
    
    if (value.length < 2) {
      validation.innerHTML = '<i class="bi bi-exclamation-circle me-1"></i>Name must be at least 2 characters';
      input.classList.add('is-invalid');
      return;
    }
    
    // Check duplicates
    const isDuplicate = this.existingCategories.some(cat => 
      cat.name.toLowerCase() === value.toLowerCase()
    );
    
    if (isDuplicate) {
      validation.innerHTML = '<i class="bi bi-exclamation-triangle me-1"></i>A category with this name already exists';
      input.classList.add('is-invalid');
      return;
    }
    
    // Valid
    input.classList.add('is-valid');
    validation.innerHTML = '<i class="bi bi-check-circle me-1 text-success"></i>Name is available';
    validation.className = 'text-success small';
  }

  showValidationError(prefix, message) {
    const validation = document.getElementById(`${prefix}-validation`);
    const input = document.getElementById(`${prefix}-category-name`);
    
    if (validation) {
      validation.innerHTML = `<i class="bi bi-exclamation-circle me-1"></i>${message}`;
      validation.className = 'invalid-feedback d-block';
    }
    
    if (input) {
      input.classList.add('is-invalid');
    }
  }

  clearValidation(prefix) {
    const validation = document.getElementById(`${prefix}-validation`);
    const input = document.getElementById(`${prefix}-category-name`);
    
    if (validation) validation.innerHTML = '';
    if (input) input.classList.remove('is-invalid', 'is-valid');
  }

  updateCharCounter(textarea, counterId) {
    if (!textarea) return;
    const counter = document.getElementById(counterId);
    if (!counter) return;
    
    const length = textarea.value.length;
    const max = textarea.maxLength;
    counter.textContent = `${length}/${max}`;
    counter.className = length > max * 0.9 ? 'text-warning fw-bold' : 'text-muted';
  }

  // ==================== Field Management ====================
  
  showFieldForm() {
    const form = document.getElementById('wizard-field-form');
    if (form) {
      form.style.display = 'block';
      this.editingFieldIndex = null;

      // Reset form
      document.getElementById('field-label').value = '';
      const preview = document.getElementById('field-key-preview');
      if (preview) preview.textContent = 'auto_generated_key';
      document.getElementById('field-type').value = 'text';
      document.getElementById('field-required').checked = false;
      document.getElementById('field-form-title').textContent = 'Add New Field';

      // Clear validation
      const validation = document.getElementById('field-key-validation');
      if (validation) {
        validation.innerHTML = '';
        validation.className = 'invalid-feedback d-block';
      }

      document.getElementById('field-label')?.focus();
    }
  }

  hideFieldForm() {
    const form = document.getElementById('wizard-field-form');
    if (form) {
      form.style.display = 'none';
      this.editingFieldIndex = null;
    }
  }

  saveField() {
    const label = document.getElementById('field-label').value.trim();
    const type = document.getElementById('field-type').value;
    const required = document.getElementById('field-required').checked;

    // Validate
    if (!label) {
      this.showFeedback('Field label is required', 'warning');
      return;
    }
    
    // Auto-generate key from label
    const key = this.generateKeyFromLabel(label);

    // Check for duplicate keys
    if (this.editingFieldIndex === null) {
      const isDuplicate = this.categoryData.fields.some(f => f.key === key);
      if (isDuplicate) {
        const validation = document.getElementById('field-key-validation');
        if (validation) {
          validation.innerHTML = '<i class="bi bi-exclamation-triangle me-1"></i>A field with this key already exists';
          validation.className = 'invalid-feedback d-block';
        }
        return;
      }
    }
    
    const field = { key, label, type, required };
    
    if (this.editingFieldIndex !== null) {
      // Update existing field
      this.categoryData.fields[this.editingFieldIndex] = field;
    } else {
      // Add new field
      this.categoryData.fields.push(field);
    }
    
    this.hideFieldForm();
    this.renderFieldsList();
    this.showFeedback(`Field "${label}" ${this.editingFieldIndex !== null ? 'updated' : 'added'}`, 'success');
  }

  editFieldAtIndex(index) {
    const field = this.categoryData.fields[index];
    if (!field) return;

    this.editingFieldIndex = index;

    // Populate form
    document.getElementById('field-label').value = field.label;
    const preview = document.getElementById('field-key-preview');
    if (preview) preview.textContent = field.key;
    document.getElementById('field-type').value = field.type;
    document.getElementById('field-required').checked = field.required;
    document.getElementById('field-form-title').textContent = 'Edit Field';

    // Show form
    const form = document.getElementById('wizard-field-form');
    if (form) form.style.display = 'block';
    
    document.getElementById('field-label')?.focus();
  }

  deleteFieldAtIndex(index) {
    const field = this.categoryData.fields[index];
    if (!field) return;
    
    if (confirm(`Delete field "${field.label}"?`)) {
      this.categoryData.fields.splice(index, 1);
      this.renderFieldsList();
      this.showFeedback(`Field "${field.label}" deleted`, 'info');
    }
  }

  generateKeyFromLabel(label) {
    return label
      .toLowerCase()
      .trim()
      .replace(/[^a-z0-9]+/g, '_')
      .replace(/^_+|_+$/g, '')
      .replace(/_+/g, '_')
      .substring(0, 50);
  }

  handleFieldLabelInput(input) {
    const value = input.value.trim();
    const preview = document.getElementById('field-key-preview');
    const validation = document.getElementById('field-key-validation');

    if (preview) {
      preview.textContent = value ? this.generateKeyFromLabel(value) || 'invalid_key' : 'auto_generated_key';
    }

    if (!validation) return;

    validation.innerHTML = '';
    validation.className = 'invalid-feedback d-block';

    if (!value) {
      return;
    }

    const key = this.generateKeyFromLabel(value);
    const keyPattern = /^[a-z][a-z0-9_]*$/;

    if (!key || !keyPattern.test(key)) {
      validation.innerHTML = '<i class="bi bi-exclamation-circle me-1"></i>Label must produce a valid key (lowercase letters, numbers, underscores)';
      validation.classList.add('text-danger');
      return;
    }

    const isDuplicate = this.categoryData.fields.some((f, idx) => 
      f.key === key && idx !== this.editingFieldIndex
    );

    if (isDuplicate) {
      validation.innerHTML = '<i class="bi bi-exclamation-triangle me-1"></i>A field with this key already exists';
      validation.classList.add('text-danger');
      return;
    }

    validation.innerHTML = '<i class="bi bi-check-circle me-1 text-success"></i>Key looks great';
    validation.className = 'text-success small';
  }

  renderFieldsList() {
    const container = document.getElementById('wizard-fields-list');
    if (!container) return;
    
    if (this.categoryData.fields.length === 0) {
      container.innerHTML = `
        <div class="alert alert-info">
          <i class="bi bi-info-circle me-2"></i>
          No fields added yet. Click "Add Field" to create custom fields for this category.
        </div>
      `;
      return;
    }
    
    const html = this.categoryData.fields.map((field, index) => `
      <div class="field-list-item">
        <div class="field-info">
          <div class="field-label">${this.escapeHtml(field.label)}</div>
          <div class="field-meta">
            <span class="field-key">${field.key}</span>
            <span class="badge bg-secondary ms-2">${field.type}</span>
            ${field.required ? '<span class="badge bg-danger ms-1">Required</span>' : ''}
          </div>
        </div>
        <div class="field-actions">
          <button type="button" class="btn btn-sm btn-outline-primary" onclick="categoryWizard.editFieldAtIndex(${index})">
            <i class="bi bi-pencil"></i>
          </button>
          <button type="button" class="btn btn-sm btn-outline-danger" onclick="categoryWizard.deleteFieldAtIndex(${index})">
            <i class="bi bi-trash"></i>
          </button>
        </div>
      </div>
    `).join('');
    
    container.innerHTML = html;
  }

  // ==================== Review ====================
  
  renderReview() {
    // Category name
    document.getElementById('review-category-name').textContent = this.categoryData.name;
    
    // Description
    const descEl = document.getElementById('review-category-description');
    if (descEl) {
      descEl.textContent = this.categoryData.description || 'None';
    }
    
    // Field count
    document.getElementById('review-field-count').textContent = this.categoryData.fields.length;
    
    // Fields list
    const container = document.getElementById('review-fields-list');
    if (!container) return;
    
    if (this.categoryData.fields.length === 0) {
      container.innerHTML = '<p class="text-muted small mb-0">No custom fields configured</p>';
      return;
    }
    
    const html = this.categoryData.fields.map(field => `
      <div class="d-flex justify-content-between align-items-center py-2 border-bottom">
        <div>
          <div class="fw-semibold">${this.escapeHtml(field.label)}</div>
          <small class="text-muted">${field.key}</small>
        </div>
        <div>
          <span class="badge bg-secondary">${field.type}</span>
          ${field.required ? '<span class="badge bg-danger ms-1">Required</span>' : ''}
        </div>
      </div>
    `).join('');
    
    container.innerHTML = html;
  }

  // ==================== Submit ====================
  
  async finish() {
    if (this.isSubmitting) return;
    
    this.isSubmitting = true;
    const finishBtn = document.getElementById('wizard-finish-btn');
    const originalText = finishBtn.innerHTML;
    finishBtn.disabled = true;
    finishBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Creating...';
    
    try {
      // Create category
      const response = await fetch('/api/category/create/', {
        method: 'POST',
        headers: {
          'X-CSRFToken': this.getCSRFToken(),
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          name: this.categoryData.name,
          description: this.categoryData.description
        })
      });
      
      const data = await response.json();
      
      if (!data.success) {
        throw new Error(data.error || 'Failed to create category');
      }
      
      const categoryId = data.category?.id || data.category_id;
      
      // Create fields if any
      if (this.categoryData.fields.length > 0 && categoryId) {
        for (const field of this.categoryData.fields) {
          const fieldResponse = await fetch(`/api/category/${categoryId}/fields/create/`, {
            method: 'POST',
            headers: {
              'X-CSRFToken': this.getCSRFToken(),
              'Content-Type': 'application/json'
            },
            body: JSON.stringify(field)
          });
          
          const fieldData = await fieldResponse.json();
          if (!fieldData.success) {
            console.error(`Failed to create field "${field.label}":`, fieldData.error);
            // Continue with other fields even if one fails
          }
        }
      }
      
      // Success - Reset state immediately
      this.isSubmitting = false;
      finishBtn.disabled = false;
      finishBtn.innerHTML = '<i class="bi bi-check-circle me-2"></i>Created!';
      
      this.showFeedback(`Category "${this.categoryData.name}" created successfully!`, 'success');
      
      setTimeout(() => {
        this.closeWizard();
        // Reload categories list
        if (typeof loadCategories === 'function') {
          loadCategories();
        }
      }, 1500);
      
    } catch (error) {
      console.error('Error creating category:', error);
      this.showFeedback(error.message || 'Failed to create category', 'danger');
      finishBtn.disabled = false;
      finishBtn.innerHTML = originalText;
      this.isSubmitting = false;
    }
  }

  // ==================== Utilities ====================
  
  showFeedback(message, type = 'info') {
    const container = document.getElementById('wizard-feedback');
    if (!container) return;
    
    container.innerHTML = `
      <div class="alert alert-${type} alert-dismissible fade show">
        <i class="bi bi-${type === 'success' ? 'check-circle' : type === 'danger' ? 'exclamation-triangle' : 'info-circle'} me-2"></i>
        ${message}
        <button type="button" class="btn-close" onclick="this.parentElement.remove()"></button>
      </div>
    `;
    
    if (type === 'success' || type === 'info') {
      setTimeout(() => { container.innerHTML = ''; }, 5000);
    }
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

  // Load existing categories for validation
  async loadExistingCategories() {
    try {
      const response = await fetch('/api/categories/');
      const data = await response.json();
      if (data.success && data.categories) {
        this.existingCategories = data.categories;
      }
    } catch (error) {
      console.error('Error loading categories:', error);
    }
  }
}

// Initialize and expose globally
const categoryWizard = new CategoryWizard();
window.categoryWizard = categoryWizard; // Expose on window for global access

// Load existing categories on page load
document.addEventListener('DOMContentLoaded', () => {
  categoryWizard.loadExistingCategories();
});

console.log('✅ Category Wizard (Simple) loaded');
