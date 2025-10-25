/**
 * World-Class Admin Tools Management
 * Professional multi-tenancy aware category and dynamic field management
 * with analytics, validation, and modern UX/UI
 */

class AdminToolsManager {
    constructor() {
        this.categories = [];
        this.fields = [];
        this.currentCategory = null;
        this.editingField = null;
        this.currentCompany = null;
        this.shouldReopenCategoryManagement = false; // Track modal state
        this.userRole = document.querySelector('[data-user-role]')?.dataset.userRole || '';
        this.isDisabled = this.userRole !== 'admin';
        if (this.isDisabled) {
            return;
        }
        this.init();
    }
    
    init() {
        this.bindEvents();
        this.loadCompanyContext();
    }
    
    // ==================== Utility Methods ====================
    
    getCSRFToken() {
        return document.querySelector('[name=csrfmiddlewaretoken]')?.value ||
               document.cookie.split('; ').find(row => row.startsWith('csrftoken='))?.split('=')[1] || '';
    }
    
    showToast(message, type = 'info') {
        let container = document.getElementById('admin-toast-container');
        if (!container) {
            container = document.createElement('div');
            container.id = 'admin-toast-container';
            container.style.cssText = 'position:fixed;top:80px;right:24px;z-index:9999;max-width:400px;';
            document.body.appendChild(container);
        }
        
        const toast = document.createElement('div');
        toast.className = `alert alert-${type} alert-dismissible fade show shadow-lg`;
        toast.style.cssText = 'margin-bottom:12px;animation:slideInRight 0.3s ease-out;';
        toast.innerHTML = `
            <div class="d-flex align-items-center">
                <i class="bi bi-${this.getIconForType(type)} me-2 fs-5"></i>
                <div class="flex-grow-1">${message}</div>
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            </div>
        `;
        
        container.appendChild(toast);
        
        setTimeout(() => {
            toast.classList.remove('show');
            setTimeout(() => toast.remove(), 300);
        }, 4000);
    }
    
    getIconForType(type) {
        const icons = {
            'success': 'check-circle-fill',
            'danger': 'exclamation-triangle-fill',
            'warning': 'exclamation-circle-fill',
            'info': 'info-circle-fill'
        };
        return icons[type] || 'info-circle-fill';
    }
    
    showLoading(elementId, message = 'Loading...') {
        const el = document.getElementById(elementId);
        if (el) {
            el.innerHTML = `
                <div class="text-center py-5">
                    <div class="spinner-border text-primary mb-3" role="status">
                        <span class="visually-hidden">Loading...</span>
                    </div>
                    <div class="text-muted">${message}</div>
                </div>
            `;
        }
    }
    
    showError(elementId, message) {
        const el = document.getElementById(elementId);
        if (el) {
            el.innerHTML = `
                <div class="alert alert-danger d-flex align-items-center" role="alert">
                    <i class="bi bi-exclamation-triangle-fill me-2 fs-4"></i>
                    <div>${message}</div>
                </div>
            `;
        }
    }
    
    // ==================== Company Context ====================
    
    async loadCompanyContext() {
        if (this.isDisabled) {
            return;
        }
        try {
            console.log('🏢 Loading company context...');
            const response = await fetch('/api/categories/');
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            
            if (data.success && data.company) {
                this.currentCompany = data.company;
                console.log('✅ Company context loaded:', this.currentCompany.name);
                this.updateCompanyDisplay();
            } else {
                console.warn('⚠️ Company context not available in response');
            }
        } catch (error) {
            console.error('❌ Failed to load company context:', error);
        }
    }
    
    updateCompanyDisplay() {
        const companyBadges = document.querySelectorAll('.company-context-badge');
        companyBadges.forEach(badge => {
            if (this.currentCompany) {
                badge.innerHTML = `
                    <i class="bi bi-building me-1"></i>
                    ${this.currentCompany.name}
                `;
                badge.classList.remove('d-none');
            }
        });
    }
    
    // ==================== Enhanced Category Management ====================
    
    async loadCategoriesWithAnalytics() {
        console.log('📊 Loading categories with analytics...');
        this.showLoading('enhanced-categories-list', 'Loading categories...');
        
        try {
            const response = await fetch('/api/categories/');
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            console.log('📦 Categories data received:', data);
            
            if (data.success) {
                this.categories = data.categories;
                this.currentCompany = data.company;
                console.log(`✅ Loaded ${this.categories.length} categories`);
                this.renderCategoriesTable();
                this.updateCategoryStats();
            } else {
                console.error('❌ API returned error:', data.error);
                this.showError('enhanced-categories-list', data.error || 'Failed to load categories');
            }
        } catch (error) {
            console.error('❌ Network error loading categories:', error);
            this.showError('enhanced-categories-list', 'Network error. Please try again.');
        }
    }
    
