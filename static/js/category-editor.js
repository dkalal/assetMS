/**
 * Category Editor - World-Class Implementation
 * Tabbed interface for editing categories with dynamic field management
 * 
 * Features:
 * - Tabbed interface (Basic Info + Dynamic Fields)
 * - Real-time validation
 * - Field CRUD operations
 * - Professional UX
 */

class CategoryEditor {
  constructor() {
    this.categoryId = null;
    this.currentTab = 'info';
    this.categoryData = { name: '', description: '' };
    this.fields = [];
    this.existingCategories = [];
    this.isSubmitting = false;
    this.editingFieldId = null;
    
    console.log('✅ Category Editor initialized');
  }

  // ==================== Modal Control ====================
  
  async openModal(categoryId) {
    console.log('📝 Opening editor for category:', categoryId);
    this.categoryId = categoryId;
    this.currentTab = 'info';
    
    const modal = document.getElementById('editCategoryModal');
    if (modal) {
      modal.classList.add('active');
      await this.loadCategory();
      this.switchTab('info');
    }
  }

  closeModal() {
    if (this.isSubmitting) return;
    
    const modal = document.getElementById('editCategoryModal');
    if (modal) {
      modal.classList.remove('active');
    }
    this.reset();
  }

  reset() {
    this.categoryId = null;
    this.currentTab = 'info';
    this.categoryData = { name: '', description: '' };
    this.fields = [];
    this.editingFieldId = null;
    this.isSubmitting = false;
    
    // Clear feedback
    const feedback = document.getElementById('edit-category-feedback');
    if (feedback) feedback.innerHTML = '';
    
    // Hide field form
    this.hideFieldForm();
  }

  // ==================== Tab Management ====================
  
  switchTab(tabName) {
    this.currentTab = tabName;
    
    // Update tab buttons
    document.querySelectorAll('.edit-tab').forEach(tab => {
      tab.classList.remove('active');
      if (tab.dataset.tab === tabName) {
        tab.classList.add('active');
      }
    });
    
    // Update tab content
    document.querySelectorAll('.edit-tab-content').forEach(content => {
      content.classList.remove('active');
      content.style.display = 'none';
      if (content.dataset.tab === tabName) {
        content.classList.add('active');
        content.style.display = 'block';
      }
    });
    
    // Load tab-specific data
    if (tabName === 'fields') {
      this.loadFields();
    }
  }

  // ==================== Category Loading ====================
  
  async loadCategory() {
    try {
      const response = await fetch('/api/categories/');
      const data = await response.json();
      
      if (data.success && data.categories) {
        const category = data.categories.find(c => c.id === this.categoryId);
        
        if (category) {
          this.categoryData = {
            name: category.name,
            description: category.description || ''
          };
          
          // Populate form
          document.getElementById('editCategoryName').value = category.name;
          document.getElementById('editCategoryDescription').value = category.description || '';
          
          // Update counters
          this.updateCharCounter(document.getElementById('editCategoryName'), 'edit-name-counter');
          this.updateCharCounter(document.getElementById('editCategoryDescription'), 'edit-desc-counter');
          
          // Update info banner
          document.getElementById('edit-category-display-name').textContent = category.name;
          const assetCount = category.asset_count || 0;
          const fieldCount = category.field_count || 0;
          document.getElementById('edit-category-asset-count').textContent = 
            `${assetCount} asset${assetCount !== 1 ? 's' : ''} • ${fieldCount} field${fieldCount !== 1 ? 's' : ''}`;
        }
      }
    } catch (error) {
      console.error('Error loading category:', error);
      this.showFeedback('Failed to load category details', 'danger');
    }
  }

  // ==================== Category Saving ====================
  
