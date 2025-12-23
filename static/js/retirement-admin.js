/**
 * ============================================================================
 * WORLD-CLASS RETIREMENT SYSTEM - ADMIN APPROVAL CENTER
 * Professional, Scalable, Maintainable JavaScript
 * ============================================================================
 */

// Global state
let currentRetirementId = null;
let allRequests = [];
let approveModal = null;
let rejectModal = null;

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    approveModal = new bootstrap.Modal(document.getElementById('approveModal'));
    rejectModal = new bootstrap.Modal(document.getElementById('rejectModal'));
    
    loadDashboardStats();
    loadPendingApprovals();
    setupEventListeners();
});

/**
 * Load dashboard statistics
 */
async function loadDashboardStats() {
    try {
        const response = await fetch('/api/retirement/dashboard/');
        const data = await response.json();
        
        if (data.success) {
            document.getElementById('pendingCount').textContent = data.pending_approvals || 0;
            document.getElementById('approvedCount').textContent = data.approved_requests || 0;
            document.getElementById('inProgressCount').textContent = data.in_progress || 0;
        }
    } catch (error) {
        console.error('Error loading dashboard stats:', error);
    }
}

/**
 * Load pending approvals
 */
async function loadPendingApprovals() {
    try {
        document.getElementById('loadingState').style.display = 'block';
        document.getElementById('approvalsList').style.display = 'none';
        document.getElementById('emptyState').style.display = 'none';
        
        const response = await fetch('/api/retirement/pending-approvals/');
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        
        console.log('API Response:', data); // Debug logging
        
        if (data.success) {
            allRequests = data.requests || [];
            console.log('Loaded requests:', allRequests.length); // Debug logging
            displayRequests(allRequests);
        } else {
            showAlert('Failed to load requests: ' + (data.error || 'Unknown error'), 'danger');
        }
    } catch (error) {
        console.error('Error loading approvals:', error);
        showAlert('Error loading retirement requests: ' + error.message, 'danger');
        document.getElementById('emptyState').style.display = 'block';
    } finally {
        document.getElementById('loadingState').style.display = 'none';
    }
}

/**
 * Display requests in world-class cards
 */
function displayRequests(requests) {
    const container = document.getElementById('approvalsList');
    
    if (requests.length === 0) {
        document.getElementById('emptyState').style.display = 'block';
        container.style.display = 'none';
        return;
    }
    
    container.style.display = 'block';
    
    const cards = requests.map(request => {
        try {
            // Safely extract user data
            const userName = request.user?.name || request.user_name || 'Unknown User';
            const userEmail = request.user?.email || request.user_email || 'No email';
            const userRole = request.user?.role || request.user_role || '';
            const branchName = request.user?.branch || request.branch_name || '';
            
            // Get initials for avatar
            const nameParts = userName.split(' ').filter(part => part.length > 0);
            const initials = nameParts.length > 1 
                ? nameParts[0][0] + nameParts[nameParts.length - 1][0]
                : (nameParts[0]?.[0] || 'U');
            
            // Calculate days until effective
            const daysUntil = request.days_until_effective !== null && request.days_until_effective !== undefined
                ? request.days_until_effective
                : Math.ceil((new Date(request.effective_date) - new Date()) / (1000 * 60 * 60 * 24));
        
        return `
            <div class="request-card">
                <!-- Card Header: User Info -->
                <div class="request-card-header">
                    <div class="request-avatar">
                        ${escapeHtml(initials.toUpperCase())}
                    </div>
                    <div class="request-user-info">
                        <h6 class="request-user-name">
                            ${escapeHtml(userName)}
                            ${userRole ? `<span class="badge bg-secondary">${escapeHtml(userRole)}</span>` : ''}
                        </h6>
                        <p class="request-user-email">
                            <i class="bi bi-envelope"></i>
                            ${escapeHtml(userEmail)}
                        </p>
                    </div>
                </div>
                
                <!-- Card Body: Request Details -->
                <div class="request-card-body">
                    <div class="request-info-item">
                        <div class="request-info-label">
                            <i class="bi bi-calendar-event"></i>
                            Request Date
                        </div>
                        <div class="request-info-value">
                            ${new Date(request.request_date).toLocaleDateString('en-US', { 
                                month: 'short', 
                                day: 'numeric', 
                                year: 'numeric' 
                            })}
                        </div>
                    </div>
                    
                    <div class="request-info-item">
                        <div class="request-info-label">
                            <i class="bi bi-calendar-check"></i>
                            Effective Date
                        </div>
                        <div class="request-info-value">
                            ${new Date(request.effective_date).toLocaleDateString('en-US', { 
                                month: 'short', 
                                day: 'numeric', 
                                year: 'numeric' 
                            })}
                        </div>
                    </div>
                    
                    <div class="request-info-item">
                        <div class="request-info-label">
                            <i class="bi bi-hourglass-split"></i>
                            Days Until
                        </div>
                        <div class="request-info-value">
                            ${daysUntil} days
                        </div>
                    </div>
                    
                    <div class="request-info-item">
                        <div class="request-info-label">
                            <i class="bi bi-box-seam"></i>
                            Assets
                        </div>
                        <div class="request-info-value">
                            ${request.asset_count || 0} items
                        </div>
                    </div>
                </div>
                
                <!-- Reason Section -->
                <div class="request-reason-section">
                    <div class="request-reason-label">
                        <i class="bi bi-chat-left-text"></i>
                        Retirement Reason
                    </div>
                    <p class="request-reason-text">
                        ${escapeHtml(request.reason)}
                    </p>
                </div>
                
                <!-- Card Footer: Meta & Actions -->
                <div class="request-card-footer">
                    <div class="request-meta">
                        <div class="request-meta-item">
                            <i class="bi bi-tag"></i>
                            <span>${escapeHtml(request.reason_category_display || request.reason_category || 'General')}</span>
                        </div>
                        ${branchName ? `
                            <div class="request-meta-item">
                                <i class="bi bi-building"></i>
                                <span>${escapeHtml(branchName)}</span>
                            </div>
                        ` : ''}
                    </div>
                    
                    <div class="request-actions">
                        <button class="request-action-btn approve" onclick="showApproveModal('${request.id}')" title="Approve Request">
                            <i class="bi bi-check-circle"></i>
                            Approve
                        </button>
                        <button class="request-action-btn reject" onclick="showRejectModal('${request.id}')" title="Reject Request">
                            <i class="bi bi-x-circle"></i>
                            Reject
                        </button>
                    </div>
                </div>
            </div>
        `;
        } catch (error) {
            console.error('Error rendering request card:', error, request);
            return `
                <div class="request-card">
                    <div class="alert alert-warning mb-0">
                        <i class="bi bi-exclamation-triangle me-2"></i>
                        Error displaying request. Please contact support.
                    </div>
                </div>
            `;
        }
    }).join('');
    
    container.innerHTML = cards;
}

