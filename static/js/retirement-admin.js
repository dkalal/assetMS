/**
 * ============================================================================
 * WORLD-CLASS RETIREMENT SYSTEM - ADMIN APPROVAL CENTER
 * Professional, Scalable, Maintainable JavaScript
 * ============================================================================
 */

// Global state
let currentRetirementId = null;
let allRequests = [];
let approvedRequests = [];
let approveModal = null;
let rejectModal = null;

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    approveModal = new bootstrap.Modal(document.getElementById('approveModal'));
    rejectModal = new bootstrap.Modal(document.getElementById('rejectModal'));
    
    loadDashboardStats();
    loadPendingApprovals();
    loadApprovedRequests();
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
 * Load approved and in-progress requests (admin processing pipeline)
 */
async function loadApprovedRequests() {
    const loading = document.getElementById('approvedLoadingState');
    const list = document.getElementById('approvedList');
    const empty = document.getElementById('approvedEmptyState');

    // Gracefully no-op if the approved section is not present
    if (!loading || !list || !empty) {
        return;
    }

    try {
        loading.style.display = 'block';
        list.style.display = 'none';
        empty.style.display = 'none';

        const response = await fetch('/api/retirement/approved-requests/');
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();

        if (data.success) {
            approvedRequests = data.requests || [];
            displayApprovedRequests(approvedRequests);
        } else {
            showAlert('Failed to load approved requests: ' + (data.error || 'Unknown error'), 'danger');
            empty.style.display = 'block';
        }
    } catch (error) {
        console.error('Error loading approved requests:', error);
        showAlert('Error loading approved retirement requests: ' + error.message, 'danger');
        empty.style.display = 'block';
    } finally {
        loading.style.display = 'none';
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
 * Display approved & in-progress requests (read-only cards)
 */
function displayApprovedRequests(requests) {
    const container = document.getElementById('approvedList');
    const emptyState = document.getElementById('approvedEmptyState');

    if (!container || !emptyState) {
        return;
    }

    if (!Array.isArray(requests) || requests.length === 0) {
        emptyState.style.display = 'block';
        container.style.display = 'none';
        return;
    }

    emptyState.style.display = 'none';
    container.style.display = 'block';

    const cards = requests.map(request => {
        try {
            const userName = request.user?.name || request.user_name || 'Unknown User';
            const userEmail = request.user?.email || request.user_email || 'No email';
            const userRole = request.user?.role || request.user_role || '';

            const nameParts = userName.split(' ').filter(part => part.length > 0);
            const initials = nameParts.length > 1
                ? nameParts[0][0] + nameParts[nameParts.length - 1][0]
                : (nameParts[0]?.[0] || 'U');

            const effectiveDate = request.effective_date
                ? new Date(request.effective_date)
                : null;
            const requestDate = request.request_date
                ? new Date(request.request_date)
                : null;

            const statusLabel = request.status_display || request.status || 'Approved';

            const daysUntil = typeof request.days_until_effective === 'number'
                ? request.days_until_effective
                : (effectiveDate
                    ? Math.max(0, Math.ceil((effectiveDate - new Date()) / (1000 * 60 * 60 * 24)))
                    : null);

            return `
                <div class="request-card request-card--approved">
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
                        <div class="ms-auto">
                            <span class="badge bg-success-subtle text-success">
                                <i class="bi bi-check2-circle me-1"></i>${escapeHtml(statusLabel)}
                            </span>
                        </div>
                    </div>

                    <div class="request-card-body">
                        <div class="request-info-item">
                            <div class="request-info-label">
                                <i class="bi bi-calendar-event"></i>
                                Request Date
                            </div>
                            <div class="request-info-value">
                                ${requestDate ? requestDate.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' }) : '—'}
                            </div>
                        </div>
                        <div class="request-info-item">
                            <div class="request-info-label">
                                <i class="bi bi-calendar-check"></i>
                                Effective Date
                            </div>
                            <div class="request-info-value">
                                ${effectiveDate ? effectiveDate.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' }) : '—'}
                            </div>
                        </div>
                        <div class="request-info-item">
                            <div class="request-info-label">
                                <i class="bi bi-hourglass-split"></i>
                                Days Until
                            </div>
                            <div class="request-info-value">
                                ${daysUntil !== null ? `${daysUntil} days` : '—'}
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

                    <div class="request-reason-section">
                        <div class="request-reason-label">
                            <i class="bi bi-chat-left-text"></i>
                            Retirement Reason
                        </div>
                        <p class="request-reason-text">
                            ${escapeHtml(request.reason || '')}
                        </p>
                    </div>
                </div>
            `;
        } catch (error) {
            console.error('Error rendering approved request card:', error, request);
            return `
                <div class="request-card">
                    <div class="alert alert-warning mb-0">
                        <i class="bi bi-exclamation-triangle me-2"></i>
                        Error displaying approved request. Please contact support.
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
    const searchInput = document.getElementById('searchInput');
    const statusSelect = document.getElementById('statusFilter');
    const sortSelect = document.getElementById('sortBy');

    const searchTerm = (searchInput?.value || '').toLowerCase();
    const statusFilter = statusSelect?.value || '';
    const sortBy = sortSelect?.value || 'newest';

    const applyFilters = (requests) => {
        let filtered = Array.isArray(requests) ? [...requests] : [];

        if (searchTerm) {
            filtered = filtered.filter(request => {
                const userName = request.user?.name || request.user_name || '';
                const userEmail = request.user?.email || request.user_email || '';
                return userName.toLowerCase().includes(searchTerm) ||
                       userEmail.toLowerCase().includes(searchTerm);
            });
        }

        if (statusFilter) {
            filtered = filtered.filter(request => request.status === statusFilter);
        }

        if (sortBy === 'newest') {
            filtered.sort((a, b) => new Date(b.request_date) - new Date(a.request_date));
        } else if (sortBy === 'oldest') {
            filtered.sort((a, b) => new Date(a.request_date) - new Date(b.request_date));
        } else if (sortBy === 'effective_date') {
            filtered.sort((a, b) => new Date(a.effective_date) - new Date(b.effective_date));
        }

        return filtered;
    };

    // Apply filters to both pending and approved datasets
    const filteredPending = applyFilters(allRequests);
    const filteredApproved = applyFilters(approvedRequests);

    displayRequests(filteredPending);
    displayApprovedRequests(filteredApproved);
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
