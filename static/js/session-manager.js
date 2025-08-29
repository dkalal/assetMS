/**
 * Enterprise Session Manager
 * Handles concurrent session management on the frontend
 */
class EnterpriseSessionManager {
    constructor() {
        this.sessionId = this.generateSessionId();
        this.heartbeatInterval = 30000; // 30 seconds
        this.heartbeatTimer = null;
        this.init();
    }
    
    init() {
        // Store session ID in sessionStorage (tab-specific)
        if (!sessionStorage.getItem('tab_session_id')) {
            sessionStorage.setItem('tab_session_id', this.sessionId);
        }
        
        // Start session heartbeat
        this.startHeartbeat();
        
        // Handle page visibility changes
        document.addEventListener('visibilitychange', () => {
            if (document.hidden) {
                this.pauseHeartbeat();
            } else {
                this.resumeHeartbeat();
            }
        });
        
        // Handle page unload
        window.addEventListener('beforeunload', () => {
            this.cleanup();
        });
    }
    
    generateSessionId() {
        return 'tab_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    }
    
    startHeartbeat() {
        this.heartbeatTimer = setInterval(() => {
            this.sendHeartbeat();
        }, this.heartbeatInterval);
    }
    
    pauseHeartbeat() {
        if (this.heartbeatTimer) {
            clearInterval(this.heartbeatTimer);
            this.heartbeatTimer = null;
        }
    }
    
    resumeHeartbeat() {
        if (!this.heartbeatTimer) {
            this.startHeartbeat();
        }
    }
    
    async sendHeartbeat() {
        try {
            const response = await fetch('/settings/api/session/heartbeat/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    tab_session_id: sessionStorage.getItem('tab_session_id'),
                    timestamp: Date.now()
                })
            });
            
            if (response.ok) {
                const data = await response.json();
                if (data.success) {
                    this.consecutiveErrors = 0;
                } else {
                    this.handleHeartbeatError('API returned error: ' + data.error);
                }
            } else if (response.status === 403) {
                this.handleHeartbeatError('Authentication required');
            } else {
                this.handleHeartbeatError(`HTTP ${response.status}`);
            }
        } catch (error) {
            this.handleHeartbeatError(error.message);
        }
    }
    
    handleHeartbeatError(errorMessage) {
        this.consecutiveErrors = (this.consecutiveErrors || 0) + 1;
        
        if (this.consecutiveErrors >= 3) {
            console.warn('Multiple heartbeat failures, pausing heartbeat');
            this.pauseHeartbeat();
            
            // Resume after 5 minutes
            setTimeout(() => {
                this.consecutiveErrors = 0;
                this.resumeHeartbeat();
            }, 300000);
        }
    }
    
    getCSRFToken() {
        const cookies = document.cookie.split(';');
        for (let cookie of cookies) {
            const [name, value] = cookie.trim().split('=');
            if (name === 'csrftoken') {
                return value;
            }
        }
        return '';
    }
    
    cleanup() {
        this.pauseHeartbeat();
        // Could send session end signal here
    }
    
    // Public API for session information
    getSessionInfo() {
        return {
            sessionId: this.sessionId,
            tabId: sessionStorage.getItem('tab_session_id'),
            isActive: !document.hidden
        };
    }
}

// Initialize session manager only for authenticated users
document.addEventListener('DOMContentLoaded', function() {
    // Check if user is authenticated by looking for auth indicators
    const isAuthenticated = document.querySelector('[data-user-role]') || 
                           document.querySelector('.navbar .dropdown') ||
                           document.body.classList.contains('authenticated');
    
    if (isAuthenticated && typeof window.sessionManager === 'undefined') {
        window.sessionManager = new EnterpriseSessionManager();
        console.log('✅ Session manager initialized for authenticated user');
    } else if (!isAuthenticated) {
        console.log('ℹ️ Session manager skipped - user not authenticated');
    }
});

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
    module.exports = EnterpriseSessionManager;
}