/**
 * Show approve modal
 */
function showApproveModal(retirementId) {
    currentRetirementId = retirementId;
    document.getElementById('approvalComments').value = '';
    approveModal.show();
}

/**
 * Show reject modal
 */
function showRejectModal(retirementId) {
    currentRetirementId = retirementId;
    document.getElementById('rejectionReason').value = '';
    rejectModal.show();
}

/**
 * Confirm approval
 */
async function confirmApprove() {
    const comments = document.getElementById('approvalComments').value.trim();
    
    const confirmBtn = document.getElementById('confirmApproveBtn');
    const originalText = confirmBtn.innerHTML;
    
    confirmBtn.disabled = true;
    confirmBtn.innerHTML = '<span class="loading-spinner"></span> Approving...';
    
    try {
        // Use RESTful endpoint with path parameter: /api/retirement/<uuid>/approve/
        const response = await fetch(`/api/retirement/${currentRetirementId}/approve/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify({
                // Backend reads comments from body; ID comes from URL
                comments: comments
            })
        });

        let result;
        try {
            result = await response.json();
        } catch (e) {
            // Fallback if server responded with non-JSON (e.g. HTML error page)
            showAlert(`Approval failed: HTTP ${response.status}`, 'danger');
            confirmBtn.disabled = false;
            confirmBtn.innerHTML = originalText;
            return;
        }

        if (!response.ok || !result.success) {
            const message = result.error || `Approval failed (HTTP ${response.status})`;
            showAlert(message, 'danger');
            confirmBtn.disabled = false;
            confirmBtn.innerHTML = originalText;
            return;
        }

        if (result.success) {
            approveModal.hide();
            showAlert(result.message || 'Request approved successfully', 'success');
            
            // Reload data
            setTimeout(() => {
                loadDashboardStats();
                loadPendingApprovals();
            }, 1000);
        }
    } catch (error) {
        console.error('Error approving request:', error);
        showAlert('An error occurred. Please try again.', 'danger');
        confirmBtn.disabled = false;
        confirmBtn.innerHTML = originalText;
    }
}

/**
 * Confirm rejection
 */
async function confirmReject() {
    const reason = document.getElementById('rejectionReason').value.trim();
    
    if (reason.length < 10) {
        showAlert('Rejection reason must be at least 10 characters', 'warning');
        return;
    }
    
    const confirmBtn = document.getElementById('confirmRejectBtn');
    const originalText = confirmBtn.innerHTML;
    
    confirmBtn.disabled = true;
    confirmBtn.innerHTML = '<span class="loading-spinner"></span> Rejecting...';
    
    try {
        // Use RESTful endpoint with path parameter: /api/retirement/<uuid>/reject/
        const response = await fetch(`/api/retirement/${currentRetirementId}/reject/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify({
                rejection_reason: reason
            })
        });

        let result;
        try {
            result = await response.json();
        } catch (e) {
            showAlert(`Rejection failed: HTTP ${response.status}`, 'danger');
            confirmBtn.disabled = false;
            confirmBtn.innerHTML = originalText;
            return;
        }

        if (!response.ok || !result.success) {
            const message = result.error || `Rejection failed (HTTP ${response.status})`;
            showAlert(message, 'danger');
            confirmBtn.disabled = false;
            confirmBtn.innerHTML = originalText;
            return;
        }

        if (result.success) {
            rejectModal.hide();
            showAlert(result.message || 'Request rejected successfully', 'success');
            
            // Reload data
            setTimeout(() => {
                loadDashboardStats();
                loadPendingApprovals();
            }, 1000);
        }
    } catch (error) {
        console.error('Error rejecting request:', error);
        showAlert('An error occurred. Please try again.', 'danger');
        confirmBtn.disabled = false;
        confirmBtn.innerHTML = originalText;
    }
}

