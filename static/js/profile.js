// Profile Page JS (moved from inline script in profile.html for CSP compliance)

// --- Pagination State ---
const assignedAssetsPagination = { page: 1, numPages: 1, pageSize: 5 };
const userActivityPagination = { page: 1, numPages: 1, pageSize: 5 };

function updateAssignedAssetsPaginationControls() {
  const prevBtn = document.getElementById('assigned-assets-prev');
  const nextBtn = document.getElementById('assigned-assets-next');
  const pageInfo = document.getElementById('assigned-assets-page-info');
  if (prevBtn && nextBtn && pageInfo) {
    prevBtn.disabled = assignedAssetsPagination.page <= 1;
    nextBtn.disabled = assignedAssetsPagination.page >= assignedAssetsPagination.numPages;
    pageInfo.textContent = `Page ${assignedAssetsPagination.page} of ${assignedAssetsPagination.numPages}`;
  }

  // --- Admin: Backup Now button wiring ---
  const backupBtn = document.getElementById('openBackupModal');
  if (backupBtn) {
    backupBtn.addEventListener('click', function() {
      const originalText = backupBtn.innerHTML;
      backupBtn.disabled = true;
      backupBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>Creating backup...';
      const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value;
      fetch('/settings/api/backup/create/', {
        method: 'POST',
        headers: { 'X-CSRFToken': csrfToken },
      })
        .then(res => res.json().then(data => ({ status: res.status, data })))
        .then(({ status, data }) => {
          const ok = status === 200 && data.success;
          showToast(ok ? 'Backup created successfully' : (data.error || 'Backup failed'), ok ? 'success' : 'danger');
          if (ok && data.filename) {
            showToast(`File: ${data.filename} (${(data.size_bytes/1024).toFixed(1)} KB)`, 'info');
          }
        })
        .catch(() => {
          showToast('Network error while creating backup', 'danger');
        })
        .finally(() => {
          backupBtn.disabled = false;
          backupBtn.innerHTML = originalText;
        });
    });
  }

  function showToast(message, type = 'info') {
    // Simple bootstrap-like toast/alert in bottom-right
    let c = document.getElementById('global-toast-container');
    if (!c) {
      c = document.createElement('div');
      c.id = 'global-toast-container';
      c.style.position = 'fixed';
      c.style.right = '24px';
      c.style.bottom = '24px';
      c.style.zIndex = '1060';
      document.body.appendChild(c);
    }
    const el = document.createElement('div');
    el.className = `alert alert-${type}`;
    el.style.minWidth = '260px';
    el.style.boxShadow = '0 8px 24px rgba(0,0,0,0.15)';
    el.textContent = message;
    c.appendChild(el);
    setTimeout(() => { el.remove(); if (!c.childElementCount) c.remove(); }, 3500);
  }
}

// Ensure a global toast helper exists
if (typeof window.showToast !== 'function') {
  window.showToast = function(message, type = 'info') {
    let c = document.getElementById('global-toast-container');
    if (!c) {
      c = document.createElement('div');
      c.id = 'global-toast-container';
      c.style.position = 'fixed';
      c.style.right = '24px';
      c.style.bottom = '24px';
      c.style.zIndex = '1060';
      document.body.appendChild(c);
    }
    const el = document.createElement('div');
    el.className = `alert alert-${type}`;
    el.style.minWidth = '260px';
    el.style.boxShadow = '0 8px 24px rgba(0,0,0,0.15)';
    el.textContent = message;
    c.appendChild(el);
    setTimeout(() => { el.remove(); if (!c.childElementCount) c.remove(); }, 3500);
  }
}

// Bind Backup Now button on DOM ready in an idempotent way
document.addEventListener('DOMContentLoaded', function() {
  const backupBtn = document.getElementById('openBackupModal');
  if (!backupBtn || backupBtn.dataset.boundBackup === '1') return;
  backupBtn.dataset.boundBackup = '1';

  backupBtn.addEventListener('click', function() {
    const originalText = backupBtn.innerHTML;
    backupBtn.disabled = true;
    backupBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>Creating backup...';
    const csrfToken = getCSRFToken();
    fetch('/settings/api/backup/create/', {
      method: 'POST',
      headers: { 'X-CSRFToken': csrfToken },
    })
      .then(res => res.json().then(data => ({ status: res.status, data })))
      .then(({ status, data }) => {
        const ok = status === 200 && data.success;
        window.showToast(ok ? 'Backup created successfully' : (data.error || 'Backup failed'), ok ? 'success' : 'danger');
        if (ok && data.filename) {
          window.showToast(`File: ${data.filename} (${(data.size_bytes/1024).toFixed(1)} KB)`, 'info');
        }
      })
      .catch(() => {
        window.showToast('Network error while creating backup', 'danger');
      })
      .finally(() => {
        backupBtn.disabled = false;
        backupBtn.innerHTML = originalText;
      });
  });
});

// Provide a local CSRF helper with cookie fallback (idempotent definition)
if (typeof window.getCSRFToken !== 'function') {
  function getCSRFToken() {
    return document.querySelector('[name=csrfmiddlewaretoken]')?.value ||
           document.cookie.split('; ').find(row => row.startsWith('csrftoken='))?.split('=')[1] || '';
  }
  window.getCSRFToken = getCSRFToken;
}

function updateUserActivityPaginationControls() {
  const prevBtn = document.getElementById('user-activity-prev');
  const nextBtn = document.getElementById('user-activity-next');
  const pageInfo = document.getElementById('user-activity-page-info');
  if (prevBtn && nextBtn && pageInfo) {
    prevBtn.disabled = userActivityPagination.page <= 1;
    nextBtn.disabled = userActivityPagination.page >= userActivityPagination.numPages;
    pageInfo.textContent = `Page ${userActivityPagination.page} of ${userActivityPagination.numPages}`;
  }
}