  async saveCategory() {
    if (this.isSubmitting) return;
    
    const nameInput = document.getElementById('editCategoryName');
    const name = nameInput.value.trim();
    const description = document.getElementById('editCategoryDescription').value.trim();
    
    // Validate
    if (!name) {
      this.showFeedback('Category name is required', 'warning');
      nameInput.focus();
      return;
    }
    
    if (name.length < 2) {
      this.showFeedback('Category name must be at least 2 characters', 'warning');
      nameInput.focus();
      return;
    }
    
    // Check duplicates (excluding current category)
    if (this.existingCategories.some(cat => 
      cat.name.toLowerCase() === name.toLowerCase() && cat.id !== this.categoryId
    )) {
      this.showFeedback('A category with this name already exists', 'warning');
      nameInput.focus();
      return;
    }
    
    this.isSubmitting = true;
    const saveBtn = document.querySelector('#editCategoryModal .btn-primary');
    const originalText = saveBtn.innerHTML;
    saveBtn.disabled = true;
    saveBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Saving...';
    
    try {
      const response = await fetch(`/api/category/${this.categoryId}/update/`, {
        method: 'POST',
        headers: {
          'X-CSRFToken': this.getCSRFToken(),
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ name, description })
      });
      
      const data = await response.json();
      
      if (!data.success) {
        throw new Error(data.error || 'Failed to update category');
      }
      
      // Success - Reset state immediately
      this.isSubmitting = false;
      saveBtn.disabled = false;
      saveBtn.innerHTML = '<i class="bi bi-check-circle me-2"></i>Saved!';
      
      this.showFeedback('Category updated successfully!', 'success');
      
      setTimeout(() => {
        this.closeModal();
        // Reload categories list
        if (typeof loadCategories === 'function') {
          loadCategories();
        }
      }, 1500);
      
    } catch (error) {
      console.error('Error updating category:', error);
      this.showFeedback(error.message || 'Failed to update category', 'danger');
      saveBtn.disabled = false;
      saveBtn.innerHTML = originalText;
      this.isSubmitting = false;
    }
  }

  // ==================== Validation ====================
  
  validateName(input) {
    const value = input.value.trim();
    const counter = document.getElementById('edit-name-counter');
    const validation = document.getElementById('edit-name-validation');
    
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
    
    // Check duplicates (excluding current category)
    const isDuplicate = this.existingCategories.some(cat => 
      cat.name.toLowerCase() === value.toLowerCase() && cat.id !== this.categoryId
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

  updateCharCounter(element, counterId) {
    if (!element) return;
    const counter = document.getElementById(counterId);
    if (!counter) return;
    
    const length = element.value.length;
    const max = element.maxLength;
    counter.textContent = `${length}/${max}`;
    counter.className = length > max * 0.9 ? 'text-warning fw-bold' : 'text-muted';
  }

  // ==================== Field Management ====================
  
  async loadFields() {
    const container = document.getElementById('edit-fields-list');
    if (!container) return;
    
    container.innerHTML = `
      <div class="text-center py-5">
        <div class="spinner-border text-primary" role="status">
          <span class="visually-hidden">Loading fields...</span>
        </div>
      </div>
    `;
    
    try {
      const response = await fetch(`/api/category/${this.categoryId}/fields/`);
      const data = await response.json();
      
      if (data.success && data.fields) {
        this.fields = data.fields;
        this.renderFields();
      } else {
        throw new Error(data.error || 'Failed to load fields');
      }
    } catch (error) {
      console.error('Error loading fields:', error);
      container.innerHTML = `
        <div class="alert alert-danger">
          <i class="bi bi-exclamation-triangle me-2"></i>
          Failed to load fields. Please try again.
        </div>
      `;
    }
  }

  renderFields() {
    const container = document.getElementById('edit-fields-list');
    if (!container) return;
    
    if (this.fields.length === 0) {
      container.innerHTML = `
        <div class="alert alert-info">
          <i class="bi bi-info-circle me-2"></i>
          No fields configured for this category. Click "Add Field" to create custom fields.
        </div>
      `;
      return;
    }
    
    const html = this.fields.map(field => `
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
          <button type="button" class="btn btn-sm btn-outline-primary" onclick="categoryEditor.editField(${field.id})">
            <i class="bi bi-pencil"></i>
          </button>
          <button type="button" class="btn btn-sm btn-outline-danger" onclick="categoryEditor.deleteField(${field.id})">
            <i class="bi bi-trash"></i>
          </button>
        </div>
      </div>
    `).join('');
    
    container.innerHTML = html;
  }

  showFieldForm(fieldId = null) {
    const form = document.getElementById('edit-field-form');
    if (!form) return;
    
    this.editingFieldId = fieldId;
    
    if (fieldId) {
      // Edit existing field
      const field = this.fields.find(f => f.id === fieldId);
      if (field) {
        document.getElementById('edit-field-key').value = field.key;
        document.getElementById('edit-field-label').value = field.label;
        const preview = document.getElementById('edit-field-key-preview');
        if (preview) preview.textContent = field.key;
        const hint = document.getElementById('edit-field-key-hint');
        if (hint) hint.textContent = 'Key is locked because it is already in use';
        document.getElementById('edit-field-type').value = field.type;
        document.getElementById('edit-field-required').checked = field.required;
        document.getElementById('edit-field-form-title').textContent = 'Edit Field';
        
        const labelInput = document.getElementById('edit-field-label');
        if (labelInput) {
          labelInput.disabled = true;
        }
      }
    } else {
      // New field
      document.getElementById('edit-field-key').value = '';
      document.getElementById('edit-field-label').value = '';
      const preview = document.getElementById('edit-field-key-preview');
      if (preview) preview.textContent = 'auto_generated_key';
      const hint = document.getElementById('edit-field-key-hint');
      if (hint) hint.textContent = 'Auto-generated from the label';
      document.getElementById('edit-field-type').value = 'text';
      document.getElementById('edit-field-required').checked = false;
      document.getElementById('edit-field-form-title').textContent = 'Add New Field';
      
      const labelInput = document.getElementById('edit-field-label');
      if (labelInput) {
        labelInput.disabled = false;
      }
    }
    
    // Clear validation
    const validation = document.getElementById('edit-field-key-validation');
    if (validation) validation.innerHTML = '';
    
    form.style.display = 'block';
    document.getElementById('edit-field-label')?.focus();
  }

  hideFieldForm() {
    const form = document.getElementById('edit-field-form');
    if (form) {
      form.style.display = 'none';
      this.editingFieldId = null;
      document.getElementById('edit-field-label').disabled = false;
    }
    
    // Clear feedback
    const feedback = document.getElementById('edit-field-form-feedback');
    if (feedback) feedback.innerHTML = '';
  }

  async saveField() {
    const label = document.getElementById('edit-field-label').value.trim();
    const key = this.editingFieldId ? document.getElementById('edit-field-key').value.trim() : this.generateKeyFromLabel(label);
    const type = document.getElementById('edit-field-type').value;
    const required = document.getElementById('edit-field-required').checked;
    
    // Validate
    if (!label) {
      this.showFieldFeedback('Field label is required', 'warning');
      return;
    }
    
    // Validate key format
    const keyPattern = /^[a-z][a-z0-9_]*$/;
    if (!keyPattern.test(key)) {
      this.showFieldFeedback('Label must produce a valid key (lowercase letters, numbers, underscores)', 'warning');
      return;
    }
    
    // Check for duplicate keys when creating new field
    if (!this.editingFieldId) {
      const isDuplicate = this.fields.some(f => f.key === key);
      if (isDuplicate) {
        this.showFieldFeedback('A field with this key already exists', 'warning');
        return;
      }
    }
    
    try {
      let response;
      
      if (this.editingFieldId) {
        // Update existing field
        response = await fetch(`/api/field/${this.editingFieldId}/update/`, {
          method: 'POST',
          headers: {
            'X-CSRFToken': this.getCSRFToken(),
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({ label, type, required })
        });
      } else {
        // Create new field
        response = await fetch(`/api/category/${this.categoryId}/fields/create/`, {
          method: 'POST',
          headers: {
            'X-CSRFToken': this.getCSRFToken(),
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({ key, label, type, required })
        });
      }
      
      const data = await response.json();
      
      if (!data.success) {
        throw new Error(data.error || 'Failed to save field');
      }
      
      this.showFieldFeedback(`Field "${label}" ${this.editingFieldId ? 'updated' : 'created'} successfully!`, 'success');
      
      setTimeout(() => {
        this.hideFieldForm();
        this.loadFields();
      }, 1000);
      
    } catch (error) {
      console.error('Error saving field:', error);
      this.showFieldFeedback(error.message || 'Failed to save field', 'danger');
    }
  }

  async deleteField(fieldId) {
    const field = this.fields.find(f => f.id === fieldId);
    if (!field) return;
    
    if (!confirm(`Delete field "${field.label}"?`)) return;
    
    try {
      const response = await fetch(`/api/field/${fieldId}/delete/`, {
        method: 'POST',
        headers: {
          'X-CSRFToken': this.getCSRFToken(),
          'Content-Type': 'application/json'
        }
      });
      
      const data = await response.json();
      
      if (!data.success) {
        throw new Error(data.error || 'Failed to delete field');
      }
      
      this.showFeedback(`Field "${field.label}" deleted successfully`, 'success');
      this.loadFields();
      
    } catch (error) {
      console.error('Error deleting field:', error);
      this.showFeedback(error.message || 'Failed to delete field', 'danger');
    }
  }

  editField(fieldId) {
    this.showFieldForm(fieldId);
  }

  handleFieldLabelInput(input) {
    const value = input.value.trim();
    const preview = document.getElementById('edit-field-key-preview');
    const validation = document.getElementById('edit-field-key-validation');

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

    const isDuplicate = this.fields.some(f => 
      f.key === key && f.id !== this.editingFieldId
    );

    if (isDuplicate) {
      validation.innerHTML = '<i class="bi bi-exclamation-triangle me-1"></i>A field with this key already exists';
      validation.classList.add('text-danger');
      return;
    }

    validation.innerHTML = '<i class="bi bi-check-circle me-1 text-success"></i>Key looks great';
    validation.className = 'text-success small';
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

  // ==================== Utilities ====================
  
  showFeedback(message, type = 'info') {
    const container = document.getElementById('edit-category-feedback');
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

  showFieldFeedback(message, type = 'info') {
    const container = document.getElementById('edit-field-form-feedback');
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
const categoryEditor = new CategoryEditor();
window.categoryEditor = categoryEditor; // Expose on window for global access

// Load existing categories on page load
document.addEventListener('DOMContentLoaded', () => {
  categoryEditor.loadExistingCategories();
});

console.log('✅ Category Editor loaded');