/**
 * Filter requests
 */
function filterRequests() {
    const searchTerm = document.getElementById('searchInput').value.toLowerCase();
    const statusFilter = document.getElementById('statusFilter').value;
    const sortBy = document.getElementById('sortBy').value;
    
    let filtered = [...allRequests];
    
    // Apply search filter
    if (searchTerm) {
        filtered = filtered.filter(request =>
            request.user_name.toLowerCase().includes(searchTerm) ||
            request.user_email.toLowerCase().includes(searchTerm)
        );
    }
    
    // Apply status filter
    if (statusFilter) {
        filtered = filtered.filter(request => request.status === statusFilter);
    }
    
    // Apply sorting
    if (sortBy === 'newest') {
        filtered.sort((a, b) => new Date(b.request_date) - new Date(a.request_date));
    } else if (sortBy === 'oldest') {
        filtered.sort((a, b) => new Date(a.request_date) - new Date(b.request_date));
    } else if (sortBy === 'effective_date') {
        filtered.sort((a, b) => new Date(a.effective_date) - new Date(b.effective_date));
    }
    
    displayRequests(filtered);
}

/**
 * Setup event listeners
 */
function setupEventListeners() {
    // Search input
    const searchInput = document.getElementById('searchInput');
    if (searchInput) {
        searchInput.addEventListener('input', filterRequests);
    }
    
    // Status filter
    const statusFilter = document.getElementById('statusFilter');
    if (statusFilter) {
        statusFilter.addEventListener('change', filterRequests);
    }
    
    // Sort dropdown
    const sortBy = document.getElementById('sortBy');
    if (sortBy) {
        sortBy.addEventListener('change', filterRequests);
    }
    
    // Approve button
    const confirmApproveBtn = document.getElementById('confirmApproveBtn');
    if (confirmApproveBtn) {
        confirmApproveBtn.addEventListener('click', confirmApprove);
    }
    
    // Reject button
    const confirmRejectBtn = document.getElementById('confirmRejectBtn');
    if (confirmRejectBtn) {
        confirmRejectBtn.addEventListener('click', confirmReject);
    }
}

/**
 * Show alert message
 */
function showAlert(message, type = 'info') {
    const alertContainer = document.createElement('div');
    alertContainer.className = `alert-modern alert-${type}`;
    alertContainer.style.cssText = 'position: fixed; top: 20px; right: 20px; z-index: 9999; min-width: 300px; animation: slideIn 0.3s ease;';
    
    const icon = {
        success: 'check-circle',
        danger: 'x-circle',
        warning: 'exclamation-triangle',
        info: 'info-circle'
    }[type] || 'info-circle';
    
    alertContainer.innerHTML = `
        <i class="bi bi-${icon} fs-4"></i>
        <div>${escapeHtml(message)}</div>
    `;
    
    document.body.appendChild(alertContainer);
    
    setTimeout(() => {
        alertContainer.style.animation = 'slideOut 0.3s ease';
        setTimeout(() => alertContainer.remove(), 300);
    }, 4000);
}

/**
 * Get CSRF token from cookie
 */
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

/**
 * Escape HTML to prevent XSS
 */
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Add CSS animations
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from {
            transform: translateX(100%);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }
    
    @keyframes slideOut {
        from {
            transform: translateX(0);
            opacity: 1;
        }
        to {
            transform: translateX(100%);
            opacity: 0;
        }
    }
`;
document.head.appendChild(style);
