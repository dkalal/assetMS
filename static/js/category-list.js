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
let searchTerm = '';

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
        
        // Update metrics
        updateMetrics(data.categories);
        
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

// ==================== Metrics Update ====================

function updateMetrics(categories) {
  if (!categories) return;
  
  // Calculate metrics
  const totalCategories = categories.length;
  const totalAssets = categories.reduce((sum, cat) => sum + (cat.asset_count || 0), 0);
  const totalFields = categories.reduce((sum, cat) => sum + (cat.field_count || 0), 0);
  const activeCategories = categories.filter(cat => (cat.asset_count || 0) > 0).length;
  
  // Update DOM
  const metricTotal = document.getElementById('metric-total');
  const metricAssets = document.getElementById('metric-assets');
  const metricFields = document.getElementById('metric-fields');
  const metricActive = document.getElementById('metric-active');
  
  if (metricTotal) metricTotal.textContent = totalCategories;
  if (metricAssets) metricAssets.textContent = totalAssets;
  if (metricFields) metricFields.textContent = totalFields;
  if (metricActive) metricActive.textContent = activeCategories;
}

// ==================== Category Filtering ====================

function filterCategories() {
  if (!searchTerm) {
    renderCategories(existingCategories);
    return;
  }
  
  const filtered = existingCategories.filter(category => {
    const nameMatch = category.name.toLowerCase().includes(searchTerm);
    const descMatch = category.description?.toLowerCase().includes(searchTerm);
    return nameMatch || descMatch;
  });
  
  renderCategories(filtered);
  
  // Show search results count
  const container = document.getElementById('categoryListContainer');
  if (filtered.length === 0 && searchTerm) {
    container.innerHTML = `
      <div class="text-center py-5">
        <i class="bi bi-search" style="font-size: 4rem; color: #ccc;"></i>
        <h5 class="mt-3 text-muted">No Results Found</h5>
        <p class="text-muted">No categories match "${escapeHtml(searchTerm)}"</p>
        <button class="btn btn-outline-primary mt-3" onclick="clearSearch()">
          <i class="bi bi-x-circle me-2"></i>Clear Search
        </button>
      </div>
    `;
  }
}

function clearSearch() {
  const searchInput = document.getElementById('categorySearchInput');
  if (searchInput) {
    searchInput.value = '';
    searchTerm = '';
    filterCategories();
  }
}

// ==================== Category Rendering ====================

function renderCategories(categories) {
  const container = document.getElementById('categoryListContainer');
  
  if (!container) return;
  
  if (!categories || categories.length === 0) {
    container.innerHTML = `
      <div class="empty-state">
        <div class="empty-state-icon">
          <i class="bi bi-folder-x"></i>
        </div>
        <h3>No Categories Yet</h3>
        <p>Create your first category to start organizing your assets with custom fields</p>
        <button class="btn btn-primary btn-lg mt-2" onclick="categoryWizard.openWizard()">
          <i class="bi bi-plus-circle me-2"></i>Create Your First Category
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
        <div class="card h-100 border-0 shadow-sm category-card" onclick="editCategory(${category.id})">
          <div class="card-body p-4">
            <div class="d-flex align-items-start mb-3">
              <div class="category-icon-wrapper me-3">
                <i class="bi bi-folder-fill"></i>
              </div>
              <div class="flex-grow-1">
                <h5 class="card-title mb-1 fw-bold" style="color: #1e293b; font-size: 1.125rem;">
                  ${escapeHtml(category.name)}
                </h5>
                <div class="d-flex gap-2 align-items-center mt-2">
                  <span class="badge bg-primary bg-opacity-10 text-primary" style="font-size: 0.75rem; padding: 0.35rem 0.65rem;">
                    <i class="bi bi-box-seam me-1"></i>${assetCount}
                  </span>
                  <span class="badge bg-info bg-opacity-10 text-info" style="font-size: 0.75rem; padding: 0.35rem 0.65rem;">
                    <i class="bi bi-sliders me-1"></i>${fieldCount}
                  </span>
                </div>
              </div>
              <div class="dropdown" onclick="event.stopPropagation();">
                <button class="btn btn-sm btn-light border-0" type="button" data-bs-toggle="dropdown" aria-expanded="false" style="width: 32px; height: 32px; padding: 0; border-radius: 8px;">
                  <i class="bi bi-three-dots-vertical"></i>
                </button>
                <ul class="dropdown-menu dropdown-menu-end shadow border-0" style="border-radius: 12px; min-width: 160px;">
                  <li>
                    <a class="dropdown-item rounded" href="javascript:void(0)" onclick="editCategory(${category.id}); event.stopPropagation();" style="padding: 0.5rem 1rem;">
                      <i class="bi bi-pencil-square me-2 text-primary"></i>Edit
                    </a>
                  </li>
                  <li><hr class="dropdown-divider my-1"></li>
                  <li>
                    <a class="dropdown-item rounded text-danger" href="javascript:void(0)" onclick="deleteCategory(${category.id}, '${escapeHtml(category.name).replace(/'/g, "\\'")}'); event.stopPropagation();" style="padding: 0.5rem 1rem;">
                      <i class="bi bi-trash me-2"></i>Delete
                    </a>
                  </li>
                </ul>
              </div>
            </div>
            
            ${description ? `
              <p class="text-muted small mb-3" style="line-height: 1.6; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; min-height: 2.4em;">
                ${escapeHtml(description)}
              </p>
            ` : `
              <p class="text-muted small fst-italic mb-3" style="min-height: 2.4em;">
                No description provided
              </p>
            `}
            
            <div class="border-top pt-3">
              <div class="d-flex justify-content-between align-items-center text-muted" style="font-size: 0.875rem;">
                <span title="${fieldCount} custom field${fieldCount !== 1 ? 's' : ''}">
                  <i class="bi bi-sliders me-1"></i>${fieldCount} field${fieldCount !== 1 ? 's' : ''}
                </span>
                <span title="${assetCount} asset${assetCount !== 1 ? 's' : ''}">
                  <i class="bi bi-archive me-1"></i>${assetCount} asset${assetCount !== 1 ? 's' : ''}
                </span>
              </div>
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
  
  // Initialize search functionality
  const searchInput = document.getElementById('categorySearchInput');
  if (searchInput) {
    searchInput.addEventListener('input', function(e) {
      searchTerm = e.target.value.toLowerCase().trim();
      filterCategories();
    });
  }
  
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
