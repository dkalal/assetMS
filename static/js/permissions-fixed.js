/**
 * Enterprise Permission Management System - CSP Compliant
 * Fixed for production with proper event delegation
 */
(function() {
    'use strict';
    
    let permissionManager = null;
    
    class PermissionManager {
        constructor() {
            this.usersData = { page: 1, numPages: 1, users: [], total: 0 };
            this.searchTimeout = null;
            this.currentEditUserId = null;
            this.isLoading = false;
            
            this.permissions = {
                admin: ['perm-view-assets', 'perm-create-assets', 'perm-edit-assets', 'perm-delete-assets', 'perm-manage-users', 'perm-view-reports', 'perm-export-data', 'perm-system-admin'],
                manager: ['perm-view-assets', 'perm-create-assets', 'perm-edit-assets', 'perm-view-reports', 'perm-export-data'],
                user: ['perm-view-assets']
            };
            
            this.init();
        }
        
        init() {
            this.bindEvents();
            console.log('Permission Manager initialized');
        }
        
        bindEvents() {
            // Main modal controls
            const openBtn = document.getElementById('openPermissionsModal');
            const closeBtn = document.getElementById('closePermissionsModal');
            const closeBtnFooter = document.getElementById('closePermissionsModalBtn');
            
            if (openBtn) openBtn.addEventListener('click', () => this.openModal());
            if (closeBtn) closeBtn.addEventListener('click', () => this.closeModal());
            if (closeBtnFooter) closeBtnFooter.addEventListener('click', () => this.closeModal());
            
            // Role selection
            const roleSelect = document.getElementById('role-select');
            if (roleSelect) {
                roleSelect.addEventListener('change', (e) => {
                    if (e.target.value) {
                        this.showRolePermissions(e.target.value);
                    } else {
                        const rolePermissions = document.getElementById('role-permissions');
                        if (rolePermissions) rolePermissions.classList.add('d-none');
                    }
                });
            }
            
            // Search functionality
            const userSearch = document.getElementById('user-search');
            if (userSearch) {
                userSearch.addEventListener('input', (e) => {
                    clearTimeout(this.searchTimeout);
                    this.searchTimeout = setTimeout(() => {
                        this.loadUsers(1, e.target.value.trim());
                    }, 300);
                });
            }
            
            // Edit modal controls
            const editForm = document.getElementById('edit-user-role-form');
            const closeEditBtn = document.getElementById('closeEditUserRoleModal');
            const cancelEditBtn = document.getElementById('cancelEditUserRole');
            
            if (editForm) editForm.addEventListener('submit', (e) => this.handleRoleUpdate(e));
            if (closeEditBtn) closeEditBtn.addEventListener('click', () => this.closeEditModal());
            if (cancelEditBtn) cancelEditBtn.addEventListener('click', () => this.closeEditModal());
            
            // Event delegation for dynamically created edit buttons
            const usersList = document.getElementById('users-list');
            if (usersList) {
                usersList.addEventListener('click', (e) => {
                    const editBtn = e.target.closest('.edit-role-btn');
                    if (editBtn) {
                        const userId = editBtn.dataset.userId;
                        const userName = editBtn.dataset.userName;
                        const userRole = editBtn.dataset.userRole;
                        this.openEditModal(userId, userName, userRole);
                    }
                });
            }
        }
        
        async openModal() {
            const modal = document.getElementById('permissionsModalCustom');
            if (!modal) return;
            
            modal.classList.add('active');
            this.clearFeedback();
            await this.loadUsers();
        }
        
        closeModal() {
            const modal = document.getElementById('permissionsModalCustom');
            if (modal) modal.classList.remove('active');
            this.clearFeedback();
        }
        
        async loadUsers(page = 1, search = '') {
            const usersList = document.getElementById('users-list');
            if (!usersList) return;
            
            this.isLoading = true;
            usersList.innerHTML = '<tr><td colspan="3" class="text-center">Loading...</td></tr>';
            
            try {
                const params = new URLSearchParams({ page, search });
                const response = await fetch(`/api/users/?${params}`);
                const data = await response.json();
                
                if (data.success) {
                    this.usersData = data;
                    this.renderUsers(data.users);
                } else {
                    this.showError(data.error || 'Failed to load users');
                }
            } catch (error) {
                console.error('Error loading users:', error);
                this.showError('Network error loading users');
            } finally {
                this.isLoading = false;
            }
        }
        
        renderUsers(users) {
            const usersList = document.getElementById('users-list');
            if (!usersList) return;
            
            if (!users || users.length === 0) {
                usersList.innerHTML = '<tr><td colspan="3" class="text-center text-muted">No users found</td></tr>';
                return;
            }
            
            usersList.innerHTML = '';
            
            users.forEach(user => {
                const tr = document.createElement('tr');
                const roleColor = this.getRoleColor(user.role);
                
                tr.innerHTML = `
                    <td>
                        <div class="fw-semibold">${this.escapeHtml(user.full_name)}</div>
                        <small class="text-muted">${this.escapeHtml(user.email)}</small>
                    </td>
                    <td><span class="badge bg-${roleColor}">${user.role}</span></td>
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
                
                usersList.appendChild(tr);
            });
        }
        
        showRolePermissions(role) {
            const rolePermissions = document.getElementById('role-permissions');
            const selectedRoleName = document.getElementById('selected-role-name');
            
            if (!rolePermissions || !selectedRoleName) return;
            
            selectedRoleName.textContent = role.charAt(0).toUpperCase() + role.slice(1);
            rolePermissions.classList.remove('d-none');
            
            // Reset all checkboxes
            document.querySelectorAll('.permissions-grid input[type="checkbox"]').forEach(cb => {
                cb.checked = false;
            });
            
            // Check permissions for selected role
            const rolePerms = this.permissions[role] || [];
            rolePerms.forEach(permId => {
                const checkbox = document.getElementById(permId);
                if (checkbox) checkbox.checked = true;
            });
        }
        
        openEditModal(userId, userName, currentRole) {
            this.currentEditUserId = userId;
            
            const editModal = document.getElementById('editUserRoleModal');
            const editUserInfo = document.getElementById('edit-user-info');
            const editRoleSelect = document.getElementById('edit-user-role-select');
            
            if (editUserInfo) {
                editUserInfo.innerHTML = `<strong>${this.escapeHtml(userName)}</strong><br><small>Current role: ${currentRole}</small>`;
            }
            
            if (editRoleSelect) {
                editRoleSelect.value = currentRole;
            }
            
            this.clearEditFeedback();
            if (editModal) editModal.classList.add('active');
        }
        
        closeEditModal() {
            const editModal = document.getElementById('editUserRoleModal');
            if (editModal) editModal.classList.remove('active');
            
            this.currentEditUserId = null;
            this.clearEditFeedback();
            
            const editForm = document.getElementById('edit-user-role-form');
            if (editForm) editForm.reset();
        }
        
        async handleRoleUpdate(e) {
            e.preventDefault();
            
            if (!this.currentEditUserId) return;
            
            const editRoleSelect = document.getElementById('edit-user-role-select');
            const newRole = editRoleSelect ? editRoleSelect.value : '';
            
            if (!newRole) {
                this.showEditError('Please select a role');
                return;
            }
            
            this.showEditInfo('Updating role...');
            
            try {
                const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
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
                        this.loadUsers();
                    }, 1000);
                } else {
                    this.showEditError(data.error || 'Failed to update role');
                }
            } catch (error) {
                console.error('Error updating role:', error);
                this.showEditError('Network error. Please try again.');
            }
        }
        
        getRoleColor(role) {
            const colors = { admin: 'danger', manager: 'warning', user: 'secondary' };
            return colors[role] || 'secondary';
        }
        
        showError(message) {
            this.showFeedback(message, 'danger');
        }
        
        showFeedback(message, type = 'info') {
            const feedback = document.getElementById('permissions-feedback');
            if (feedback) {
                feedback.innerHTML = `<div class="alert alert-${type}">${this.escapeHtml(message)}</div>`;
            }
        }
        
        clearFeedback() {
            const feedback = document.getElementById('permissions-feedback');
            if (feedback) feedback.innerHTML = '';
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
            const editFeedback = document.getElementById('edit-role-feedback');
            if (editFeedback) {
                editFeedback.innerHTML = `<div class="alert alert-${type}">${this.escapeHtml(message)}</div>`;
            }
        }
        
        clearEditFeedback() {
            const editFeedback = document.getElementById('edit-role-feedback');
            if (editFeedback) editFeedback.innerHTML = '';
        }
        
        escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }
    }
    
    // Initialize when DOM is ready
    document.addEventListener('DOMContentLoaded', function() {
        permissionManager = new PermissionManager();
        window.permissionManager = permissionManager;
    });
    
})();