    renderCategoriesTable() {
        const container = document.getElementById('enhanced-categories-list');
        if (!container) return;
        
        if (this.categories.length === 0) {
            container.innerHTML = `
                <div class="text-center py-5">
                    <i class="bi bi-folder-x fs-1 text-muted mb-3 d-block"></i>
                    <h5 class="text-muted">No categories yet</h5>
                    <p class="text-muted">Create your first category to organize assets</p>
                    <button class="btn btn-primary" onclick="if(window.wizard) { adminTools.closeCategoryManagementModal(); wizard.openWizard(); } else console.error('Wizard not loaded');">
                        <i class="bi bi-magic me-2"></i>Create Category (Wizard)
                    </button>
                </div>
            `;
            return;
        }
        
        const tableHTML = `
            <div class="table-responsive">
                <table class="table table-hover align-middle">
                    <thead class="table-light">
                        <tr>
                            <th style="width: 40%;">
                                <i class="bi bi-folder me-2"></i>Category Name
                            </th>
                            <th style="width: 20%;" class="text-center">
                                <i class="bi bi-box me-2"></i>Assets
                            </th>
                            <th style="width: 20%;" class="text-center">
                                <i class="bi bi-list-check me-2"></i>Fields
                            </th>
                            <th style="width: 20%;" class="text-end">Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${this.categories.map(cat => this.renderCategoryRow(cat)).join('')}
                    </tbody>
                </table>
            </div>
        `;
        
        container.innerHTML = tableHTML;
    }
    
    renderCategoryRow(category) {
        const assetBadgeClass = category.asset_count > 0 ? 'bg-success' : 'bg-secondary';
        const fieldBadgeClass = category.field_count > 0 ? 'bg-info' : 'bg-secondary';
        
        return `
            <tr>
                <td>
                    <div class="d-flex align-items-center">
                        <div class="category-icon me-3">
                            <i class="bi bi-folder-fill text-primary fs-4"></i>
                        </div>
                        <div>
                            <div class="fw-semibold">${this.escapeHtml(category.name)}</div>
                            <small class="text-muted">ID: ${category.id}</small>
                        </div>
                    </div>
                </td>
                <td class="text-center">
                    <span class="badge ${assetBadgeClass} fs-6 px-3 py-2">
                        ${category.asset_count}
                    </span>
                </td>
                <td class="text-center">
                    <span class="badge ${fieldBadgeClass} fs-6 px-3 py-2">
                        ${category.field_count}
                    </span>
                </td>
                <td class="text-end">
                    <div class="btn-group" role="group">
                        <button class="btn btn-sm btn-outline-primary category-action-btn" 
                                data-action="manage-fields"
                                data-category-id="${category.id}"
                                data-category-name="${this.escapeHtml(category.name)}"
                                title="Manage Fields">
                            <i class="bi bi-list-check"></i>
                        </button>
                        <button class="btn btn-sm btn-outline-info category-action-btn" 
                                data-action="view-analytics"
                                data-category-id="${category.id}"
                                title="View Analytics">
                            <i class="bi bi-graph-up"></i>
                        </button>
                        <button class="btn btn-sm btn-outline-danger category-action-btn" 
                                data-action="delete"
                                data-category-id="${category.id}"
                                data-category-name="${this.escapeHtml(category.name)}"
                                title="Delete Category"
                                ${category.asset_count > 0 ? 'disabled' : ''}>
                            <i class="bi bi-trash"></i>
                        </button>
                    </div>
                </td>
            </tr>
        `;
    }
    
