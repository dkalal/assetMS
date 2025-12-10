/**
 * ============================================================================
 * PHASE 7: ASSET DETAIL - ENHANCED FUNCTIONALITY
 * ============================================================================
 * World-class features: inline editing, real-time updates, keyboard shortcuts
 * Inspired by: Notion, Airtable, Linear, ServiceNow ITAM
 * ============================================================================
 */

class AssetDetailManager {
  constructor(assetUuid) {
    this.assetUuid = assetUuid;
    this.csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value;
    this.isEditing = false;
    this.originalValues = {};
    this.init();
  }

  init() {
    this.setupInlineEditing();
    this.setupKeyboardShortcuts();
    this.setupTabRefresh();
    this.setupQuickActions();
  }

  /**
   * INLINE EDITING - Click to edit fields (Notion-style)
   */
  setupInlineEditing() {
    const editableFields = document.querySelectorAll('.data-value.editable');
    
    editableFields.forEach(field => {
      field.addEventListener('click', (e) => {
        if (!this.isEditing) {
          this.startEditing(field);
        }
      });
    });
  }

  startEditing(field) {
    this.isEditing = true;
    const fieldName = field.dataset.field;
    const currentValue = field.textContent.trim();
    
    // Store original value
    this.originalValues[fieldName] = currentValue;
    
    // Add editing class
    field.classList.add('editing');
    
    // Create input element
    const input = document.createElement('input');
    input.type = 'text';
    input.value = currentValue;
    input.className = 'form-control form-control-sm';
    input.style.width = '100%';
    
    // Replace content with input
    field.innerHTML = '';
    field.appendChild(input);
    
    // Focus and select
    input.focus();
    input.select();
    
    // Handle save on Enter
    input.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        this.saveEdit(field, fieldName, input.value);
      } else if (e.key === 'Escape') {
        this.cancelEdit(field, fieldName);
      }
    });
    
    // Handle save on blur
    input.addEventListener('blur', () => {
      setTimeout(() => {
        if (this.isEditing) {
          this.saveEdit(field, fieldName, input.value);
        }
      }, 200);
    });
  }

  async saveEdit(field, fieldName, newValue) {
    // Don't save if value hasn't changed
    if (newValue === this.originalValues[fieldName]) {
      this.cancelEdit(field, fieldName);
      return;
    }
    
    // Show loading state
    field.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Saving...';
    
    try {
      const response = await fetch(`/assets/api/${this.assetUuid}/quick-edit/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': this.csrfToken
        },
        body: JSON.stringify({
          field: fieldName,
          value: newValue
        })
      });
      
      if (response.ok) {
        // Update UI with new value
        field.textContent = newValue;
        field.classList.remove('editing');
        this.isEditing = false;
        
        // Show success toast
        this.showToast('Updated successfully', 'success');
      } else {
        throw new Error('Failed to update');
      }
    } catch (error) {
      // Restore original value
      field.textContent = this.originalValues[fieldName];
      field.classList.remove('editing');
      this.isEditing = false;
      
      // Show error toast
      this.showToast('Update failed', 'danger');
    }
  }

  cancelEdit(field, fieldName) {
    field.textContent = this.originalValues[fieldName];
    field.classList.remove('editing');
    this.isEditing = false;
  }

  /**
   * KEYBOARD SHORTCUTS - Power user features
   */
  setupKeyboardShortcuts() {
    document.addEventListener('keydown', (e) => {
      // Cmd/Ctrl + E: Edit asset
      if ((e.metaKey || e.ctrlKey) && e.key === 'e') {
        e.preventDefault();
        const editBtn = document.querySelector('a[href*="update"]');
        if (editBtn) editBtn.click();
      }
      
      // Cmd/Ctrl + T: Transfer asset
      if ((e.metaKey || e.ctrlKey) && e.key === 't') {
        e.preventDefault();
        const transferBtn = document.querySelector('[data-bs-target="#transferAssetModal"]');
        if (transferBtn) transferBtn.click();
      }
      
      // Cmd/Ctrl + P: Print
      if ((e.metaKey || e.ctrlKey) && e.key === 'p') {
        e.preventDefault();
        window.print();
      }
      
      // Number keys: Switch tabs (1-5)
      if (e.key >= '1' && e.key <= '5' && !e.metaKey && !e.ctrlKey) {
        const tabs = document.querySelectorAll('.nav-tabs-modern .nav-link');
        const index = parseInt(e.key) - 1;
        if (tabs[index] && document.activeElement.tagName !== 'INPUT') {
          e.preventDefault();
          tabs[index].click();
        }
      }
    });
  }

  /**
   * TAB REFRESH - Reload tab content without full page refresh
   */
  setupTabRefresh() {
    const refreshButtons = document.querySelectorAll('[data-refresh-tab]');
    
    refreshButtons.forEach(btn => {
      btn.addEventListener('click', async () => {
        const tabName = btn.dataset.refreshTab;
        await this.refreshTab(tabName);
      });
    });
  }

  async refreshTab(tabName) {
    const tabContent = document.getElementById(`${tabName}Tab`);
    if (!tabContent) return;
    
    // Show loading
    const originalContent = tabContent.innerHTML;
    tabContent.innerHTML = `
      <div class="text-center py-5">
        <div class="spinner-border text-primary" role="status">
          <span class="visually-hidden">Loading...</span>
        </div>
      </div>
    `;
    
    try {
      const response = await fetch(`/assets/api/${this.assetUuid}/tab/${tabName}/`);
      if (response.ok) {
        const data = await response.json();
        tabContent.innerHTML = data.html || originalContent;
        this.showToast('Refreshed', 'success');
      } else {
        throw new Error('Failed to refresh');
      }
    } catch (error) {
      tabContent.innerHTML = originalContent;
      this.showToast('Refresh failed', 'danger');
    }
  }

  /**
   * QUICK ACTIONS - Floating action buttons for common tasks
   */
  setupQuickActions() {
    // Create quick action menu (hidden by default, shown on scroll)
    const quickMenu = document.createElement('div');
    quickMenu.className = 'quick-actions-menu';
    quickMenu.innerHTML = `
      <button class="quick-action-btn" title="Edit (Ctrl+E)" data-action="edit">
        <i class="bi bi-pencil"></i>
      </button>
      <button class="quick-action-btn" title="Transfer (Ctrl+T)" data-action="transfer">
        <i class="bi bi-arrow-left-right"></i>
      </button>
      <button class="quick-action-btn" title="Print (Ctrl+P)" data-action="print">
        <i class="bi bi-printer"></i>
      </button>
      <button class="quick-action-btn" title="Back to Top" data-action="top">
        <i class="bi bi-arrow-up"></i>
      </button>
    `;
    
    // Add styles
    const style = document.createElement('style');
    style.textContent = `
      .quick-actions-menu {
        position: fixed;
        right: 2rem;
        bottom: 2rem;
        display: flex;
        flex-direction: column;
        gap: 0.75rem;
        opacity: 0;
        transform: translateY(20px);
        transition: all 0.3s;
        z-index: 1000;
        pointer-events: none;
      }
      
      .quick-actions-menu.visible {
        opacity: 1;
        transform: translateY(0);
        pointer-events: auto;
      }
      
      .quick-action-btn {
        width: 48px;
        height: 48px;
        border-radius: 50%;
        border: none;
        background: var(--ad-primary, #6B9BD1);
        color: white;
        font-size: 1.25rem;
        display: flex;
        align-items: center;
        justify-content: center;
        cursor: pointer;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
        transition: all 0.2s;
      }
      
      .quick-action-btn:hover {
        transform: scale(1.1);
        box-shadow: 0 6px 16px rgba(0, 0, 0, 0.2);
      }
      
      .quick-action-btn:active {
        transform: scale(0.95);
      }
      
      @media (max-width: 767px) {
        .quick-actions-menu {
          right: 1rem;
          bottom: 1rem;
        }
        
        .quick-action-btn {
          width: 40px;
          height: 40px;
          font-size: 1rem;
        }
      }
    `;
    document.head.appendChild(style);
    document.body.appendChild(quickMenu);
    
    // Show/hide on scroll
    let scrollTimeout;
    window.addEventListener('scroll', () => {
      clearTimeout(scrollTimeout);
      
      if (window.scrollY > 300) {
        quickMenu.classList.add('visible');
      } else {
        quickMenu.classList.remove('visible');
      }
    });
    
    // Handle quick action clicks
    quickMenu.addEventListener('click', (e) => {
      const btn = e.target.closest('.quick-action-btn');
      if (!btn) return;
      
      const action = btn.dataset.action;
      
      switch (action) {
        case 'edit':
          document.querySelector('a[href*="update"]')?.click();
          break;
        case 'transfer':
          document.querySelector('[data-bs-target="#transferAssetModal"]')?.click();
          break;
        case 'print':
          window.print();
          break;
        case 'top':
          window.scrollTo({ top: 0, behavior: 'smooth' });
          break;
      }
    });
  }

  /**
   * TOAST NOTIFICATIONS
   */
  showToast(message, type = 'info') {
    // Use Bootstrap toast if available
    if (window.showToast) {
      window.showToast(message, type);
      return;
    }
    
    // Fallback: simple alert
    const toastContainer = document.getElementById('toastContainer') || this.createToastContainer();
    
    const toast = document.createElement('div');
    toast.className = `alert alert-${type} alert-dismissible fade show`;
    toast.role = 'alert';
    toast.innerHTML = `
      ${message}
      <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    toastContainer.appendChild(toast);
    
    // Auto dismiss after 3 seconds
    setTimeout(() => {
      toast.classList.remove('show');
      setTimeout(() => toast.remove(), 300);
    }, 3000);
  }

  createToastContainer() {
    const container = document.createElement('div');
    container.id = 'toastContainer';
    container.style.cssText = 'position: fixed; top: 1rem; right: 1rem; z-index: 9999;';
    document.body.appendChild(container);
    return container;
  }
}

/**
 * DOCUMENT UPLOAD HANDLER
 */
class DocumentUploader {
  constructor(assetUuid) {
    this.assetUuid = assetUuid;
    this.csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value;
  }

  async upload(file) {
    const formData = new FormData();
    formData.append('document', file);
    
    try {
      const response = await fetch(`/assets/api/${this.assetUuid}/documents/upload/`, {
        method: 'POST',
        headers: {
          'X-CSRFToken': this.csrfToken
        },
        body: formData
      });
      
      if (response.ok) {
        return await response.json();
      } else {
        throw new Error('Upload failed');
      }
    } catch (error) {
      console.error('Document upload error:', error);
      throw error;
    }
  }
}

/**
 * INITIALIZE ON PAGE LOAD
 */
document.addEventListener('DOMContentLoaded', () => {
  const assetUuid = document.querySelector('[data-asset-uuid]')?.dataset.assetUuid;
  
  if (assetUuid) {
    window.assetDetailManager = new AssetDetailManager(assetUuid);
    window.documentUploader = new DocumentUploader(assetUuid);
  }
  
  // Add visual feedback for editable fields
  document.querySelectorAll('.data-value.editable').forEach(field => {
    field.setAttribute('title', 'Click to edit (inline editing)');
  });
  
  // Smooth scroll for timeline items
  document.querySelectorAll('.timeline-item').forEach((item, index) => {
    item.style.animationDelay = `${index * 0.1}s`;
  });
  
  // Add keyboard shortcut hints
  const shortcutsHint = document.createElement('div');
  shortcutsHint.className = 'text-muted small text-end mb-2 no-print';
  shortcutsHint.innerHTML = `
    <span title="Keyboard shortcuts available">
      <i class="bi bi-keyboard"></i> 
      <span class="d-none d-md-inline">Shortcuts: 1-5 (tabs), Ctrl+E (edit), Ctrl+T (transfer), Ctrl+P (print)</span>
    </span>
  `;
  
  const firstTab = document.querySelector('.nav-tabs-modern');
  if (firstTab) {
    firstTab.parentNode.insertBefore(shortcutsHint, firstTab);
  }
});
