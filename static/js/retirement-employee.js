/**
 * ============================================================================
 * WORLD-CLASS RETIREMENT SYSTEM - EMPLOYEE PAGE
 * Professional, Scalable, Maintainable JavaScript
 * ============================================================================
 */

// Global state
let currentRetirement = null;
let cancelModal = null;

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    cancelModal = new bootstrap.Modal(document.getElementById('cancelModal'));
    loadRetirementStatus();
    setupFormValidation();
    setupEventListeners();
});

/**
 * Load retirement status from API
 */
async function loadRetirementStatus() {
    try {
        const response = await fetch('/api/retirement/my-request/', {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        const data = await response.json();
        
        if (data.success && data.has_request) {
            currentRetirement = data.retirement;
            showStatusCard(data);
        } else {
            showRequestForm();
        }
    } catch (error) {
        console.error('Error loading retirement status:', error);
        showAlert('Error loading retirement status. Please refresh the page.', 'danger');
    }
}

/**
 * Show status card with retirement details
 */
function showStatusCard(data) {
    document.getElementById('statusCard').style.display = 'block';
    document.getElementById('requestFormCard').style.display = 'none';
    
    // Update status badge
    const statusBadgeContainer = document.getElementById('statusBadgeContainer');
    const statusClass = `status-${data.retirement.status.toLowerCase().replace(/ /g, '_')}`;
    statusBadgeContainer.innerHTML = `
        <span class="status-badge ${statusClass}">
            <i class="bi bi-circle-fill"></i>
            ${data.retirement.status_display}
        </span>
    `;
    
    // Update metrics
    updateMetrics(data.retirement);
    
    // Update request details
    updateRequestDetails(data.retirement);
    
    // Update timeline
    updateTimeline(data.timeline || []);
    
    // Update assets
    if (data.assets && data.assets.length > 0) {
        updateAssets(data.assets);
    }
    
    // Show/hide actions based on status
    const actionsCard = document.getElementById('actionsCard');
    if (data.retirement.status === 'requested' || data.retirement.status === 'pending_approval') {
        actionsCard.style.display = 'block';
    } else {
        actionsCard.style.display = 'none';
    }
}

/**
 * Show request form
 */
function showRequestForm() {
    document.getElementById('statusCard').style.display = 'none';
    document.getElementById('requestFormCard').style.display = 'block';
}

/**
 * Update metrics cards
 */
function updateMetrics(retirement) {
    const metricsRow = document.getElementById('metricsRow');
    
    const metrics = [
        {
            icon: 'calendar-event',
            iconClass: 'primary',
            value: retirement.days_until_effective !== null ? retirement.days_until_effective : 'N/A',
            label: 'Days Until Effective',
            suffix: retirement.days_until_effective !== null ? ' days' : ''
        },
        {
            icon: 'box-seam',
            iconClass: 'warning',
            value: retirement.asset_count || 0,
            label: 'Assigned Assets',
            suffix: ' assets'
        },
        {
            icon: 'clock-history',
            iconClass: 'info',
            value: retirement.duration_days || 0,
            label: 'Days Since Request',
            suffix: ' days'
        }
    ];
    
    if (retirement.status === 'in_progress') {
        metrics.push({
            icon: 'check-circle',
            iconClass: 'success',
            value: retirement.assets_return_progress || 0,
            label: 'Assets Returned',
            suffix: '%'
        });
    }
    
    const colClass = retirement.status === 'in_progress' ? 'col-md-3' : 'col-md-4';
    
    metricsRow.innerHTML = metrics.map(metric => `
        <div class="${colClass}">
            <div class="metric-card">
                <div class="metric-icon ${metric.iconClass}">
                    <i class="bi bi-${metric.icon}"></i>
                </div>
                <div class="metric-value">${metric.value}${metric.suffix}</div>
                <div class="metric-label">${metric.label}</div>
            </div>
        </div>
    `).join('');
}

/**
 * Update request details
 */
function updateRequestDetails(retirement) {
    const details = document.getElementById('requestDetails');
    
    const rows = [
        { label: 'Request Date', value: new Date(retirement.request_date).toLocaleDateString() },
        { label: 'Effective Date', value: new Date(retirement.effective_date).toLocaleDateString() },
        { label: 'Reason Category', value: retirement.reason_category_display },
        { label: 'Reason', value: retirement.reason, fullWidth: true }
    ];
    
    if (retirement.notes) {
        rows.push({ label: 'Additional Notes', value: retirement.notes, fullWidth: true });
    }
    
    if (retirement.approval_notes) {
        rows.push({ label: 'Approval Notes', value: retirement.approval_notes, fullWidth: true });
    }
    
    if (retirement.rejection_reason) {
        rows.push({ label: 'Rejection Reason', value: retirement.rejection_reason, fullWidth: true });
    }
    
    details.innerHTML = rows.map(row => {
        if (row.fullWidth) {
            return `
                <div class="mb-3">
                    <div class="info-label mb-2">${row.label}</div>
                    <div class="info-value text-start">${escapeHtml(row.value)}</div>
                </div>
            `;
        }
        return `
            <div class="info-row">
                <span class="info-label">${row.label}</span>
                <span class="info-value">${escapeHtml(row.value)}</span>
            </div>
        `;
    }).join('');
}

/**
 * Update timeline
 */
function updateTimeline(timeline) {
    const container = document.getElementById('timelineContainer');
    
    if (timeline.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <i class="bi bi-clock-history"></i>
                <p>No timeline events yet</p>
            </div>
        `;
        return;
    }
    
    container.innerHTML = timeline.map(event => `
        <div class="timeline-item">
            <div class="timeline-dot"></div>
            <div class="timeline-content">
                <div class="d-flex justify-content-between align-items-start mb-2">
                    <strong style="color: var(--accent-primary);">${escapeHtml(event.title)}</strong>
                    <small class="text-muted">${new Date(event.date).toLocaleDateString()}</small>
                </div>
                <p class="mb-0 text-muted">${escapeHtml(event.description)}</p>
            </div>
        </div>
    `).join('');
}

/**
 * Update assets list
 */
function updateAssets(assets) {
    const assetsCard = document.getElementById('assetsCard');
    const assetsList = document.getElementById('assetsList');
    
    assetsCard.style.display = 'block';
    
    assetsList.innerHTML = assets.map(asset => `
        <div class="asset-card">
            <div class="d-flex justify-content-between align-items-start">
                <div>
                    <strong>${escapeHtml(asset.name)}</strong>
                    <div class="text-muted small">${escapeHtml(asset.asset_tag)}</div>
                </div>
                <span class="badge bg-secondary">${escapeHtml(asset.status)}</span>
            </div>
        </div>
    `).join('');
}

/**
 * Setup form validation
 */
function setupFormValidation() {
    const reasonTextarea = document.getElementById('reason');
    const charCount = document.getElementById('reasonCharCount');
    
    if (reasonTextarea && charCount) {
        reasonTextarea.addEventListener('input', function() {
            const length = this.value.length;
            charCount.textContent = `${length} / 10 characters minimum`;
            
            if (length >= 10) {
                charCount.style.color = 'var(--accent-success)';
            } else {
                charCount.style.color = '#6b7280';
            }
        });
    }
}

/**
 * Setup event listeners
 */
function setupEventListeners() {
    // Form submission
    const form = document.getElementById('retirementRequestForm');
    if (form) {
        form.addEventListener('submit', handleFormSubmit);
    }
    
    // Cancel request button
    const cancelBtn = document.getElementById('cancelRequestBtn');
    if (cancelBtn) {
        cancelBtn.addEventListener('click', function() {
            cancelModal.show();
        });
    }
    
    // Confirm cancel button
    const confirmCancelBtn = document.getElementById('confirmCancelBtn');
    if (confirmCancelBtn) {
        confirmCancelBtn.addEventListener('click', handleCancelRequest);
    }
}

/**
 * Handle form submission
 */
async function handleFormSubmit(e) {
    e.preventDefault();
    
    const submitBtn = document.getElementById('submitBtn');
    const originalText = submitBtn.innerHTML;
    
    // Disable button and show loading
    submitBtn.disabled = true;
    submitBtn.innerHTML = '<span class="loading-spinner"></span> Submitting...';
    
    try {
        const data = {
            effective_date: document.getElementById('effectiveDate').value,
            reason_category: document.getElementById('reasonCategory').value,
            reason: document.getElementById('reason').value,
            notes: document.getElementById('notes').value
        };
        
        const response = await fetch('/api/retirement/request/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify(data)
        });
        
        const result = await response.json();
        
        if (result.success) {
            showAlert(result.message || 'Retirement request submitted successfully!', 'success');
            
            // Reload status after 1.5 seconds
            setTimeout(() => {
                loadRetirementStatus();
            }, 1500);
        } else {
            showAlert(result.error || 'Failed to submit request', 'danger');
            submitBtn.disabled = false;
            submitBtn.innerHTML = originalText;
        }
    } catch (error) {
        console.error('Error submitting request:', error);
        showAlert('An error occurred. Please try again.', 'danger');
        submitBtn.disabled = false;
        submitBtn.innerHTML = originalText;
    }
}

/**
 * Handle cancel request
 */
async function handleCancelRequest() {
    const reason = document.getElementById('cancelReason').value.trim();
    
    if (reason.length < 10) {
        showAlert('Cancellation reason must be at least 10 characters', 'warning');
        return;
    }
    
    const confirmBtn = document.getElementById('confirmCancelBtn');
    const originalText = confirmBtn.innerHTML;
    
    confirmBtn.disabled = true;
    confirmBtn.innerHTML = '<span class="loading-spinner"></span> Cancelling...';
    
    try {
        const response = await fetch('/api/retirement/cancel/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify({
                retirement_id: currentRetirement.id,
                reason: reason
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            cancelModal.hide();
            showAlert(result.message || 'Request cancelled successfully', 'success');
            
            setTimeout(() => {
                window.location.reload();
            }, 1500);
        } else {
            showAlert(result.error || 'Failed to cancel request', 'danger');
            confirmBtn.disabled = false;
            confirmBtn.innerHTML = originalText;
        }
    } catch (error) {
        console.error('Error cancelling request:', error);
        showAlert('An error occurred. Please try again.', 'danger');
        confirmBtn.disabled = false;
        confirmBtn.innerHTML = originalText;
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