    updateCategoryStats() {
        if (!this.currentCompany) return;
        
        const statsHTML = `
            <div class="row g-3 mb-4">
                <div class="col-md-3">
                    <div class="card border-0 shadow-sm h-100">
                        <div class="card-body">
                            <div class="d-flex align-items-center">
                                <div class="flex-shrink-0">
                                    <div class="stat-icon bg-primary bg-opacity-10 text-primary rounded-3 p-3">
                                        <i class="bi bi-folder-fill fs-3"></i>
                                    </div>
                                </div>
                                <div class="flex-grow-1 ms-3">
                                    <div class="text-muted small">Total Categories</div>
                                    <div class="fs-3 fw-bold">${this.currentCompany.total_categories}</div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="card border-0 shadow-sm h-100">
                        <div class="card-body">
                            <div class="d-flex align-items-center">
                                <div class="flex-shrink-0">
                                    <div class="stat-icon bg-success bg-opacity-10 text-success rounded-3 p-3">
                                        <i class="bi bi-box-seam fs-3"></i>
                                    </div>
                                </div>
                                <div class="flex-grow-1 ms-3">
                                    <div class="text-muted small">Total Assets</div>
                                    <div class="fs-3 fw-bold">${this.currentCompany.total_assets}</div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="card border-0 shadow-sm h-100">
                        <div class="card-body">
                            <div class="d-flex align-items-center">
                                <div class="flex-shrink-0">
                                    <div class="stat-icon bg-info bg-opacity-10 text-info rounded-3 p-3">
                                        <i class="bi bi-list-check fs-3"></i>
                                    </div>
                                </div>
                                <div class="flex-grow-1 ms-3">
                                    <div class="text-muted small">Dynamic Fields</div>
                                    <div class="fs-3 fw-bold">${this.currentCompany.total_fields}</div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="card border-0 shadow-sm h-100">
                        <div class="card-body">
                            <div class="d-flex align-items-center">
                                <div class="flex-shrink-0">
                                    <div class="stat-icon bg-warning bg-opacity-10 text-warning rounded-3 p-3">
                                        <i class="bi bi-building fs-3"></i>
                                    </div>
                                </div>
                                <div class="flex-grow-1 ms-3">
                                    <div class="text-muted small">Company</div>
                                    <div class="fs-6 fw-bold text-truncate" title="${this.escapeHtml(this.currentCompany.name)}">
                                        ${this.escapeHtml(this.currentCompany.name)}
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        const statsContainer = document.getElementById('category-stats');
        if (statsContainer) {
            statsContainer.innerHTML = statsHTML;
        }
    }
    
    // ==================== Enhanced Dynamic Field Management ====================
    
    async manageFields(categoryId, categoryName) {
        console.log(`🔧 Managing fields for category: ${categoryName} (ID: ${categoryId})`);
        this.currentCategory = { id: categoryId, name: categoryName };
        
        // Hide Category Management modal if it's open
        const categoryManagementModal = document.getElementById('enhancedCategoryManagementModal');
        if (categoryManagementModal && categoryManagementModal.classList.contains('show')) {
            const bsModal = bootstrap.Modal.getInstance(categoryManagementModal);
            if (bsModal) {
                console.log('🔽 Hiding Category Management Modal temporarily');
                bsModal.hide();
                this.shouldReopenCategoryManagement = true;
            }
        }
        
        // Open Fields modal
        const modal = document.getElementById('enhancedFieldsModal');
        if (modal) {
            modal.classList.add('active');
            const nameElement = document.getElementById('enhanced-fields-category-name');
            if (nameElement) {
                nameElement.textContent = categoryName;
            }
            console.log('✅ Fields Modal opened');
            
            await this.loadFieldsWithAnalytics(categoryId);
        }
    }
    
    async loadFieldsWithAnalytics(categoryId) {
        this.showLoading('enhanced-fields-list', 'Loading fields...');
        
        try {
            const response = await fetch(`/api/category/${categoryId}/fields/`);
            const data = await response.json();
            
            if (data.success) {
                this.fields = data.fields;
                this.renderFieldsTable(data.category);
            } else {
                this.showError('enhanced-fields-list', data.error || 'Failed to load fields');
            }
        } catch (error) {
            this.showError('enhanced-fields-list', 'Network error. Please try again.');
        }
    }
    
    renderFieldsTable(categoryInfo) {
        const container = document.getElementById('enhanced-fields-list');
        if (!container) return;
        
        // Update category info banner
        const infoBanner = document.getElementById('field-category-info');
        if (infoBanner && categoryInfo) {
            infoBanner.innerHTML = `
                <div class="alert alert-info d-flex align-items-center mb-3">
                    <i class="bi bi-info-circle-fill me-2 fs-5"></i>
                    <div>
                        <strong>${categoryInfo.name}</strong> has 
                        <strong>${categoryInfo.total_assets}</strong> asset(s) and 
                        <strong>${this.fields.length}</strong> dynamic field(s)
                    </div>
                </div>
            `;
        }
        
        if (this.fields.length === 0) {
            container.innerHTML = `
                <div class="text-center py-5">
                    <i class="bi bi-list-ul fs-1 text-muted mb-3 d-block"></i>
                    <h5 class="text-muted">No fields defined</h5>
                    <p class="text-muted">Add dynamic fields to customize this category</p>
                    <button class="btn btn-primary" onclick="adminTools.openAddFieldForm()">
                        <i class="bi bi-plus-lg me-2"></i>Add Field
                    </button>
                </div>
            `;
            return;
        }
        
        const tableHTML = `
            <div class="table-responsive">
                <table class="table table-hover align-middle">
                    <thead class="table-light">
                        <tr>
                            <th style="width: 25%;">Field Label</th>
                            <th style="width: 20%;">Key</th>
                            <th style="width: 15%;">Type</th>
                            <th style="width: 10%;" class="text-center">Required</th>
                            <th style="width: 15%;" class="text-center">Usage</th>
                            <th style="width: 15%;" class="text-end">Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${this.fields.map(field => this.renderFieldRow(field)).join('')}
                    </tbody>
                </table>
            </div>
        `;
        
        container.innerHTML = tableHTML;
    }
    
    renderFieldRow(field) {
        const typeIcons = {
            'text': 'bi-fonts',
            'number': 'bi-123',
            'date': 'bi-calendar-date'
        };
        
        const typeColors = {
            'text': 'primary',
            'number': 'success',
            'date': 'info'
        };
        
        const usageColor = field.usage_percentage >= 75 ? 'success' : 
                          field.usage_percentage >= 50 ? 'warning' : 'danger';
        
        return `
            <tr>
                <td>
                    <div class="fw-semibold">${this.escapeHtml(field.label)}</div>
                </td>
                <td>
                    <code class="text-muted">${this.escapeHtml(field.key)}</code>
                </td>
                <td>
                    <span class="badge bg-${typeColors[field.type]} bg-opacity-10 text-${typeColors[field.type]}">
                        <i class="bi ${typeIcons[field.type]} me-1"></i>
                        ${field.type}
                    </span>
                </td>
                <td class="text-center">
                    ${field.required ? 
                        '<span class="badge bg-danger"><i class="bi bi-asterisk"></i> Yes</span>' : 
                        '<span class="badge bg-secondary">No</span>'}
                </td>
                <td class="text-center">
                    <div class="d-flex align-items-center justify-content-center">
                        <div class="progress flex-grow-1 me-2" style="height: 8px; max-width: 80px;">
                            <div class="progress-bar bg-${usageColor}" 
                                 style="width: ${field.usage_percentage}%"></div>
                        </div>
                        <small class="text-muted">${field.usage_percentage}%</small>
                    </div>
                    <small class="text-muted d-block">${field.usage_count} assets</small>
                </td>
                <td class="text-end">
                    <div class="btn-group" role="group">
                        <button class="btn btn-sm btn-outline-primary" 
                                onclick="adminTools.editField(${field.id})"
                                title="Edit Field">
                            <i class="bi bi-pencil"></i>
                        </button>
                        <button class="btn btn-sm btn-outline-danger" 
                                onclick="adminTools.deleteField(${field.id}, '${this.escapeHtml(field.label)}')"
                                title="Delete Field">
                            <i class="bi bi-trash"></i>
                        </button>
                    </div>
                </td>
            </tr>
        `;
    }
    
    // ==================== Modal Management ====================
    
    openCreateCategoryModal() {
        console.log('🧙 Redirecting to Category Wizard...');
        
        // Close the Category Management modal if it's open
        this.closeCategoryManagementModal();
        
        // Open the wizard instead of legacy modal
        if (window.wizard) {
            wizard.openWizard();
            console.log('✅ Category Wizard opened');
        } else {
            console.error('❌ Category Wizard not loaded');
            alert('Category Wizard is not available. Please refresh the page.');
        }
    }
    
    closeEnhancedCategoryModal() {
        console.log('🔽 Closing Create Category Modal...');
        const modal = document.getElementById('enhancedCategoryModal');
        if (modal) {
            modal.classList.remove('active');
        }
        
        // Reopen Category Management modal if it was open before
        if (this.shouldReopenCategoryManagement) {
            console.log('🔼 Reopening Category Management Modal');
            this.shouldReopenCategoryManagement = false;
            setTimeout(() => {
                this.openCategoryManagementModal();
            }, 300); // Small delay for smooth transition
        }
    }
    
    closeEnhancedFieldsModal() {
        console.log('🔽 Closing Fields Modal...');
        const modal = document.getElementById('enhancedFieldsModal');
        if (modal) {
            modal.classList.remove('active');
            this.currentCategory = null;
            this.fields = [];
        }
        
        // Reopen Category Management modal if it was open before
        if (this.shouldReopenCategoryManagement) {
            console.log('🔼 Reopening Category Management Modal');
            this.shouldReopenCategoryManagement = false;
            setTimeout(() => {
                this.openCategoryManagementModal();
            }, 300); // Small delay for smooth transition
        }
    }
    
    openAddFieldForm() {
        const form = document.getElementById('enhanced-field-form-section');
        if (form) {
            form.classList.remove('d-none');
            document.getElementById('enhanced-field-form').reset();
            document.getElementById('enhanced-field-title').textContent = 'Add New Field';
            document.getElementById('enhanced-field-key').disabled = false;
            this.editingField = null;
        }
    }
    
    closeFieldForm() {
        const form = document.getElementById('enhanced-field-form-section');
        if (form) {
            form.classList.add('d-none');
            document.getElementById('enhanced-field-form').reset();
            this.editingField = null;
        }
    }
    
    // ==================== CRUD Operations ====================
    
    async createCategory(formData) {
        try {
            const response = await fetch('/api/create-category/', {
                method: 'POST',
                headers: {
                    'X-CSRFToken': this.getCSRFToken(),
                    'Content-Type': 'application/x-www-form-urlencoded',
                },
                body: new URLSearchParams(formData)
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.showToast('Category created successfully!', 'success');
                this.closeEnhancedCategoryModal();
                await this.loadCategoriesWithAnalytics();
            } else {
                document.getElementById('enhanced-category-feedback').innerHTML = 
                    `<div class="alert alert-danger">${data.error}</div>`;
            }
        } catch (error) {
            document.getElementById('enhanced-category-feedback').innerHTML = 
                `<div class="alert alert-danger">Network error. Please try again.</div>`;
        }
    }
    
    async deleteCategory(categoryId, categoryName) {
        if (!confirm(`Are you sure you want to delete "${categoryName}"?\n\nThis action cannot be undone.`)) {
            return;
        }
        
        console.log(`🗑️ Deleting category: ${categoryName} (ID: ${categoryId})`);
        
        try {
            const response = await fetch(`/api/category/${categoryId}/delete/`, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': this.getCSRFToken(),
                    'Content-Type': 'application/json',
                },
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.showToast(data.message || 'Category deleted successfully!', 'success');
                await this.loadCategoriesWithAnalytics();
            } else {
                this.showToast(data.error || 'Failed to delete category', 'danger');
            }
        } catch (error) {
            console.error('❌ Error deleting category:', error);
            this.showToast('Network error. Please try again.', 'danger');
        }
    }
    
    async createField(formData) {
        if (!this.currentCategory) return;
        
        try {
            const response = await fetch(`/api/category/${this.currentCategory.id}/fields/create/`, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': this.getCSRFToken(),
                    'Content-Type': 'application/x-www-form-urlencoded',
                },
                body: new URLSearchParams(formData)
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.showToast('Field created successfully!', 'success');
                this.closeFieldForm();
                await this.loadFieldsWithAnalytics(this.currentCategory.id);
            } else {
                document.getElementById('enhanced-field-feedback').innerHTML = 
                    `<div class="alert alert-danger">${data.error}</div>`;
            }
        } catch (error) {
            document.getElementById('enhanced-field-feedback').innerHTML = 
                `<div class="alert alert-danger">Network error. Please try again.</div>`;
        }
    }
    
    async editField(fieldId) {
        const field = this.fields.find(f => f.id === fieldId);
        if (!field) return;
        
        this.editingField = field;
        this.openAddFieldForm();
        
        document.getElementById('enhanced-field-title').textContent = 'Edit Field';
        document.getElementById('enhanced-field-key').value = field.key;
        document.getElementById('enhanced-field-key').disabled = true;
        document.getElementById('enhanced-field-label').value = field.label;
        document.getElementById('enhanced-field-type').value = field.type;
        document.getElementById('enhanced-field-required').checked = field.required;
    }
    
    async updateField(formData) {
        if (!this.editingField) return;
        
        try {
            const response = await fetch(`/api/field/${this.editingField.id}/update/`, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': this.getCSRFToken(),
                    'Content-Type': 'application/x-www-form-urlencoded',
                },
                body: new URLSearchParams(formData)
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.showToast('Field updated successfully!', 'success');
                this.closeFieldForm();
                await this.loadFieldsWithAnalytics(this.currentCategory.id);
            } else {
                document.getElementById('enhanced-field-feedback').innerHTML = 
                    `<div class="alert alert-danger">${data.error}</div>`;
            }
        } catch (error) {
            document.getElementById('enhanced-field-feedback').innerHTML = 
                `<div class="alert alert-danger">Network error. Please try again.</div>`;
        }
    }
    
    async deleteField(fieldId, fieldLabel) {
        if (!confirm(`Are you sure you want to delete "${fieldLabel}"?\n\nThis action cannot be undone.`)) {
            return;
        }
        
        try {
            const response = await fetch(`/api/field/${fieldId}/delete/`, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': this.getCSRFToken(),
                }
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.showToast('Field deleted successfully!', 'success');
                await this.loadFieldsWithAnalytics(this.currentCategory.id);
            } else {
                this.showToast(data.error || 'Failed to delete field', 'danger');
            }
        } catch (error) {
            this.showToast('Network error. Please try again.', 'danger');
        }
    }
    
    async viewCategoryAnalytics(categoryId) {
        console.log(`📊 Loading analytics for category ID: ${categoryId}`);
        
        try {
            const response = await fetch(`/api/category/${categoryId}/analytics/`);
            const data = await response.json();
            
            if (data.success) {
                this.showAnalyticsModal(data.analytics);
            } else {
                this.showToast(data.error || 'Failed to load analytics', 'danger');
            }
        } catch (error) {
            console.error('❌ Error loading analytics:', error);
            this.showToast('Network error. Please try again.', 'danger');
        }
    }
    
    showAnalyticsModal(analytics) {
        console.log('📈 Displaying analytics modal', analytics);
        
        // Hide Category Management modal
        const categoryManagementModal = document.getElementById('enhancedCategoryManagementModal');
        if (categoryManagementModal && categoryManagementModal.classList.contains('show')) {
            const bsModal = bootstrap.Modal.getInstance(categoryManagementModal);
            if (bsModal) {
                bsModal.hide();
                this.shouldReopenCategoryManagement = true;
            }
        }
        
        // Open Analytics modal
        const modal = document.getElementById('enhancedAnalyticsModal');
        if (modal) {
            modal.classList.add('active');
            this.renderAnalytics(analytics);
        }
    }
    
    closeAnalyticsModal() {
        console.log('🔽 Closing Analytics Modal...');
        const modal = document.getElementById('enhancedAnalyticsModal');
        if (modal) {
            modal.classList.remove('active');
        }
        
        // Reopen Category Management modal if it was open before
        if (this.shouldReopenCategoryManagement) {
            console.log('🔼 Reopening Category Management Modal');
            this.shouldReopenCategoryManagement = false;
            setTimeout(() => {
                this.openCategoryManagementModal();
            }, 300);
        }
    }
    
    renderAnalytics(analytics) {
        const container = document.getElementById('analytics-content');
        if (!container) return;
        
        const { category, summary, status_distribution, branch_distribution, field_statistics, recent_activity } = analytics;
        
        // Status chart colors
        const statusColors = {
            'ACTIVE': '#28a745',
            'IN_MAINTENANCE': '#ffc107',
            'RETIRED': '#6c757d',
            'LOST': '#dc3545',
            'DELETED': '#343a40'
        };
        
        const html = `
            <!-- Category Header -->
            <div class="alert alert-primary d-flex align-items-center mb-4">
                <i class="bi bi-folder-fill fs-3 me-3"></i>
                <div>
                    <h5 class="mb-0 fw-bold">${this.escapeHtml(category.name)}</h5>
                    <small>${this.escapeHtml(category.description) || 'No description'}</small>
                </div>
            </div>
            
            <!-- Summary Cards -->
            <div class="row g-3 mb-4">
                <div class="col-md-3">
                    <div class="card border-0 shadow-sm h-100">
                        <div class="card-body text-center">
                            <i class="bi bi-box fs-1 text-primary mb-2"></i>
                            <h3 class="fw-bold mb-0">${summary.total_assets}</h3>
                            <small class="text-muted">Total Assets</small>
                        </div>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="card border-0 shadow-sm h-100">
                        <div class="card-body text-center">
                            <i class="bi bi-list-check fs-1 text-success mb-2"></i>
                            <h3 class="fw-bold mb-0">${summary.total_fields}</h3>
                            <small class="text-muted">Dynamic Fields</small>
                        </div>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="card border-0 shadow-sm h-100">
                        <div class="card-body text-center">
                            <i class="bi bi-clock-history fs-1 text-info mb-2"></i>
                            <h3 class="fw-bold mb-0">${summary.recent_additions}</h3>
                            <small class="text-muted">Added (30 days)</small>
                        </div>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="card border-0 shadow-sm h-100">
                        <div class="card-body text-center">
                            <i class="bi bi-building fs-1 text-warning mb-2"></i>
                            <h3 class="fw-bold mb-0">${summary.branches_using}</h3>
                            <small class="text-muted">Branches</small>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- Status Distribution -->
            <div class="card border-0 shadow-sm mb-4">
                <div class="card-header bg-white">
                    <h6 class="mb-0 fw-bold"><i class="bi bi-pie-chart me-2"></i>Status Distribution</h6>
                </div>
                <div class="card-body">
                    ${status_distribution.length > 0 ? `
                        <div class="row g-3">
                            ${status_distribution.map(item => `
                                <div class="col-md-4">
                                    <div class="d-flex align-items-center">
                                        <div class="flex-shrink-0">
                                            <div style="width: 40px; height: 40px; background: ${statusColors[item.status] || '#6c757d'}; border-radius: 8px;" class="d-flex align-items-center justify-content-center text-white fw-bold">
                                                ${item.count}
                                            </div>
                                        </div>
                                        <div class="flex-grow-1 ms-3">
                                            <div class="fw-semibold">${item.status.replace('_', ' ')}</div>
                                            <div class="progress" style="height: 6px;">
                                                <div class="progress-bar" style="width: ${(item.count / summary.total_assets * 100)}%; background: ${statusColors[item.status] || '#6c757d'};"></div>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            `).join('')}
                        </div>
                    ` : '<p class="text-muted mb-0">No assets in this category</p>'}
                </div>
            </div>
            
            <!-- Branch Distribution -->
            <div class="card border-0 shadow-sm mb-4">
                <div class="card-header bg-white">
                    <h6 class="mb-0 fw-bold"><i class="bi bi-building me-2"></i>Top Branches</h6>
                </div>
                <div class="card-body">
                    ${branch_distribution.length > 0 ? `
                        ${branch_distribution.map(item => `
                            <div class="d-flex align-items-center mb-3">
                                <div class="flex-grow-1">
                                    <div class="d-flex justify-content-between mb-1">
                                        <span class="fw-semibold">${this.escapeHtml(item.branch__name || 'Head Office')}</span>
                                        <span class="badge bg-primary">${item.count}</span>
                                    </div>
                                    <div class="progress" style="height: 8px;">
                                        <div class="progress-bar bg-primary" style="width: ${(item.count / summary.total_assets * 100)}%;"></div>
                                    </div>
                                </div>
                            </div>
                        `).join('')}
                    ` : '<p class="text-muted mb-0">No branch data available</p>'}
                </div>
            </div>
            
            <!-- Field Statistics -->
            <div class="card border-0 shadow-sm mb-4">
                <div class="card-header bg-white">
                    <h6 class="mb-0 fw-bold"><i class="bi bi-bar-chart me-2"></i>Field Usage Statistics</h6>
                </div>
                <div class="card-body">
                    ${field_statistics.length > 0 ? `
                        <div class="table-responsive">
                            <table class="table table-sm table-hover">
                                <thead>
                                    <tr>
                                        <th>Field</th>
                                        <th>Type</th>
                                        <th>Required</th>
                                        <th class="text-end">Usage</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    ${field_statistics.map(field => `
                                        <tr>
                                            <td>
                                                <div class="fw-semibold">${this.escapeHtml(field.label)}</div>
                                                <small class="text-muted">${this.escapeHtml(field.key)}</small>
                                            </td>
                                            <td><span class="badge bg-secondary">${field.type}</span></td>
                                            <td>${field.required ? '<span class="badge bg-danger">Required</span>' : '<span class="badge bg-secondary">Optional</span>'}</td>
                                            <td class="text-end">
                                                <div class="d-flex align-items-center justify-content-end">
                                                    <small class="me-2">${field.filled_count}/${summary.total_assets}</small>
                                                    <div class="progress" style="width: 100px; height: 6px;">
                                                        <div class="progress-bar ${field.usage_percentage >= 75 ? 'bg-success' : field.usage_percentage >= 50 ? 'bg-warning' : 'bg-danger'}" 
                                                             style="width: ${field.usage_percentage}%;"></div>
                                                    </div>
                                                    <small class="ms-2">${field.usage_percentage}%</small>
                                                </div>
                                            </td>
                                        </tr>
                                    `).join('')}
                                </tbody>
                            </table>
                        </div>
                    ` : '<p class="text-muted mb-0">No fields defined for this category</p>'}
                </div>
            </div>
            
            <!-- Recent Activity -->
            <div class="card border-0 shadow-sm">
                <div class="card-header bg-white">
                    <h6 class="mb-0 fw-bold"><i class="bi bi-clock-history me-2"></i>Recent Activity</h6>
                </div>
                <div class="card-body">
                    ${recent_activity.length > 0 ? `
                        <div class="list-group list-group-flush">
                            ${recent_activity.map(event => `
                                <div class="list-group-item border-0 px-0">
                                    <div class="d-flex justify-content-between align-items-start">
                                        <div>
                                            <span class="badge bg-info me-2">${event.action}</span>
                                            <small class="text-muted">${event.details}</small>
                                        </div>
                                        <small class="text-muted">${new Date(event.timestamp).toLocaleDateString()}</small>
                                    </div>
                                    <small class="text-muted">by ${event.user__username}</small>
                                </div>
                            `).join('')}
                        </div>
                    ` : '<p class="text-muted mb-0">No recent activity</p>'}
                </div>
            </div>
        `;
        
        container.innerHTML = html;
    }
    
    // ==================== Modal Management ====================
    
    openCategoryManagementModal() {
        console.log('📊 Opening Category Management Modal...');
        const modalElement = document.getElementById('enhancedCategoryManagementModal');
        
        // Debug logging
        console.log('🔍 Modal element found:', !!modalElement);
        console.log('🔍 Bootstrap available:', typeof bootstrap !== 'undefined');
        
        if (!modalElement) {
            console.error('❌ Modal element #enhancedCategoryManagementModal not found in DOM');
            console.log('🔍 Available modals:', Array.from(document.querySelectorAll('.modal')).map(m => m.id));
            return;
        }
        
        if (typeof bootstrap === 'undefined') {
            console.error('❌ Bootstrap library not loaded');
            return;
        }
        
        try {
            const modal = new bootstrap.Modal(modalElement, {
                backdrop: true,
                keyboard: true,
                focus: true
            });
            console.log('✅ Modal instance created successfully');
            modal.show();
            console.log('✅ Modal show() called');
            this.loadCategoriesWithAnalytics();
        } catch (error) {
            console.error('❌ Error creating/showing modal:', error);
        }
    }
    
    closeCategoryManagementModal() {
        console.log('🔽 Closing Category Management Modal...');
        const modalElement = document.getElementById('enhancedCategoryManagementModal');
        
        if (!modalElement) {
            console.warn('⚠️ Modal element not found');
            return;
        }
        
        try {
            const modalInstance = bootstrap.Modal.getInstance(modalElement);
            if (modalInstance) {
                modalInstance.hide();
                console.log('✅ Modal closed successfully');
            } else {
                // If no instance, just remove classes manually
                modalElement.classList.remove('show');
                const backdrop = document.querySelector('.modal-backdrop');
                if (backdrop) backdrop.remove();
                document.body.classList.remove('modal-open');
                document.body.style.removeProperty('overflow');
                document.body.style.removeProperty('padding-right');
                console.log('✅ Modal closed manually');
            }
        } catch (error) {
            console.error('❌ Error closing modal:', error);
        }
    }
    
    // ==================== Event Binding ====================
    
    bindEvents() {
        // Bootstrap modal event listeners (for when opened via data-bs-toggle)
        const categoryManagementModal = document.getElementById('enhancedCategoryManagementModal');
        if (categoryManagementModal) {
            categoryManagementModal.addEventListener('show.bs.modal', () => {
                console.log('📊 Category Management Modal opening via Bootstrap...');
                this.loadCategoriesWithAnalytics();
            });
        }
        
        // Event delegation for category action buttons
        document.addEventListener('click', (e) => {
            const btn = e.target.closest('.category-action-btn');
            if (!btn) return;
            
            // Prevent action if button is disabled
            if (btn.disabled) {
                console.log('⚠️ Button is disabled');
                return;
            }
            
            const action = btn.dataset.action;
            const categoryId = parseInt(btn.dataset.categoryId);
            const categoryName = btn.dataset.categoryName;
            
            console.log(`🎯 Category action: ${action}, ID: ${categoryId}, Name: ${categoryName}`);
            
            switch (action) {
                case 'manage-fields':
                    this.manageFields(categoryId, categoryName);
                    break;
                case 'view-analytics':
                    this.viewCategoryAnalytics(categoryId);
                    break;
                case 'delete':
                    this.deleteCategory(categoryId, categoryName);
                    break;
                default:
                    console.warn('Unknown action:', action);
            }
        });
        
        // Category form submission
        document.addEventListener('submit', (e) => {
            if (e.target.id === 'enhanced-category-form') {
                e.preventDefault();
                const formData = new FormData(e.target);
                this.createCategory(formData);
            } else if (e.target.id === 'enhanced-field-form') {
                e.preventDefault();
                const formData = new FormData(e.target);
                
                if (this.editingField) {
                    this.updateField(formData);
                } else {
                    this.createField(formData);
                }
            }
        });
        
        // Modal close on backdrop click
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('custom-modal-overlay')) {
                if (e.target.id === 'enhancedCategoryModal') {
                    this.closeEnhancedCategoryModal();
                } else if (e.target.id === 'enhancedFieldsModal') {
                    this.closeEnhancedFieldsModal();
                }
            }
        });
        
        // ESC key to close modals
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                this.closeEnhancedCategoryModal();
                this.closeEnhancedFieldsModal();
            }
        });
    }
    
    // ==================== Utility ====================
    
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    // ==================== Wizard Integration ====================
    
    openWizard() {
        if (window.wizard) {
            wizard.openWizard();
        } else {
            console.error('❌ Category Wizard not loaded');
        }
    }
    
    closeWizard() {
        if (window.wizard) {
            wizard.closeWizard();
        }
    }
    
    selectWizardPath(path) {
        if (window.wizard) {
            wizard.selectWizardPath(path);
        }
    }
    
    wizardNextStep() {
        if (window.wizard) {
            wizard.wizardNextStep();
        }
    }
    
    wizardPrevStep() {
        if (window.wizard) {
            wizard.wizardPrevStep();
        }
    }
    
    wizardFinish() {
        if (window.wizard) {
            wizard.wizardFinish();
        }
    }
    
    addWizardField() {
        if (window.wizard) {
            wizard.addWizardField();
        }
    }
}

// Initialize on DOM ready
let adminTools;
document.addEventListener('DOMContentLoaded', () => {
    console.log('🚀 Initializing Admin Tools Manager...');
    adminTools = new AdminToolsManager();
    if (adminTools && adminTools.isDisabled) {
        console.log('ℹ️ Admin Tools Manager disabled for role:', adminTools.userRole || 'unknown');
        return;
    }
    console.log('✅ Admin Tools Manager initialized successfully');
});
