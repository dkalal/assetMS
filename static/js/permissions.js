/**
 * Enterprise Permission Management System
 * Optimized for performance, security, and UX
 */

class PermissionManager {
    constructor() {
        this.usersData = { page: 1, numPages: 1, users: [], total: 0 };
        this.searchTimeout = null;
        this.currentEditUserId = null;
        this.isLoading = false;
        
        // Cache DOM elements for performance
        this.elements = {
            modal: document.getElementById('permissionsModalCustom'),
            openBtn: document.getElementById('openPermissionsModal'),
            closeBtn: document.getElementById('closePermissionsModal'),
            closeBtnFooter: document.getElementById('closePermissionsModalBtn'),
            feedback: document.getElementById('permissions-feedback'),
            usersList: document.getElementById('users-list'),
            userSearch: document.getElementById('user-search'),
            roleSelect: document.getElementById('role-select'),
            rolePermissions: document.getElementById('role-permissions'),
            selectedRoleName: document.getElementById('selected-role-name'),
            usersPrev: document.getElementById('users-prev'),
            usersNext: document.getElementById('users-next'),
            usersPageInfo: document.getElementById('users-page-info'),
            editModal: document.getElementById('editUserRoleModal'),
            editForm: document.getElementById('edit-user-role-form'),
            editUserInfo: document.getElementById('edit-user-info'),
            editRoleSelect: document.getElementById('edit-user-role-select'),
            editFeedback: document.getElementById('edit-role-feedback')
        };
        
        this.init();
    }
    
    init() {
        this.bindEvents();
        this.setupPermissionMatrix();
    }
    
