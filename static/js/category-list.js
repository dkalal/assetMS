/**
 * Category List Management - World-Class Implementation
 * Handles category display, loading, and integration with wizard/editor
 * 
 * Features:
 * - Category grid display
 * - Real-time loading
 * - Delete operations
 * - Integration with wizard and editor
 */

// Global state
let existingCategories = [];
let isLoading = false;

// ==================== Category Loading ====================

function loadCategories() {
  if (isLoading) return;
  
  isLoading = true;
  const container = document.getElementById('categoryListContainer');
  
  if (!container) {
    console.error('Category list container not found');
    return;
  }
  
  // Show loading state
  container.innerHTML = `
    <div class="text-center py-5">
      <div class="spinner-border text-primary" role="status">
        <span class="visually-hidden">Loading categories...</span>
      </div>
      <p class="text-muted mt-3">Loading categories...</p>
    </div>
  `;
  
  fetch('/api/categories/')
    .then(response => response.json())
    .then(data => {
      if (data.success && data.categories) {
        existingCategories = data.categories;
        
        // Update wizard and editor with latest categories
        if (window.categoryWizard) {
          categoryWizard.existingCategories = data.categories;
        }
        if (window.categoryEditor) {
          categoryEditor.existingCategories = data.categories;
        }
        
        renderCategories(data.categories);
      } else {
        throw new Error(data.error || 'Failed to load categories');
      }
    })
    .catch(error => {
      console.error('Error loading categories:', error);
      container.innerHTML = `
        <div class="alert alert-danger">
          <i class="bi bi-exclamation-triangle me-2"></i>
          Failed to load categories. Please refresh the page.
          <button type="button" class="btn btn-sm btn-outline-danger ms-3" onclick="loadCategories()">
            <i class="bi bi-arrow-clockwise me-1"></i>Retry
          </button>
        </div>
      `;
    })
    .finally(() => {
      isLoading = false;
    });
}

// ==================== Category Rendering ====================

function renderCategories(categories) {
  const container = document.getElementById('categoryListContainer');
  
  if (!container) return;
  
  if (!categories || categories.length === 0) {
    container.innerHTML = `
      <div class="text-center py-5">
        <i class="bi bi-inbox" style="font-size: 4rem; color: #ccc;"></i>
        <h5 class="mt-3 text-muted">No Categories Found</h5>
        <p class="text-muted">Create your first category to get started organizing your assets.</p>
        <button class="btn btn-primary mt-3" onclick="categoryWizard.openWizard()">
          <i class="bi bi-magic me-2"></i>Create Category
        </button>
      </div>
    `;
    return;
  }
  
  let html = '<div class="row g-4">';
  
  categories.forEach(category => {
    const fieldCount = category.field_count || 0;
    const assetCount = category.asset_count || 0;
    const description = category.description || '';
    
    html += `
      <div class="col-md-6 col-lg-4">
        <div class="card h-100 shadow-sm hover-lift" style="transition: transform 0.2s ease, box-shadow 0.2s ease;">
          <div class="card-body">
            <div class="d-flex justify-content-between align-items-start mb-3">
              <h5 class="card-title mb-0 d-flex align-items-center">
                <i class="bi bi-folder-fill me-2 text-primary"></i>
                ${escapeHtml(category.name)}
              </h5>
              <div class="dropdown">
                <button class="btn btn-sm btn-outline-secondary" type="button" data-bs-toggle="dropdown" aria-expanded="false">
                  <i class="bi bi-three-dots-vertical"></i>
                </button>
                <ul class="dropdown-menu dropdown-menu-end">
                  <li>
                    <a class="dropdown-item" href="javascript:void(0)" onclick="editCategory(${category.id})">
                      <i class="bi bi-pencil me-2"></i>Edit
                    </a>
                  </li>
                  <li><hr class="dropdown-divider"></li>
                  <li>
                    <a class="dropdown-item text-danger" href="javascript:void(0)" onclick="deleteCategory(${category.id}, '${escapeHtml(category.name).replace(/'/g, "\\'")}')">
                      <i class="bi bi-trash me-2"></i>Delete
                    </a>
                  </li>
                </ul>
              </div>
            </div>
            
            ${description ? `
              <p class="text-muted small mb-3" style="line-height: 1.5;">
                ${escapeHtml(description)}
              </p>
            ` : ''}
            
            <div class="d-flex gap-3 text-muted small mt-auto">
              <span title="${fieldCount} custom field${fieldCount !== 1 ? 's' : ''}">
                <i class="bi bi-list-ul me-1"></i>${fieldCount} field${fieldCount !== 1 ? 's' : ''}
              </span>
              <span title="${assetCount} asset${assetCount !== 1 ? 's' : ''}">
                <i class="bi bi-box-seam me-1"></i>${assetCount} asset${assetCount !== 1 ? 's' : ''}
              </span>
            </div>
          </div>
        </div>
      </div>
    `;
  });
  
  html += '</div>';
  
  container.innerHTML = html;
}

// ==================== Category Operations ====================

function editCategory(categoryId) {
  if (window.categoryEditor) {
    categoryEditor.openModal(categoryId);
  } else {
    console.error('Category editor not initialized');
    alert('Category editor is not available. Please refresh the page.');
  }
}