function loadAssignedAssets(page = 1) {
  const tableBody = document.getElementById('assigned-assets-table-body');
  const emptyDiv = document.getElementById('assigned-assets-empty');
  const countSpan = document.getElementById('assigned-assets-count');
  const badgeSpan = document.getElementById('assigned-assets-badge');
  const table = tableBody?.closest('table');
  
  if (tableBody) tableBody.innerHTML = '';
  if (emptyDiv) emptyDiv.classList.add('d-none');
  if (table) table.style.display = '';
  
  fetch(`/api/user-assets/?page=${page}&page_size=${assignedAssetsPagination.pageSize}`)
    .then(res => {
      if (!res.ok) throw new Error('Network error');
      if (res.redirected) window.location.href = res.url;
      return res.json();
    })
    .then(data => {
      assignedAssetsPagination.page = data.page || 1;
      assignedAssetsPagination.numPages = data.num_pages || 1;
      updateAssignedAssetsPaginationControls();
      
      if (data.assets && data.assets.length) {
        data.assets.forEach((a, idx) => {
          const tr = document.createElement('tr');
          tr.innerHTML = `
            <td>${a.name || ''}</td>
            <td>${a.serial || ''}</td>
            <td>${a.assigned || ''}</td>
            <td>${a.status || ''}</td>
          `;
          tableBody.appendChild(tr);
        });
        // Update both metric card and badge
        const total = data.total || data.assets.length;
        if (countSpan) countSpan.textContent = total;
        if (badgeSpan) badgeSpan.textContent = total;
      } else {
        if (table) table.style.display = 'none';
        if (emptyDiv) emptyDiv.classList.remove('d-none');
        if (countSpan) countSpan.textContent = '0';
        if (badgeSpan) badgeSpan.textContent = '0';
      }
    })
    .catch(e => {
      if (table) table.style.display = 'none';
      if (emptyDiv) {
        emptyDiv.classList.remove('d-none');
        emptyDiv.innerHTML = '<i class="bi bi-exclamation-triangle fs-1 text-danger mb-3 d-block"></i><p class="mb-0">Unable to load assigned assets. Please log in again.</p>';
      }
      if (countSpan) countSpan.textContent = '0';
      if (badgeSpan) badgeSpan.textContent = '0';
    });
}

function loadUserActivity(page = 1) {
  const tableBody = document.getElementById('user-activity-table-body');
  const emptyDiv = document.getElementById('user-activity-empty');
  const countSpan = document.getElementById('user-activity-count');
  const badgeSpan = document.getElementById('user-activity-badge');
  const table = tableBody?.closest('table');
  
  if (tableBody) tableBody.innerHTML = '';
  if (emptyDiv) emptyDiv.classList.add('d-none');
  if (table) table.style.display = '';
  
  fetch(`/api/user-activity/?page=${page}&page_size=${userActivityPagination.pageSize}`)
    .then(res => {
      if (!res.ok) throw new Error('Network error');
      if (res.redirected) window.location.href = res.url;
      return res.json();
    })
    .then(data => {
      userActivityPagination.page = data.page || 1;
      userActivityPagination.numPages = data.num_pages || 1;
      updateUserActivityPaginationControls();
      
      if (data.logs && data.logs.length) {
        data.logs.forEach((l, idx) => {
          const tr = document.createElement('tr');
          tr.innerHTML = `
            <td>${l.action || ''}</td>
            <td>${l.asset || ''}</td>
            <td>${l.time || ''}</td>
            <td>${l.details || ''}</td>
          `;
          tableBody.appendChild(tr);
        });
        // Update both metric card and badge
        const total = data.total || data.logs.length;
        if (countSpan) countSpan.textContent = total;
        if (badgeSpan) badgeSpan.textContent = total;
      } else {
        if (table) table.style.display = 'none';
        if (emptyDiv) emptyDiv.classList.remove('d-none');
        if (countSpan) countSpan.textContent = '0';
        if (badgeSpan) badgeSpan.textContent = '0';
      }
    })
    .catch(e => {
      if (table) table.style.display = 'none';
      if (emptyDiv) {
        emptyDiv.classList.remove('d-none');
        emptyDiv.innerHTML = '<i class="bi bi-exclamation-triangle fs-1 text-danger mb-3 d-block"></i><p class="mb-0">Unable to load recent activity. Please log in again.</p>';
      }
      if (countSpan) countSpan.textContent = '0';
      if (badgeSpan) badgeSpan.textContent = '0';
    });
}

function refreshCategoryDropdowns(newCategory) {
  // Find all category <select> elements by common IDs or names
  const selects = [
    ...document.querySelectorAll('select[name="category"], select#category-select, select#id_category')
  ];
  selects.forEach(select => {
    // Fetch latest categories from backend
    fetch('/api/categories/')
      .then(res => res.json())
      .then(data => {
        if (data.success && Array.isArray(data.categories)) {
          // Clear and repopulate options
          select.innerHTML = '<option value="">All</option>';
          data.categories.forEach(cat => {
            const opt = document.createElement('option');
            opt.value = cat.id;
            opt.textContent = cat.name;
            if (newCategory && cat.id === newCategory.id) {
              opt.selected = true;
            }
            select.appendChild(opt);
          });
        }
      });
  });
}

