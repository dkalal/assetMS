/**
 * Enterprise Authentication & Authorization Handler
 * Handles API errors and user role-based access control
 */
class EnterpriseAuth {
    constructor() {
        this.currentUser = null;
        this.init();
    }
    
    init() {
        // Get current user info from DOM
        this.getCurrentUser();
        
        // Setup global error handlers
        this.setupGlobalErrorHandlers();
    }
    
    getCurrentUser() {
        // Extract user info from Django template context
        const userElement = document.querySelector('[data-user-role]');
        if (userElement) {
            this.currentUser = {
                role: userElement.dataset.userRole,
                isAdmin: userElement.dataset.userRole === 'admin',
                isManager: userElement.dataset.userRole === 'manager',
                isUser: userElement.dataset.userRole === 'user'
            };
        }
    }
    
    setupGlobalErrorHandlers() {
        // Override fetch to handle authentication errors
        const originalFetch = window.fetch;
        window.fetch = async (...args) => {
            try {
                const [url] = args;
                const isHeartbeat = url && url.includes('/session/heartbeat/');
                
                const response = await originalFetch(...args);
                
                // Handle API authentication/authorization errors (skip heartbeat logging)
                if ((response.status === 401 || response.status === 403) && !isHeartbeat) {
                    try {
                        const data = await response.json();
                        this.handleAuthError(data, response.status);
                    } catch (e) {
                        // Response might not be JSON
                        this.handleAuthError({error: 'Authentication failed'}, response.status);
                    }
                }
                
                return response;
            } catch (error) {
                const [url] = args;
                const isHeartbeat = url && url.includes('/session/heartbeat/');
                if (!isHeartbeat) {
                    console.error('Network error:', error);
                }
                throw error;
            }
        };
    }
    
    handleAuthError(data, status) {
        let message = '';
        let type = 'error';
        
        if (status === 401) {
            message = 'Your session has expired. Please login again.';
            // Redirect to login after showing message
            setTimeout(() => {
                window.location.href = '/login/';
            }, 3000);
        } else if (status === 403) {
            message = `Access denied. ${data.error || 'Insufficient permissions.'}`;
            if (data.required_roles) {
                message += ` Required roles: ${data.required_roles.join(', ')}`;
            }
        }
        
        // Show toast notification
        if (window.showToast) {
            window.showToast(message, type, 5000);
        } else {
            alert(message);
        }
    }
    
    hasRole(role) {
        return this.currentUser && this.currentUser.role === role;
    }
    
    hasAnyRole(roles) {
        return this.currentUser && roles.includes(this.currentUser.role);
    }
    
    canAccessUserManagement() {
        return this.hasAnyRole(['admin', 'manager']);
    }
    
    canInviteUsers() {
        return this.hasRole('admin');
    }
    
    canEditUsers() {
        return this.hasRole('admin');
    }
    
    hideElementsBasedOnRole() {
        // Hide elements that user doesn't have access to
        if (!this.canAccessUserManagement()) {
            const userMgmtElements = document.querySelectorAll('[data-requires-role="admin,manager"]');
            userMgmtElements.forEach(el => el.style.display = 'none');
        }
        
        if (!this.canInviteUsers()) {
            const inviteElements = document.querySelectorAll('[data-requires-role="admin"]');
            inviteElements.forEach(el => el.style.display = 'none');
        }
    }
}

// Initialize enterprise auth
window.enterpriseAuth = new EnterpriseAuth();

// Global toast function for consistency
window.showToast = function(message, type = 'success', duration = 3000) {
    const toastContainer = document.querySelector('.toast-container') || createToastContainer();
    
    const toast = document.createElement('div');
    toast.className = `enterprise-toast ${type} p-3 mb-2`;
    
    const icon = {
        success: 'check-circle',
        error: 'exclamation-triangle',
        warning: 'exclamation-triangle',
        info: 'info-circle'
    }[type] || 'info-circle';
    
    toast.innerHTML = `
        <div class="d-flex align-items-center">
            <i class="bi bi-${icon} me-2 fs-5"></i>
            <div class="flex-grow-1">${message}</div>
            <button type="button" class="btn-close btn-close-sm ms-2" onclick="this.parentElement.parentElement.remove()"></button>
        </div>
    `;
    
    toastContainer.appendChild(toast);
    
    // Auto remove
    setTimeout(() => {
        if (toast.parentNode) {
            toast.style.animation = 'slideInRight 0.3s ease-out reverse';
            setTimeout(() => toast.remove(), 300);
        }
    }, duration);
};

function createToastContainer() {
    const container = document.createElement('div');
    container.className = 'toast-container';
    document.body.appendChild(container);
    return container;
}