function deleteCategory(categoryId, categoryName) {
  // Check if category has assets
  const category = existingCategories.find(c => c.id === categoryId);
  const assetCount = category?.asset_count || 0;
  
  let confirmMessage = `Are you sure you want to delete the category "${categoryName}"?`;
  
  if (assetCount > 0) {
    confirmMessage = `Warning: This category has ${assetCount} asset${assetCount !== 1 ? 's' : ''}.\n\n` +
                     `Deleting this category will affect ${assetCount} asset${assetCount !== 1 ? 's' : ''}.\n\n` +
                     `Are you sure you want to continue?`;
  }
  
  if (!confirm(confirmMessage)) {
    return;
  }
  
  // Show loading state
  const container = document.getElementById('categoryListContainer');
  const originalContent = container.innerHTML;
  
  container.innerHTML = `
    <div class="text-center py-5">
      <div class="spinner-border text-danger" role="status">
        <span class="visually-hidden">Deleting category...</span>
      </div>
      <p class="text-muted mt-3">Deleting "${escapeHtml(categoryName)}"...</p>
    </div>
  `;
  
  fetch(`/api/category/${categoryId}/delete/`, {
    method: 'POST',
    headers: {
      'X-CSRFToken': getCSRFToken(),
      'Content-Type': 'application/json'
    }
  })
    .then(response => response.json())
    .then(data => {
      if (data.success) {
        // Show success message
        showToast(`Category "${categoryName}" deleted successfully`, 'success');
        
        // Reload categories
        loadCategories();
      } else {
        throw new Error(data.error || 'Failed to delete category');
      }
    })
    .catch(error => {
      console.error('Error deleting category:', error);
      
      // Restore original content
      container.innerHTML = originalContent;
      
      // Show error message
      showToast(error.message || 'Failed to delete category', 'danger');
    });
}

// ==================== Utilities ====================

function escapeHtml(text) {
  if (!text) return '';
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

function getCSRFToken() {
  return document.querySelector('[name=csrfmiddlewaretoken]')?.value || 
         document.cookie.split('; ').find(row => row.startsWith('csrftoken='))?.split('=')[1] || '';
}

// Local toast implementation - never calls window.showToast to prevent recursion
function showToast(message, type = 'info') {
  // Create simple toast notification directly (no global function checks)
  const toastContainer = document.getElementById('toast-container') || createToastContainer();
  
  const toast = document.createElement('div');
  toast.className = `alert alert-${type} alert-dismissible fade show`;
  toast.style.cssText = 'position: fixed; top: 20px; right: 20px; z-index: 10999; min-width: 300px; max-width: 500px; box-shadow: 0 4px 12px rgba(0,0,0,0.15);';
  
  const iconMap = {
    'success': 'check-circle-fill',
    'danger': 'exclamation-triangle-fill',
    'warning': 'exclamation-circle-fill',
    'info': 'info-circle-fill'
  };
  
  toast.innerHTML = `
    <div class="d-flex align-items-center">
      <i class="bi bi-${iconMap[type] || 'info-circle-fill'} me-2"></i>
      <span class="flex-grow-1">${escapeHtml(message)}</span>
      <button type="button" class="btn-close ms-2" aria-label="Close"></button>
    </div>
  `;
  
  // Add close button handler
  const closeBtn = toast.querySelector('.btn-close');
  if (closeBtn) {
    closeBtn.addEventListener('click', () => {
      toast.classList.remove('show');
      setTimeout(() => toast.remove(), 300);
    });
  }
  
  toastContainer.appendChild(toast);
  
  // Auto-remove after 5 seconds
  setTimeout(() => {
    if (toast.parentElement) {
      toast.classList.remove('show');
      setTimeout(() => {
        if (toast.parentElement) {
          toast.remove();
        }
      }, 300);
    }
  }, 5000);
}

function createToastContainer() {
  const container = document.createElement('div');
  container.id = 'toast-container';
  container.style.cssText = 'position: fixed; top: 20px; right: 20px; z-index: 9999;';
  document.body.appendChild(container);
  return container;
}

// ==================== Keyboard Shortcuts ====================

document.addEventListener('keydown', function(e) {
  // ESC to close modals
  if (e.key === 'Escape') {
    if (window.categoryWizard && document.getElementById('categoryWizardModal')?.classList.contains('active')) {
      categoryWizard.closeWizard();
    }
    if (window.categoryEditor && document.getElementById('editCategoryModal')?.classList.contains('active')) {
      categoryEditor.closeModal();
    }
  }
  
  // Ctrl/Cmd + K to open wizard
  if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
    e.preventDefault();
    if (window.categoryWizard) {
      categoryWizard.openWizard();
    }
  }
});

// ==================== Modal Overlay Click Handler ====================

document.addEventListener('click', function(e) {
  // Close wizard on overlay click
  if (e.target.id === 'categoryWizardModal' && e.target.classList.contains('custom-modal-overlay')) {
    if (window.categoryWizard && !categoryWizard.isSubmitting) {
      categoryWizard.closeWizard();
    }
  }
  
  // Close editor on overlay click
  if (e.target.id === 'editCategoryModal' && e.target.classList.contains('custom-modal-overlay')) {
    if (window.categoryEditor && !categoryEditor.isSubmitting) {
      categoryEditor.closeModal();
    }
  }
});

// ==================== Initialization ====================

document.addEventListener('DOMContentLoaded', function() {
  console.log('✅ Category List initialized');
  
  // Load categories on page load
  loadCategories();
  
  // Refresh categories every 30 seconds
  setInterval(function() {
    // Only refresh if not currently editing
    if (!document.getElementById('categoryWizardModal')?.classList.contains('active') &&
        !document.getElementById('editCategoryModal')?.classList.contains('active')) {
      loadCategories();
    }
  }, 30000);
});

console.log('✅ Category List script loaded');