document.addEventListener('DOMContentLoaded', function() {
  // Edit profile logic - Updated for new design
  const editBtn = document.getElementById('edit-profile-btn');
  const profileEditSection = document.getElementById('profile-edit-section');
  const profileHero = document.querySelector('.profile-hero');
  const metricsGrid = document.querySelector('.metrics-grid');
  const cancelBtn = document.getElementById('cancel-edit-profile');
  
  if (editBtn && profileEditSection && cancelBtn) {
    editBtn.addEventListener('click', () => {
      // Hide hero and metrics, show edit form
      if (profileHero) profileHero.style.display = 'none';
      if (metricsGrid) metricsGrid.style.display = 'none';
      profileEditSection.classList.remove('d-none');
      // Scroll to top smoothly
      window.scrollTo({ top: 0, behavior: 'smooth' });
    });
    
    cancelBtn.addEventListener('click', () => {
      // Show hero and metrics, hide edit form
      if (profileHero) profileHero.style.display = 'block';
      if (metricsGrid) metricsGrid.style.display = 'grid';
      profileEditSection.classList.add('d-none');
      // Scroll to top smoothly
      window.scrollTo({ top: 0, behavior: 'smooth' });
    });
  }
  // Theme preference (robust, professional)
  const themeSelect = document.getElementById('theme-select');
  if (themeSelect) {
    // Set initial value from localStorage or default
    const savedTheme = localStorage.getItem('theme') || 'light';
    themeSelect.value = savedTheme;
    document.documentElement.setAttribute('data-theme', savedTheme);
    // Feedback toast/alert
    function showPrefToast(msg) {
      let toast = document.getElementById('pref-toast');
      if (!toast) {
        toast = document.createElement('div');
        toast.id = 'pref-toast';
        toast.style.position = 'fixed';
        toast.style.bottom = '32px';
        toast.style.right = '32px';
        toast.style.zIndex = 9999;
        toast.style.background = 'rgba(23,107,135,0.98)';
        toast.style.color = '#fff';
        toast.style.padding = '12px 24px';
        toast.style.borderRadius = '8px';
        toast.style.boxShadow = '0 4px 16px 0 rgba(0,0,0,0.12)';
        toast.style.fontSize = '1rem';
        toast.style.transition = 'opacity 0.3s';
        document.body.appendChild(toast);
      }
      toast.textContent = msg;
      toast.style.opacity = 1;
      setTimeout(() => { toast.style.opacity = 0; }, 1800);
    }
    themeSelect.addEventListener('change', function() {
      localStorage.setItem('theme', this.value);
      document.documentElement.setAttribute('data-theme', this.value);
      showPrefToast(`Theme set to ${this.value.charAt(0).toUpperCase() + this.value.slice(1)}`);
    });
  }
  // Future: Language/notification preference persistence
  // const langSelect = document.getElementById('language-select');
  // const notifSelect = document.getElementById('notif-select');
  // ... add similar logic for saving to localStorage or backend when enabled ...
  // Assigned assets AJAX
  function showLoading(target) {
    document.getElementById(target).innerHTML = '<div class="d-flex align-items-center justify-content-center py-3"><div class="spinner-border text-primary me-2" role="status" aria-label="Loading"></div> <span>Loading...</span></div>';
  }
  function showError(target, msg) {
    document.getElementById(target).innerHTML = `<div class='alert alert-danger text-center mb-0'>${msg}</div>`;
  }
  // Pagination event listeners
  document.getElementById('assigned-assets-prev').addEventListener('click', function() {
    if (assignedAssetsPagination.page > 1) {
      assignedAssetsPagination.page--;
      loadAssignedAssets(assignedAssetsPagination.page);
    }
  });
  document.getElementById('assigned-assets-next').addEventListener('click', function() {
    if (assignedAssetsPagination.page < assignedAssetsPagination.numPages) {
      assignedAssetsPagination.page++;
      loadAssignedAssets(assignedAssetsPagination.page);
    }
  });
  document.getElementById('user-activity-prev').addEventListener('click', function() {
    if (userActivityPagination.page > 1) {
      userActivityPagination.page--;
      loadUserActivity(userActivityPagination.page);
    }
  });
  document.getElementById('user-activity-next').addEventListener('click', function() {
    if (userActivityPagination.page < userActivityPagination.numPages) {
      userActivityPagination.page++;
      loadUserActivity(userActivityPagination.page);
    }
  });
  // Initial load
  loadAssignedAssets();
  loadUserActivity();
  
  // View My Permissions functionality
  const viewMyPermissionsBtn = document.getElementById('viewMyPermissions');
  const userPermissionsSummary = document.getElementById('user-permissions-summary');
  const currentUserPermissions = document.getElementById('current-user-permissions');
  
  if (viewMyPermissionsBtn) {
    viewMyPermissionsBtn.addEventListener('click', function() {
      if (userPermissionsSummary.classList.contains('d-none')) {
        loadCurrentUserPermissions();
        userPermissionsSummary.classList.remove('d-none');
        // Update button text and icon
        this.innerHTML = '<i class="bi bi-eye-slash me-2"></i>Hide My Permissions';
      } else {
        userPermissionsSummary.classList.add('d-none');
        // Update button text and icon
        this.innerHTML = '<i class="bi bi-shield-lock me-2"></i>View My Permissions';
      }
    });
  }
  
  function loadCurrentUserPermissions() {
    if (!currentUserPermissions) {
      console.error('❌ Permissions container not found');
      return;
    }
    
    // Get current user role from the page - multiple fallback selectors
    let userRole = 'user'; // default
    
    // Try multiple selectors to find the role badge
    const selectors = [
      '.profile-hero__subtitle .badge',
      '.section-card .badge.bg-danger',
      '.section-card .badge.bg-warning',
      '.section-card .badge.bg-secondary',
      '.badge.bg-danger',
      '.badge.bg-warning',
      '.badge.bg-secondary'
    ];
    
    for (const selector of selectors) {
      const badge = document.querySelector(selector);
      if (badge && badge.textContent.trim()) {
        const roleText = badge.textContent.trim().toLowerCase();
        console.log('🔍 Found role badge:', roleText, 'using selector:', selector);
        
        // Map display text to role value
        if (roleText.includes('admin')) {
          userRole = 'admin';
          break;
        } else if (roleText.includes('manager')) {
          userRole = 'manager';
          break;
        } else if (roleText.includes('user')) {
          userRole = 'user';
          break;
        }
      }
    }
    
    console.log('✅ Detected user role:', userRole);
    
    const permissions = {
      admin: [
        { name: 'View Assets', icon: 'bi-eye', color: 'success' },
        { name: 'Create Assets', icon: 'bi-plus-circle', color: 'primary' },
        { name: 'Edit Assets', icon: 'bi-pencil', color: 'warning' },
        { name: 'Delete Assets', icon: 'bi-trash', color: 'danger' },
        { name: 'Manage Users', icon: 'bi-people', color: 'info' },
        { name: 'View Reports', icon: 'bi-graph-up', color: 'secondary' },
        { name: 'Export Data', icon: 'bi-download', color: 'dark' },
        { name: 'System Admin', icon: 'bi-gear', color: 'danger' }
      ],
      manager: [
        { name: 'View Assets', icon: 'bi-eye', color: 'success' },
        { name: 'Create Assets', icon: 'bi-plus-circle', color: 'primary' },
        { name: 'Edit Assets', icon: 'bi-pencil', color: 'warning' },
        { name: 'View Reports', icon: 'bi-graph-up', color: 'secondary' },
        { name: 'Export Data', icon: 'bi-download', color: 'dark' }
      ],
      user: [
        { name: 'View Assets', icon: 'bi-eye', color: 'success' }
      ]
    };
    
    const userPermissions = permissions[userRole] || [];
    currentUserPermissions.innerHTML = '';
    
    userPermissions.forEach(perm => {
      const permDiv = document.createElement('div');
      permDiv.className = 'col-md-6 col-lg-4';
      permDiv.innerHTML = `
        <div class="d-flex align-items-center p-2 bg-light rounded">
          <i class="${perm.icon} text-${perm.color} me-2"></i>
          <small class="fw-semibold">${perm.name}</small>
        </div>
      `;
      currentUserPermissions.appendChild(permDiv);
    });
  }

  // ============================================================================
  // DEPRECATED: Legacy Create Category Modal Logic
  // 
  // This code has been replaced by the Category Wizard system.
  // See: category-wizard.js and admin-tools-enhanced.js
  // 
  // The new system provides:
  // - Template-based category creation
  // - Guided wizard interface
  // - Integrated field management
  // - Better validation and UX
  // 
  // This code is kept commented for reference only.
  // DO NOT UNCOMMENT - Use the new wizard system.
  // ============================================================================
  /*
  const openCreateCategoryBtn = document.getElementById('openCreateCategoryModal');
  const createCategoryModalCustom = document.getElementById('createCategoryModalCustom');
  const closeCreateCategoryModalBtn = document.getElementById('closeCreateCategoryModal');
  const cancelCreateCategoryModalBtn = document.getElementById('cancelCreateCategoryModal');
  const createCategoryForm = document.getElementById('create-category-form');
  const createCategoryFeedback = document.getElementById('create-category-feedback');
  function openCreateCategoryModal() {
    createCategoryForm.reset();
    createCategoryFeedback.innerHTML = '';
    createCategoryModalCustom.classList.add('active');
    createCategoryModalCustom.focus();
  }
  function closeCreateCategoryModal() {
    createCategoryModalCustom.classList.remove('active');
    createCategoryForm.reset();
    createCategoryFeedback.innerHTML = '';
  }
  if (openCreateCategoryBtn && createCategoryModalCustom) {
    openCreateCategoryBtn.addEventListener('click', openCreateCategoryModal);
  }
  if (closeCreateCategoryModalBtn) {
    closeCreateCategoryModalBtn.addEventListener('click', closeCreateCategoryModal);
  }
  if (cancelCreateCategoryModalBtn) {
    cancelCreateCategoryModalBtn.addEventListener('click', closeCreateCategoryModal);
  }
  if (createCategoryModalCustom) {
    createCategoryModalCustom.addEventListener('click', function(e) {
      if (e.target === createCategoryModalCustom) {
        closeCreateCategoryModal();
      }
    });
    document.addEventListener('keydown', function(e) {
      if (e.key === 'Escape' && createCategoryModalCustom.classList.contains('active')) {
        closeCreateCategoryModal();
      }
    });
  }
  if (createCategoryForm) {
    createCategoryForm.addEventListener('submit', function(e) {
      e.preventDefault();
      createCategoryFeedback.innerHTML = '';
      const name = createCategoryForm.elements['name'].value.trim();
      const description = createCategoryForm.elements['description'].value.trim();
      if (!name) {
        createCategoryFeedback.innerHTML = '<div class="alert alert-danger">Category name is required.</div>';
        return;
      }
      createCategoryFeedback.innerHTML = '<div class="alert alert-info">Creating category...</div>';
      const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value;
      fetch('/api/create-category/', {
        method: 'POST',
        headers: {
          'X-CSRFToken': csrfToken,
          'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: new URLSearchParams({ name, description })
      })
      .then(res => res.json().then(data => ({ status: res.status, data })))
      .then(({ status, data }) => {
        if (status === 200 && data.success) {
          createCategoryFeedback.innerHTML = '<div class="alert alert-success">Category created successfully!</div>';
          refreshCategoryDropdowns(data.category);
          setTimeout(() => {
            closeCreateCategoryModal();
          }, 1200);
        } else {
          createCategoryFeedback.innerHTML = `<div class="alert alert-danger">${data.error || 'Failed to create category.'}</div>`;
        }
      })
      .catch(() => {
        createCategoryFeedback.innerHTML = '<div class="alert alert-danger">Network error. Please try again.</div>';
      });
    });
  }
  */
  
  // --- Admin: Create User Custom Modal Logic ---
  const openCreateUserBtn = document.getElementById('openCreateUserModal');
  const createUserModalCustom = document.getElementById('createUserModalCustom');
  const closeCreateUserModalBtn = document.getElementById('closeCreateUserModal');
  const cancelCreateUserModalBtn = document.getElementById('cancelCreateUserModal');
  const createUserForm = document.getElementById('create-user-form');
  const createUserFeedback = document.getElementById('create-user-feedback');
  let createUserModalLocked = false; // lock modal when temp password is displayed
  const beforeUnloadHandler = (e) => {
    if (createUserModalLocked) {
      e.preventDefault();
      e.returnValue = '';
      return '';
    }
  };

  function openCreateUserModal() {
    if (createUserForm) createUserForm.reset();
    if (createUserFeedback) createUserFeedback.innerHTML = '';
    if (createUserModalCustom) {
      createUserModalCustom.classList.add('active');
      createUserModalCustom.focus();
    }
    createUserModalLocked = false;
    window.removeEventListener('beforeunload', beforeUnloadHandler);
  }
  function closeCreateUserModal() {
    if (createUserModalLocked) return; // prevent closing until acknowledged
    if (createUserModalCustom) createUserModalCustom.classList.remove('active');
    if (createUserForm) createUserForm.reset();
    if (createUserFeedback) createUserFeedback.innerHTML = '';
    window.removeEventListener('beforeunload', beforeUnloadHandler);
  }
  if (openCreateUserBtn && createUserModalCustom) {
    openCreateUserBtn.addEventListener('click', openCreateUserModal);
  }
  if (closeCreateUserModalBtn) {
    closeCreateUserModalBtn.addEventListener('click', function(){ if (!createUserModalLocked) closeCreateUserModal(); });
  }
  if (cancelCreateUserModalBtn) {
    cancelCreateUserModalBtn.addEventListener('click', function(){ if (!createUserModalLocked) closeCreateUserModal(); });
  }
  if (createUserModalCustom) {
    createUserModalCustom.addEventListener('click', function(e) {
      if (e.target === createUserModalCustom && !createUserModalLocked) closeCreateUserModal();
    });
    document.addEventListener('keydown', function(e) {
      if (e.key === 'Escape' && createUserModalCustom.classList.contains('active') && !createUserModalLocked) {
        closeCreateUserModal();
      }
    });
  }
  if (createUserForm) {
    createUserForm.addEventListener('submit', function(e) {
      e.preventDefault();
      if (createUserFeedback) createUserFeedback.innerHTML = '';
      const fd = new FormData(createUserForm);
      const username = fd.get('username')?.toString().trim();
      const email = fd.get('email')?.toString().trim();
      if (!username || !email) {
        createUserFeedback.innerHTML = '<div class="alert alert-danger">Username and Email are required.</div>';
        return;
      }
      // Optional: prevent non-admins from selecting Admin
      const role = (fd.get('role') || 'User').toString();
      const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value;
      createUserFeedback.innerHTML = '<div class="alert alert-info">Creating user...</div>';
      fetch('/api/users/create/', {
        method: 'POST',
        headers: { 'X-CSRFToken': csrfToken, 'Content-Type': 'application/x-www-form-urlencoded' },
        body: new URLSearchParams({
          username: username,
          email: email,
          first_name: fd.get('first_name')?.toString() || '',
          last_name: fd.get('last_name')?.toString() || '',
          role: role,
          password: fd.get('password')?.toString() || ''
        })
      })
      .then(res => res.json().then(data => ({ status: res.status, data })))
      .then(({ status, data }) => {
        if (status === 200 && data.success) {
          // Success message
          let html = '<div class="alert alert-success">User created successfully!</div>';
          // If server generated a temporary password, show a persistent, copyable block and DO NOT auto-close
          if (data.temporary_password) {
            createUserModalLocked = true; // lock modal until user acknowledges
            window.addEventListener('beforeunload', beforeUnloadHandler);
            // Disable form inputs to prevent losing feedback area
            try { Array.from(createUserForm.elements).forEach(el => el.disabled = true); } catch(_) {}
            html += `
              <div class="alert alert-warning mt-2" role="alert">
                <div class="d-flex flex-column gap-2">
                  <div><strong>Temporary password (copy and share securely):</strong></div>
                  <div class="d-flex align-items-center gap-2 flex-wrap">
                    <code id="temp-password-value" class="px-2 py-1">${data.temporary_password}</code>
                    <button type="button" id="copy-temp-password" class="btn btn-sm btn-outline-secondary">Copy</button>
                  </div>
                  <small class="text-muted">Shown once. User will be required to change it at first login.</small>
                  <div class="form-check mt-2">
                    <input class="form-check-input" type="checkbox" id="ack-temp-password">
                    <label class="form-check-label" for="ack-temp-password">I have saved/copied the temporary password</label>
                  </div>
                  <div>
                    <button type="button" id="dismiss-temp-password" class="btn btn-sm btn-success" disabled>Close</button>
                  </div>
                </div>
              </div>`;
          }
          createUserFeedback.innerHTML = html;
          // Bind copy action if temp password exists
          const copyBtn = document.getElementById('copy-temp-password');
          if (copyBtn) {
            copyBtn.addEventListener('click', () => {
              const pwEl = document.getElementById('temp-password-value');
              if (!pwEl) return;
              const pw = pwEl.textContent;
              navigator.clipboard.writeText(pw).then(() => {
                copyBtn.textContent = 'Copied';
                copyBtn.classList.remove('btn-outline-secondary');
                copyBtn.classList.add('btn-success');
                setTimeout(() => {
                  copyBtn.textContent = 'Copy';
                  copyBtn.classList.add('btn-outline-secondary');
                  copyBtn.classList.remove('btn-success');
                }, 2000);
              });
            });
          }
          // Acknowledge checkbox and dismiss button
          const ackCb = document.getElementById('ack-temp-password');
          const dismissBtn = document.getElementById('dismiss-temp-password');
          if (ackCb && dismissBtn) {
            ackCb.addEventListener('change', function(){
              dismissBtn.disabled = !this.checked;
            });
            dismissBtn.addEventListener('click', function(){
              createUserModalLocked = false;
              window.removeEventListener('beforeunload', beforeUnloadHandler);
              // Re-enable form controls for next use
              try { Array.from(createUserForm.elements).forEach(el => el.disabled = false); } catch(_) {}
              closeCreateUserModal();
            });
          }
          // Refresh users list in permissions modal if present
          try { loadUsersList?.(1, ''); } catch (_) {}
          // Auto-close only when no temporary password is returned
          if (!data.temporary_password) {
            setTimeout(() => { closeCreateUserModal(); }, 1500);
          }
        } else {
          createUserFeedback.innerHTML = `<div class="alert alert-danger">${data.error || 'Failed to create user.'}</div>`;
        }
      })
      .catch(() => {
        createUserFeedback.innerHTML = '<div class="alert alert-danger">Network error. Please try again.</div>';
      });
    });
  }
  // --- Admin: Permissions Management Custom Modal Logic ---
  // Note: Permissions Management modal logic has been consolidated into static/js/permissions-fixed.js
  // The duplicate logic previously here has been removed to avoid conflicts.

  // User role editing functionality
  let currentEditUserId = null;
  const editUserRoleModal = document.getElementById('editUserRoleModal');
  const editUserRoleForm = document.getElementById('edit-user-role-form');
  const editUserInfo = document.getElementById('edit-user-info');
  const editUserRoleSelect = document.getElementById('edit-user-role-select');
  const editRoleFeedback = document.getElementById('edit-role-feedback');

  window.openEditUserRole = function(userId, userName, currentRole) {
    currentEditUserId = userId;
    if (editUserInfo) editUserInfo.innerHTML = `<strong>${userName}</strong><br><small>Current role: ${currentRole}</small>`;
    if (editUserRoleSelect) editUserRoleSelect.value = currentRole;
    if (editRoleFeedback) editRoleFeedback.innerHTML = '';
    if (editUserRoleModal) editUserRoleModal.classList.add('active');
  };

  function closeEditUserRoleModal() {
    if (editUserRoleModal) editUserRoleModal.classList.remove('active');
    currentEditUserId = null;
    if (editUserRoleForm) editUserRoleForm.reset();
    if (editRoleFeedback) editRoleFeedback.innerHTML = '';
  }

  // Event listeners for user role editing
  if (editUserRoleForm) {
    editUserRoleForm.addEventListener('submit', function(e) {
      e.preventDefault();
      if (!currentEditUserId) return;
      
      const newRole = editUserRoleSelect.value;
      if (!newRole) {
        editRoleFeedback.innerHTML = '<div class="alert alert-danger">Please select a role</div>';
        return;
      }
      
      editRoleFeedback.innerHTML = '<div class="alert alert-info">Updating role...</div>';
      
      const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value;
      fetch('/api/users/update-role/', {
        method: 'POST',
        headers: {
          'X-CSRFToken': csrfToken,
          'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: new URLSearchParams({
          user_id: currentEditUserId,
          role: newRole
        })
      })
      .then(res => res.json())
      .then(data => {
        if (data.success) {
          editRoleFeedback.innerHTML = '<div class="alert alert-success">Role updated successfully!</div>';
          setTimeout(() => {
            closeEditUserRoleModal();
            loadUsersList(usersData.page, document.getElementById('user-search')?.value || '');
          }, 1000);
        } else {
          editRoleFeedback.innerHTML = `<div class="alert alert-danger">${data.error}</div>`;
        }
      })
      .catch(() => {
        editRoleFeedback.innerHTML = '<div class="alert alert-danger">Network error. Please try again.</div>';
      });
    });
  }

  // Close modal event listeners
  document.getElementById('closeEditUserRoleModal')?.addEventListener('click', closeEditUserRoleModal);
  document.getElementById('cancelEditUserRole')?.addEventListener('click', closeEditUserRoleModal);

  // Search functionality
  const userSearch = document.getElementById('user-search');
  if (userSearch) {
    userSearch.addEventListener('input', function() {
      clearTimeout(searchTimeout);
      searchTimeout = setTimeout(() => {
        loadUsersList(1, this.value);
      }, 300);
    });
  }

  // Pagination event listeners
  document.getElementById('users-prev')?.addEventListener('click', function() {
    if (usersData.page > 1) {
      loadUsersList(usersData.page - 1, userSearch?.value || '');
    }
  });

  document.getElementById('users-next')?.addEventListener('click', function() {
    if (usersData.page < usersData.num_pages) {
      loadUsersList(usersData.page + 1, userSearch?.value || '');
    }
  });

  // ============================================================================
  // DEPRECATED: Legacy Dynamic Field Management Logic
  // 
  // This code has been replaced by the Category Wizard system.
  // Dynamic fields are now managed during category creation in the wizard.
  // 
  // The new system provides:
  // - Integrated field management in wizard
  // - Template-based fields
  // - Better validation and UX
  // - Simplified workflow
  // 
  // This code is kept commented for reference only.
  // DO NOT UNCOMMENT - Use the new wizard system.
  // ============================================================================
  /*
  const openDynamicFieldBtn = document.getElementById('openDynamicFieldModal');
  const dynamicFieldModalCustom = document.getElementById('dynamicFieldModalCustom');
  const closeDynamicFieldModalBtn = document.getElementById('closeDynamicFieldModal');
  const cancelDfAddEditBtn = document.getElementById('cancelDfAddEditBtn');
  const dfAddEditForm = document.getElementById('df-add-edit-form');
  const dynamicFieldFeedback = document.getElementById('dynamic-field-feedback');
  const dfCategorySelect = document.getElementById('df-category-select');
  const dfFieldsSection = document.getElementById('df-fields-section');
  const dfFieldsTableBody = document.getElementById('df-fields-table-body');
  const dfFieldsEmpty = document.getElementById('df-fields-empty');
  const addDynamicFieldBtn = document.getElementById('addDynamicFieldBtn');
  const dfAddEditSection = document.getElementById('df-add-edit-section');
  const dfAddEditTitle = document.getElementById('df-add-edit-title');
  const dfKey = document.getElementById('df-key');
  const dfLabel = document.getElementById('df-label');
  const dfType = document.getElementById('df-type');
  const dfRequired = document.getElementById('df-required');
  const saveDfAddEditBtn = document.getElementById('saveDfAddEditBtn');

  let editingFieldId = null;
  let currentCategoryId = null;

  function openDynamicFieldModal() {
    if (dfAddEditForm) dfAddEditForm.reset();
    if (dynamicFieldFeedback) dynamicFieldFeedback.innerHTML = '';
    if (dynamicFieldModalCustom) {
      dynamicFieldModalCustom.classList.add('active');
      dynamicFieldModalCustom.focus();
    }
  }
  function closeDynamicFieldModal() {
    if (dynamicFieldModalCustom) dynamicFieldModalCustom.classList.remove('active');
    if (dfAddEditForm) dfAddEditForm.reset();
    if (dynamicFieldFeedback) dynamicFieldFeedback.innerHTML = '';
  }
  // --- Helper Functions ---
  function showDfFeedback(msg, type = 'info') {
    if (dynamicFieldFeedback) {
      dynamicFieldFeedback.innerHTML = `<div class="alert alert-${type}">${msg}</div>`;
    }
  }
  function clearDfFeedback() {
    if (dynamicFieldFeedback) dynamicFieldFeedback.innerHTML = '';
  }
  function resetDfAddEditForm() {
    dfKey.value = '';
    dfLabel.value = '';
    dfType.value = 'text';
    dfRequired.checked = false;
    editingFieldId = null;
    dfKey.disabled = false;
    // Manage required flags for clean state
    dfKey.required = true;
    dfLabel.required = true;
    dfType.required = true;
    dfAddEditTitle.textContent = 'Add Field';
    saveDfAddEditBtn.textContent = 'Save Field';
  }
  function showDfAddEditSection(edit = false, field = null) {
    dfAddEditSection.classList.remove('d-none');
    // Re-enable inputs when section is shown
    dfKey.disabled = false;
    dfLabel.disabled = false;
    dfType.disabled = false;
    dfRequired.disabled = false;
    if (edit && field) {
      editingFieldId = field.id;
      dfKey.value = field.key;
      dfKey.disabled = true; // lock key on edit
      dfLabel.value = field.label;
      dfType.value = field.type;
      dfRequired.checked = field.required;
      dfAddEditTitle.textContent = 'Edit Field';
      saveDfAddEditBtn.textContent = 'Update Field';
      // During edit, key is not required (disabled anyway)
      dfKey.required = false;
      dfLabel.required = true;
      dfType.required = true;
    } else {
      resetDfAddEditForm();
    }
  }
  function hideDfAddEditSection() {
    dfAddEditSection.classList.add('d-none');
    resetDfAddEditForm();
    // Disable inputs when hidden to avoid native validation on hidden controls
    dfKey.disabled = true;
    dfLabel.disabled = true;
    dfType.disabled = true;
    dfRequired.disabled = true;
  }
  function renderDfFieldsTable(fields) {
    dfFieldsTableBody.innerHTML = '';
    if (!fields.length) {
      dfFieldsEmpty.classList.remove('d-none');
      dfFieldsSection.classList.remove('d-none');
      return;
    }
    dfFieldsEmpty.classList.add('d-none');
    // Sort alphabetically by label (case-insensitive)
    const sorted = [...fields].sort((a, b) => (a.label || '').localeCompare(b.label || '', undefined, { sensitivity: 'base' }));
    sorted.forEach(field => {
      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td>${field.key}</td>
        <td>${field.label}</td>
        <td>${field.type.charAt(0).toUpperCase() + field.type.slice(1)}</td>
        <td>${field.required ? '<span class="badge bg-success">Yes</span>' : '<span class="badge bg-secondary">No</span>'}</td>
        <td>
          <button type="button" class="btn btn-sm btn-outline-primary me-1 df-edit-btn" data-id="${field.id}" title="Edit Field" aria-label="Edit Field"><i class="bi bi-pencil"></i></button>
          <button type="button" class="btn btn-sm btn-outline-danger df-delete-btn" data-id="${field.id}" title="Delete Field" aria-label="Delete Field"><i class="bi bi-trash"></i></button>
        </td>
      `;
      dfFieldsTableBody.appendChild(tr);
    });
    dfFieldsSection.classList.remove('d-none');
  }
  function fetchDfFields(categoryId) {
    dfFieldsSection.classList.add('d-none');
    dfFieldsTableBody.innerHTML = '';
    dfFieldsEmpty.classList.add('d-none');
    hideDfAddEditSection();
    if (!categoryId) return;
    showDfFeedback('Loading fields...', 'info');
    fetch(`/api/category/${categoryId}/fields/`)
      .then(res => res.json())
      .then(data => {
        clearDfFeedback();
        if (data.success) {
          renderDfFieldsTable(data.fields);
        } else {
          showDfFeedback(data.error || 'Failed to load fields.', 'danger');
        }
      })
      .catch(() => {
        showDfFeedback('Network error. Please try again.', 'danger');
      });
  }
  function populateDfCategoryDropdown(selectedId = null) {
    fetch('/api/categories/')
      .then(res => res.json())
      .then(data => {
        if (data.success && Array.isArray(data.categories)) {
          dfCategorySelect.innerHTML = '<option value="">-- Select Category --</option>';
          data.categories.forEach(cat => {
            const opt = document.createElement('option');
            opt.value = cat.id;
            opt.textContent = cat.name;
            if (selectedId && cat.id == selectedId) opt.selected = true;
            dfCategorySelect.appendChild(opt);
          });
        }
      });
  }
  // --- Event Listeners ---
  if (openDynamicFieldBtn && dynamicFieldModalCustom) {
    openDynamicFieldBtn.addEventListener('click', function() {
      populateDfCategoryDropdown();
      openDynamicFieldModal();
      hideDfAddEditSection();
      dfFieldsSection.classList.add('d-none');
      dfCategorySelect.value = '';
    });
  }
  if (dfCategorySelect) {
    dfCategorySelect.addEventListener('change', function() {
      currentCategoryId = this.value;
      if (currentCategoryId) {
        fetchDfFields(currentCategoryId);
      } else {
        dfFieldsSection.classList.add('d-none');
        hideDfAddEditSection();
      }
    });
  }
  if (addDynamicFieldBtn) {
    addDynamicFieldBtn.addEventListener('click', function() {
      showDfAddEditSection(false);
    });
  }
  if (dfFieldsTableBody) {
    dfFieldsTableBody.addEventListener('click', function(e) {
      if (e.target.closest('.df-edit-btn')) {
        const fieldId = e.target.closest('.df-edit-btn').dataset.id;
        // Find field data from table row
        const tr = e.target.closest('tr');
        const key = tr.children[0].textContent;
        const label = tr.children[1].textContent;
        const type = tr.children[2].textContent.toLowerCase();
        const required = tr.children[3].textContent.trim().toLowerCase() === 'yes';
        showDfAddEditSection(true, { id: fieldId, key, label, type, required });
      } else if (e.target.closest('.df-delete-btn')) {
        const fieldId = e.target.closest('.df-delete-btn').dataset.id;
        if (confirm('Are you sure you want to delete this field? This action cannot be undone.')) {
          showDfFeedback('Deleting field...', 'info');
          const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value;
          fetch(`/api/field/${fieldId}/delete/`, {
            method: 'POST',
            headers: { 'X-CSRFToken': csrfToken },
          })
            .then(res => res.json())
            .then(data => {
              if (data.success) {
                showDfFeedback('Field deleted successfully.', 'success');
                fetchDfFields(currentCategoryId);
              } else {
                showDfFeedback(data.error || 'Failed to delete field.', 'danger');
              }
            })
            .catch(() => {
              showDfFeedback('Network error. Please try again.', 'danger');
            });
        }
      }
    });
  }
  if (dfAddEditForm) {
    dfAddEditForm.addEventListener('submit', function(e) {
      e.preventDefault();
      clearDfFeedback();
      if (!currentCategoryId) {
        showDfFeedback('Please select a category first.', 'danger');
        return;
      }
      const key = dfKey.value.trim();
      const label = dfLabel.value.trim();
      const type = dfType.value;
      const required = dfRequired.checked;
      if (!label || !type) {
        showDfFeedback('Label and type are required.', 'danger');
        return;
      }
      const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value;
      if (editingFieldId) {
        // Update field
        showDfFeedback('Updating field...', 'info');
        fetch(`/api/field/${editingFieldId}/update/`, {
          method: 'POST',
          headers: { 'X-CSRFToken': csrfToken, 'Content-Type': 'application/x-www-form-urlencoded' },
          body: new URLSearchParams({ label, type, required })
        })
          .then(res => res.json())
          .then(data => {
            if (data.success) {
              showDfFeedback('Field updated successfully.', 'success');
              fetchDfFields(currentCategoryId);
              hideDfAddEditSection();
            } else {
              showDfFeedback(data.error || 'Failed to update field.', 'danger');
            }
          })
          .catch(() => {
            showDfFeedback('Network error. Please try again.', 'danger');
          });
      } else {
        // Create field
        if (!key) {
          showDfFeedback('Key is required.', 'danger');
          return;
        }
        showDfFeedback('Creating field...', 'info');
        fetch(`/api/category/${currentCategoryId}/fields/create/`, {
          method: 'POST',
          headers: { 'X-CSRFToken': csrfToken, 'Content-Type': 'application/x-www-form-urlencoded' },
          body: new URLSearchParams({ key, label, type, required })
        })
          .then(res => res.json())
          .then(data => {
            if (data.success) {
              showDfFeedback('Field created successfully.', 'success');
              fetchDfFields(currentCategoryId);
              hideDfAddEditSection();
            } else {
              showDfFeedback(data.error || 'Failed to create field.', 'danger');
            }
          })
          .catch(() => {
            showDfFeedback('Network error. Please try again.', 'danger');
          });
      }
    });
  }
  if (cancelDfAddEditBtn) {
    cancelDfAddEditBtn.addEventListener('click', function() {
      hideDfAddEditSection();
    });
  }
  if (dynamicFieldModalCustom) {
    dynamicFieldModalCustom.addEventListener('click', function(e) {
      if (e.target === dynamicFieldModalCustom) {
        closeDynamicFieldModal();
      }
    });
    document.addEventListener('keydown', function(e) {
      if (e.key === 'Escape' && dynamicFieldModalCustom.classList.contains('active')) {
        closeDynamicFieldModal();
      }
    });
  }
  */
  // End of deprecated dynamic field management code
  
  // --- Admin: Restore Backup Custom Modal Logic ---
  const openRestoreBtn = document.getElementById('openRestoreModal');
  const restoreModal = document.getElementById('restoreBackupModalCustom');
  const closeRestoreBtn = document.getElementById('closeRestoreBackupModal');
  const cancelRestoreBtn = document.getElementById('cancelRestoreBackupModal');
  const restoreForm = document.getElementById('restore-backup-form');
  const restoreFileInput = document.getElementById('restore-backup-file');
  const confirmRestoreBtn = document.getElementById('confirmRestoreBackupBtn');
  const restoreFeedback = document.getElementById('restore-backup-feedback');

  function openRestoreModal() {
    if (restoreFeedback) restoreFeedback.innerHTML = '';
    if (restoreFileInput) restoreFileInput.value = '';
    if (restoreModal) {
      restoreModal.classList.add('active');
      restoreModal.focus();
    }
  }
  function closeRestoreModal() {
    if (restoreModal) restoreModal.classList.remove('active');
    if (restoreForm) restoreForm.reset();
    if (restoreFeedback) restoreFeedback.innerHTML = '';
  }
  function showRestoreFeedback(msg, type = 'info') {
    if (restoreFeedback) restoreFeedback.innerHTML = `<div class="alert alert-${type}">${msg}</div>`;
  }

  if (openRestoreBtn && restoreModal) {
    openRestoreBtn.addEventListener('click', openRestoreModal);
  }
  if (closeRestoreBtn) closeRestoreBtn.addEventListener('click', closeRestoreModal);
  if (cancelRestoreBtn) cancelRestoreBtn.addEventListener('click', closeRestoreModal);
  if (restoreModal) {
    restoreModal.addEventListener('click', function(e) {
      if (e.target === restoreModal) closeRestoreModal();
    });
    document.addEventListener('keydown', function(e) {
      if (e.key === 'Escape' && restoreModal.classList.contains('active')) closeRestoreModal();
    });
  }

  if (restoreForm) {
    restoreForm.addEventListener('submit', function(e) {
      e.preventDefault();
      if (restoreFeedback) restoreFeedback.innerHTML = '';
      const file = restoreFileInput?.files?.[0];
      if (!file) {
        showRestoreFeedback('Please choose a backup file (.json).', 'danger');
        return;
      }
      if (!file.name.toLowerCase().endsWith('.json')) {
        showRestoreFeedback('Invalid file type. Please select a .json backup.', 'danger');
        return;
      }
      // Optional client-side size check (50MB)
      const maxSize = 50 * 1024 * 1024;
      if (file.size > maxSize) {
        showRestoreFeedback('File too large. Max allowed size is 50MB.', 'danger');
        return;
      }
      const csrfToken = window.getCSRFToken ? window.getCSRFToken() : '';
      const fd = new FormData();
      fd.append('backup_file', file);
      const originalHtml = confirmRestoreBtn ? confirmRestoreBtn.innerHTML : '';
      if (confirmRestoreBtn) {
        confirmRestoreBtn.disabled = true;
        confirmRestoreBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>Restoring...';
      }
      showRestoreFeedback('Uploading and restoring backup...', 'info');
      fetch('/settings/api/backup/restore/', {
        method: 'POST',
        headers: { 'X-CSRFToken': csrfToken },
        body: fd,
      })
        .then(res => res.json().then(data => ({ status: res.status, data })))
        .then(({ status, data }) => {
          const ok = status === 200 && data.success;
          if (ok) {
            showRestoreFeedback('Restore completed successfully.', 'success');
            window.showToast('System restore completed successfully', 'success');
            setTimeout(() => { closeRestoreModal(); }, 800);
          } else {
            showRestoreFeedback(data.error || 'Restore failed. Check the backup file and try again.', 'danger');
            window.showToast(data.error || 'Restore failed', 'danger');
          }
        })
        .catch(() => {
          showRestoreFeedback('Network error while restoring. Please try again.', 'danger');
          window.showToast('Network error while restoring', 'danger');
        })
        .finally(() => {
          if (confirmRestoreBtn) {
            confirmRestoreBtn.disabled = false;
            confirmRestoreBtn.innerHTML = originalHtml;
          }
        });
    });
  }
}); 