    bindEvents() {
        // Modal controls
        this.elements.openBtn?.addEventListener('click', () => this.openModal());
        this.elements.closeBtn?.addEventListener('click', () => this.closeModal());
        this.elements.closeBtnFooter?.addEventListener('click', () => this.closeModal());
        
        // Search functionality with debouncing
        this.elements.userSearch?.addEventListener('input', (e) => {
            clearTimeout(this.searchTimeout);
            this.searchTimeout = setTimeout(() => {
                this.loadUsers(1, e.target.value.trim());
            }, 300);
        });
        
        // Role selection
        this.elements.roleSelect?.addEventListener('change', (e) => {
            if (e.target.value) {
                this.showRolePermissions(e.target.value);
            } else {
                this.elements.rolePermissions?.classList.add('d-none');
            }
        });
        
        // Pagination
        this.elements.usersPrev?.addEventListener('click', () => this.previousPage());
        this.elements.usersNext?.addEventListener('click', () => this.nextPage());
        
        // Modal backdrop and ESC key
        this.elements.modal?.addEventListener('click', (e) => {
            if (e.target === this.elements.modal) this.closeModal();
        });
        
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && this.elements.modal?.classList.contains('active')) {
                this.closeModal();
            }
        });
        
        // Edit user role form
        this.elements.editForm?.addEventListener('submit', (e) => this.handleRoleUpdate(e));
        document.getElementById('closeEditUserRoleModal')?.addEventListener('click', () => this.closeEditModal());
        document.getElementById('cancelEditUserRole')?.addEventListener('click', () => this.closeEditModal());
    }
    
    setupPermissionMatrix() {
        this.permissions = {
            admin: [
                'perm-view-assets', 'perm-create-assets', 'perm-edit-assets', 
                'perm-delete-assets', 'perm-manage-users', 'perm-view-reports', 
                'perm-export-data', 'perm-system-admin'
            ],
            manager: [
                'perm-view-assets', 'perm-create-assets', 'perm-edit-assets', 
                'perm-view-reports', 'perm-export-data'
            ],
            user: ['perm-view-assets']
        };
    }
    
    async openModal() {
        if (this.isLoading) return;
        
        this.clearFeedback();
        this.elements.modal?.classList.add('active');
        this.elements.modal?.focus();
        
        // Reset role selection
        if (this.elements.roleSelect) this.elements.roleSelect.value = '';
        this.elements.rolePermissions?.classList.add('d-none');
        
        await this.loadUsers();
    }
    
    closeModal() {
        this.elements.modal?.classList.remove('active');
        this.clearFeedback();
        if (this.elements.userSearch) this.elements.userSearch.value = '';
    }
    
    async loadUsers(page = 1, search = '') {
        if (this.isLoading) return;
        
        this.isLoading = true;
        this.showLoadingState();
        
        try {
            const params = new URLSearchParams({ page, search });
            const response = await fetch(`/api/users/?${params}`, {
                method: 'GET',
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                    'Content-Type': 'application/json'
                }
            });
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            
            if (data.success) {
                this.usersData = data;
                this.renderUsers(data.users);
                this.updatePagination();
            } else {
                this.showError(data.error || 'Failed to load users');
            }
        } catch (error) {
            console.error('Error loading users:', error);
            this.showError('Network error. Please check your connection and try again.');
        } finally {
            this.isLoading = false;
        }
    }
    
    showLoadingState() {
        if (this.elements.usersList) {
            this.elements.usersList.innerHTML = `
                <tr>
                    <td colspan="3" class="text-center py-4">
                        <div class="d-flex align-items-center justify-content-center">
                            <div class="spinner-border spinner-border-sm text-primary me-2" role="status"></div>
                            <span>Loading users...</span>
                        </div>
                    </td>
                </tr>
            `;
        }
    }
    
    renderUsers(users) {
        if (!this.elements.usersList) return;
        
        if (!users || users.length === 0) {
            this.elements.usersList.innerHTML = `
                <tr>
                    <td colspan="3" class="text-center text-muted py-4">
                        <i class="bi bi-people fs-3 d-block mb-2"></i>
                        No users found
                    </td>
                </tr>
            `;
            return;
        }
        
        this.elements.usersList.innerHTML = '';
        
        users.forEach((user, index) => {
            const tr = document.createElement('tr');
            tr.className = 'user-row';
            tr.style.animationDelay = `${index * 50}ms`;
            
            const roleColor = this.getRoleColor(user.role);
            const lastLogin = user.last_login ? 
                new Date(user.last_login).toLocaleDateString() : 'Never';
            
            tr.innerHTML = `
                <td>
                    <div class="d-flex align-items-center">
                        <div class="user-avatar me-2">
                            <div class="rounded-circle bg-${roleColor} d-flex align-items-center justify-content-center" 
                                 style="width:32px;height:32px;font-size:0.8rem;color:white;">
                                ${user.full_name.charAt(0).toUpperCase()}
                            </div>
                        </div>
                        <div>
                            <div class="fw-semibold">${this.escapeHtml(user.full_name)}</div>
                            <small class="text-muted">${this.escapeHtml(user.email)}</small>
                        </div>
                    </div>
                </td>
                <td>
                    <span class="badge bg-${roleColor} role-badge">
                        ${user.role.charAt(0).toUpperCase() + user.role.slice(1)}
                    </span>
                    <div class="small text-muted mt-1">Last: ${lastLogin}</div>
                </td>
                <td>
                    <button class="btn btn-sm btn-outline-primary edit-role-btn" 
                            data-user-id="${user.id}"
                            data-user-name="${this.escapeHtml(user.full_name)}"
                            data-user-role="${user.role}"
                            title="Edit Role">
                        <i class="bi bi-pencil"></i>
                    </button>
                </td>
            `;
            
            this.elements.usersList.appendChild(tr);
        });
        
        // Bind edit buttons
        this.elements.usersList.querySelectorAll('.edit-role-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const userId = e.currentTarget.dataset.userId;
                const userName = e.currentTarget.dataset.userName;
                const userRole = e.currentTarget.dataset.userRole;
                this.openEditModal(userId, userName, userRole);
            });
        });
    }
    
    getRoleColor(role) {
        const colors = {
            admin: 'danger',
            manager: 'warning',
            user: 'secondary'
        };
        return colors[role] || 'secondary';
    }
    
    updatePagination() {
        if (this.elements.usersPrev) {
            this.elements.usersPrev.disabled = this.usersData.page <= 1;
        }
        if (this.elements.usersNext) {
            this.elements.usersNext.disabled = this.usersData.page >= this.usersData.num_pages;
        }
        if (this.elements.usersPageInfo) {
            this.elements.usersPageInfo.textContent = 
                `Page ${this.usersData.page} of ${this.usersData.num_pages} (${this.usersData.total} users)`;
        }
    }
    
    previousPage() {
        if (this.usersData.page > 1 && !this.isLoading) {
            this.loadUsers(this.usersData.page - 1, this.elements.userSearch?.value || '');
        }
    }
    
    nextPage() {
        if (this.usersData.page < this.usersData.num_pages && !this.isLoading) {
            this.loadUsers(this.usersData.page + 1, this.elements.userSearch?.value || '');
        }
    }
    
    showRolePermissions(role) {
        if (!this.elements.rolePermissions || !this.elements.selectedRoleName) return;
        
        this.elements.selectedRoleName.textContent = role.charAt(0).toUpperCase() + role.slice(1);
        this.elements.rolePermissions.classList.remove('d-none');
        
        // Reset all checkboxes
        document.querySelectorAll('.permissions-grid input[type="checkbox"]').forEach(cb => {
            cb.checked = false;
        });
        
        // Check permissions for selected role
        const rolePermissions = this.permissions[role] || [];
        rolePermissions.forEach(permId => {
            const checkbox = document.getElementById(permId);
            if (checkbox) checkbox.checked = true;
        });
    }
    
    openEditModal(userId, userName, currentRole) {
        this.currentEditUserId = userId;
        
        if (this.elements.editUserInfo) {
            this.elements.editUserInfo.innerHTML = `
                <div class="d-flex align-items-center">
                    <div class="rounded-circle bg-${this.getRoleColor(currentRole)} d-flex align-items-center justify-content-center me-2" 
                         style="width:24px;height:24px;font-size:0.7rem;color:white;">
                        ${userName.charAt(0).toUpperCase()}
                    </div>
                    <div>
                        <strong>${this.escapeHtml(userName)}</strong>
                        <br><small class="text-muted">Current role: ${currentRole}</small>
                    </div>
                </div>
            `;
        }
        
        if (this.elements.editRoleSelect) {
            this.elements.editRoleSelect.value = currentRole;
        }
        
        this.clearEditFeedback();
        this.elements.editModal?.classList.add('active');
    }
    
    closeEditModal() {
        this.elements.editModal?.classList.remove('active');
        this.currentEditUserId = null;
        this.elements.editForm?.reset();
        this.clearEditFeedback();
    }
    
    async handleRoleUpdate(e) {
        e.preventDefault();
        
        if (!this.currentEditUserId) return;
        
        const newRole = this.elements.editRoleSelect?.value;
        if (!newRole) {
            this.showEditError('Please select a role');
            return;
        }
        
        this.showEditInfo('Updating role...');
        
        try {
            const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value;
            const response = await fetch('/api/users/update-role/', {
                method: 'POST',
                headers: {
                    'X-CSRFToken': csrfToken,
                    'Content-Type': 'application/x-www-form-urlencoded',
                },
                body: new URLSearchParams({
                    user_id: this.currentEditUserId,
                    role: newRole
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.showEditSuccess('Role updated successfully!');
                setTimeout(() => {
                    this.closeEditModal();
                    this.loadUsers(this.usersData.page, this.elements.userSearch?.value || '');
                }, 1000);
            } else {
                this.showEditError(data.error || 'Failed to update role');
            }
        } catch (error) {
            console.error('Error updating role:', error);
            this.showEditError('Network error. Please try again.');
        }
    }
    
    // Utility methods
    showError(message) {
        this.showFeedback(message, 'danger');
    }
    
    showSuccess(message) {
        this.showFeedback(message, 'success');
    }
    
    showInfo(message) {
        this.showFeedback(message, 'info');
    }
    
    showFeedback(message, type = 'info') {
        if (this.elements.feedback) {
            this.elements.feedback.innerHTML = `
                <div class="alert alert-${type} alert-dismissible fade show" role="alert">
                    ${this.escapeHtml(message)}
                    <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
                </div>
            `;
        }
    }
    
    clearFeedback() {
        if (this.elements.feedback) {
            this.elements.feedback.innerHTML = '';
        }
    }
    
    showEditError(message) {
        this.showEditFeedback(message, 'danger');
    }
    
    showEditSuccess(message) {
        this.showEditFeedback(message, 'success');
    }
    
    showEditInfo(message) {
        this.showEditFeedback(message, 'info');
    }
    
    showEditFeedback(message, type = 'info') {
        if (this.elements.editFeedback) {
            this.elements.editFeedback.innerHTML = `
                <div class="alert alert-${type}">${this.escapeHtml(message)}</div>
            `;
        }
    }
    
    clearEditFeedback() {
        if (this.elements.editFeedback) {
            this.elements.editFeedback.innerHTML = '';
        }
    }
    
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.permissionManager = new PermissionManager();
});

// Add CSS animations
const style = document.createElement('style');
style.textContent = `
    .user-row {
        animation: fadeInUp 0.3s ease-out forwards;
        opacity: 0;
        transform: translateY(10px);
    }
    
    @keyframes fadeInUp {
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }
    
    .role-badge {
        transition: all 0.2s ease;
    }
    
    .edit-role-btn {
        transition: all 0.2s ease;
    }
    
    .edit-role-btn:hover {
        transform: scale(1.05);
    }
    
    .user-avatar {
        transition: transform 0.2s ease;
    }
    
    .user-row:hover .user-avatar {
        transform: scale(1.1);
    }
`;
document.head.appendChild(style);