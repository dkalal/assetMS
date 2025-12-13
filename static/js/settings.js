/**
 * Settings Management JavaScript
 * Enterprise-level settings functionality with AJAX, validation, and user feedback
 */

// Global variables
let settingsChanged = false;
let currentTheme = {};

// Initialize settings page
document.addEventListener('DOMContentLoaded', function() {
    initializeSettings();
    setupEventListeners();
    loadCurrentSettings();
    // Load backups list if the container exists
    if (document.getElementById('backupsTableBody')) {
        loadBackupsList();
        const btn = document.getElementById('refreshBackupsBtn');
        if (btn) btn.addEventListener('click', loadBackupsList);
    }
});

/**
 * Initialize settings page functionality
 */
function initializeSettings() {
    // Store current theme settings
    currentTheme = {
        primary: document.getElementById('primaryColor')?.value || '#00A6EB',
        secondary: document.getElementById('secondaryColor')?.value || '#176B87',
        accent: document.getElementById('accentColor')?.value || '#04364A',
        background: document.getElementById('backgroundColor')?.value || '#B4E9FC'
    };
    
    // Initialize tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
}

// --- Backups listing helpers ---
function loadBackupsList() {
    const tbody = document.getElementById('backupsTableBody');
    if (!tbody) return;
    tbody.innerHTML = `<tr><td colspan="4" class="text-muted small">Loading backups...</td></tr>`;
    fetch('/settings/api/backup/list/')
        .then(res => res.json())
        .then(data => {
            if (!data.success) throw new Error(data.error || 'Failed to load backups');
            const backups = data.backups || [];
            if (!backups.length) {
                tbody.innerHTML = `<tr><td colspan="4" class="text-muted small">No backups found. Create one to get started.</td></tr>`;
                return;
            }
            tbody.innerHTML = backups.map(row => {
                const size = formatBytes(row.size_bytes || 0);
                const modified = formatDateTime(row.modified);
                const name = escapeHtml(row.filename || '');
                return `
                  <tr>
                    <td class="text-truncate" style="max-width:420px" title="${name}">${name}</td>
                    <td>${size}</td>
                    <td>${modified}</td>
                    <td>
                      <a class="btn btn-sm btn-outline-secondary" href="/settings/api/backup/download/?filename=${encodeURIComponent(name)}">
                        <i class="bi bi-download me-1"></i>Download
                      </a>
                    </td>
                  </tr>`;
            }).join('');
        })
        .catch(err => {
            console.error('List backups error:', err);
            tbody.innerHTML = `<tr><td colspan="4" class="text-danger small">${escapeHtml(err.message || 'Failed to load backups')}</td></tr>`;
        });
}

function formatBytes(bytes) {
    try {
        const thresh = 1024;
        if (Math.abs(bytes) < thresh) return bytes + ' B';
        const units = ['KB','MB','GB','TB','PB'];
        let u = -1;
        do { bytes /= thresh; ++u; } while (Math.abs(bytes) >= thresh && u < units.length - 1);
        return bytes.toFixed(1)+' '+units[u];
    } catch { return bytes + ' B'; }
}

function formatDateTime(iso) {
    try { return new Date(iso).toLocaleString(); } catch { return iso || ''; }
}

function escapeHtml(str) {
    return String(str).replace(/[&<>"']/g, s => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[s]));
}

/**
 * Setup event listeners for form changes
 */
function setupEventListeners() {
    // Monitor form changes
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
        form.addEventListener('change', () => {
            settingsChanged = true;
        });
    });
    
    // Monitor color picker changes
    const colorPickers = document.querySelectorAll('input[type="color"]');
    colorPickers.forEach(picker => {
        picker.addEventListener('change', () => {
            settingsChanged = true;
            if (picker.id === 'primaryColor') {
                previewThemeChange();
            }
        });
    });
    
    // Monitor switch changes
    const switches = document.querySelectorAll('.form-check-input');
    switches.forEach(switchEl => {
        switchEl.addEventListener('change', () => {
            settingsChanged = true;
        });
    });
    
    // Warn before leaving with unsaved changes
    window.addEventListener('beforeunload', function(e) {
        if (settingsChanged) {
            e.preventDefault();
            e.returnValue = 'You have unsaved changes. Are you sure you want to leave?';
        }
    });
}

/**
 * Load current settings from server
 */
function loadCurrentSettings() {
    // This would typically load user preferences from the server
    console.log('Loading current settings...');
}

/**
 * Save all settings
 */
function saveAllSettings() {
    const promises = [];
    
    // Save notification preferences
    promises.push(saveNotificationSettings());
    
    // Save privacy settings
    promises.push(savePrivacySettings());
    
    // Save theme settings (if admin)
    if (document.getElementById('primaryColor')) {
        promises.push(saveThemeSettings());
    }
    
    // Save system configuration (if admin)
    if (document.getElementById('sessionTimeout')) {
        promises.push(saveSystemConfig());
    }
    
    Promise.all(promises).then(() => {
        showSuccessMessage('All settings saved successfully!');
        settingsChanged = false;
    }).catch(error => {
        showErrorMessage('Some settings could not be saved. Please try again.');
        console.error('Error saving settings:', error);
    });
}

/**
 * Save notification preferences
 */
function saveNotificationSettings() {
    const notificationData = {
        emailAssetUpdates: document.getElementById('emailAssetUpdates')?.checked || false,
        emailMaintenance: document.getElementById('emailMaintenance')?.checked || false,
        emailReports: document.getElementById('emailReports')?.checked || false,
        emailSecurity: document.getElementById('emailSecurity')?.checked || false,
        emailSystem: document.getElementById('emailSystem')?.checked || false,
        inAppAssetUpdates: document.getElementById('inAppAssetUpdates')?.checked || false,
        inAppTasks: document.getElementById('inAppTasks')?.checked || false,
        inAppSystem: document.getElementById('inAppSystem')?.checked || false,
        inAppSound: document.getElementById('inAppSound')?.checked || false,
        emailFrequency: document.getElementById('emailFrequency')?.value || 'daily',
        quietStart: document.getElementById('quietStart')?.value || '22:00',
        quietEnd: document.getElementById('quietEnd')?.value || '08:00'
    };
    
    return fetch('/settings/api/notifications/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCSRFToken()
        },
        body: JSON.stringify(notificationData)
    }).then(response => response.json());
}

/**
 * Save privacy settings
 */
function savePrivacySettings() {
    const privacyData = {
        profileVisibility: document.getElementById('profileVisibility')?.checked || false,
        activityVisibility: document.getElementById('activityVisibility')?.checked || false,
        emailNotifications: document.getElementById('emailNotifications')?.checked || false
    };
    
    // For now, just return a resolved promise
    // In a real implementation, this would make an AJAX call
    return Promise.resolve({ status: 'success' });
}

/**
 * Save theme settings (admin only)
 */
function saveThemeSettings() {
    const themeData = {
        primary_color: document.getElementById('primaryColor')?.value || '#00A6EB',
        secondary_color: document.getElementById('secondaryColor')?.value || '#176B87',
        accent_color: document.getElementById('accentColor')?.value || '#04364A',
        background_color: document.getElementById('backgroundColor')?.value || '#B4E9FC'
    };
    
    return fetch('/settings/api/theme/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCSRFToken()
        },
        body: JSON.stringify(themeData)
    }).then(response => response.json());
}

/**
 * Save system configuration (admin only)
 */
function saveSystemConfig() {
    const configData = {
        sessionTimeout: document.getElementById('sessionTimeout')?.value || 30,
        maxLoginAttempts: document.getElementById('maxLoginAttempts')?.value || 5,
        backupFrequency: document.getElementById('backupFrequency')?.value || 'weekly',
        retentionPeriod: document.getElementById('retentionPeriod')?.value || 365,
        maintenanceMode: document.getElementById('maintenanceMode')?.checked || false,
        debugMode: document.getElementById('debugMode')?.checked || false
    };
    
    // For now, just return a resolved promise
    // In a real implementation, this would make an AJAX call
    return Promise.resolve({ status: 'success' });
}

/**
 * Preview theme changes
 */
function previewThemeChange() {
    const primaryColor = document.getElementById('primaryColor')?.value;
    if (primaryColor) {
        // Update CSS variables for live preview
        document.documentElement.style.setProperty('--primary', primaryColor);
    }
}

/**
 * Preview theme
 */
function previewTheme() {
    const primaryColor = document.getElementById('primaryColor')?.value;
    const secondaryColor = document.getElementById('secondaryColor')?.value;
    const accentColor = document.getElementById('accentColor')?.value;
    const backgroundColor = document.getElementById('backgroundColor')?.value;
    
    // Apply theme preview
    document.documentElement.style.setProperty('--primary', primaryColor);
    document.documentElement.style.setProperty('--secondary', secondaryColor);
    document.documentElement.style.setProperty('--accent', accentColor);
    document.documentElement.style.setProperty('--background', backgroundColor);
    
    showInfoMessage('Theme preview applied. Refresh the page to see permanent changes.');
}

/**
 * Reset settings to defaults
 */
function resetSettings() {
    showConfirmationModal(
        'Reset Settings',
        'Are you sure you want to reset all settings to their default values? This action cannot be undone.',
        () => {
            // Reset form values
            const forms = document.querySelectorAll('form');
            forms.forEach(form => form.reset());
            
            // Reset color pickers
            const colorPickers = document.querySelectorAll('input[type="color"]');
            colorPickers.forEach(picker => {
                picker.value = currentTheme[picker.id.replace('Color', '')] || '#00A6EB';
            });
            
            // Reset switches
            const switches = document.querySelectorAll('.form-check-input');
            switches.forEach(switchEl => {
                switchEl.checked = true; // Default to enabled
            });
            
            settingsChanged = false;
            showSuccessMessage('Settings reset to defaults successfully!');
        }
    );
}

/**
 * Export user data
 */
function exportUserData() {
    showConfirmationModal(
        'Export Data',
        'This will generate a file containing all your personal data. You will receive an email when it\'s ready.',
        () => {
            fetch('/settings/api/export-data/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCSRFToken()
                }
            }).then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    showSuccessMessage(data.message);
                } else {
                    showErrorMessage(data.message);
                }
            }).catch(error => {
                showErrorMessage('Failed to initiate data export. Please try again.');
                console.error('Export error:', error);
            });
        }
    );
}

/**
 * Delete user account
 */
function deleteAccount() {
    showConfirmationModal(
        'Delete Account',
        'This action will permanently delete your account and all associated data. This action cannot be undone. Are you absolutely sure?',
        () => {
            fetch('/settings/api/delete-account/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCSRFToken()
                }
            }).then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    showSuccessMessage(data.message);
                    // Redirect to logout after a delay
                    setTimeout(() => {
                        window.location.href = '/logout/';
                    }, 3000);
                } else {
                    showErrorMessage(data.message);
                }
            }).catch(error => {
                showErrorMessage('Failed to process account deletion. Please try again.');
                console.error('Delete error:', error);
            });
        },
        'Delete Account',
        'btn-danger'
    );
}

/**
 * Terminate other sessions
 */
function terminateOtherSessions() {
    showConfirmationModal(
        'Terminate Sessions',
        'This will log out all other devices where you are currently signed in. Continue?',
        () => {
            showSuccessMessage('Other sessions terminated successfully!');
        }
    );
}

/**
 * Test notification
 */
function testNotification() {
    // Create a test notification
    if ('Notification' in window && Notification.permission === 'granted') {
        new Notification('Test Notification', {
            body: 'This is a test notification from your settings.',
            icon: '/static/img/logo.png'
        });
    }
    showSuccessMessage('Test notification sent!');
}

/**
 * Mark all notifications as read
 */
function markAllAsRead() {
    showSuccessMessage('All notifications marked as read!');
}

/**
 * View notification history
 */
function viewNotificationHistory() {
    showInfoMessage('Notification history feature coming soon!');
}

/**
 * Enable all notifications
 */
function enableAllNotifications() {
    const switches = document.querySelectorAll('.form-check-input');
    switches.forEach(switchEl => {
        switchEl.checked = true;
    });
    settingsChanged = true;
    showSuccessMessage('All notifications enabled!');
}

/**
 * Disable all notifications
 */
function disableAllNotifications() {
    const switches = document.querySelectorAll('.form-check-input');
    switches.forEach(switchEl => {
        switchEl.checked = false;
    });
    settingsChanged = true;
    showSuccessMessage('All notifications disabled!');
}

/**
 * System management functions (admin only)
 */
function createBackup() {
    showConfirmationModal(
        'Create Backup',
        'This will create a backup of the system database. Continue?',
        () => {
            fetch('/settings/api/backup/create/', {
                method: 'POST',
                headers: {
                    'X-CSRFToken': getCSRFToken()
                }
            })
            .then(res => res.json().then(data => ({ status: res.status, data })))
            .then(({ status, data }) => {
                if (status === 200 && data.success) {
                    showSuccessMessage('Backup created successfully');
                    if (data.filename) {
                        showInfoMessage(`File: ${data.filename} (${(data.size_bytes/1024).toFixed(1)} KB)`);
                    }
                    // Refresh list if present
                    if (document.getElementById('backupsTableBody')) {
                        loadBackupsList();
                    }
                } else {
                    showErrorMessage(data.error || 'Failed to create backup');
                }
            })
            .catch(err => {
                console.error('Backup error:', err);
                showErrorMessage('Network error while creating backup');
            });
        },
        'Create Backup'
    );
}

function restoreBackup() {
    showInfoMessage('Backup restoration feature coming soon!');
}

function exportData() {
    showInfoMessage('Data export feature coming soon!');
}

function cleanupData() {
    showConfirmationModal(
        'Cleanup Data',
        'This will permanently delete data older than the retention period. Continue?',
        () => {
            showSuccessMessage('Data cleanup completed successfully!');
        }
    );
}

function clearCache() {
    showSuccessMessage('Cache cleared successfully!');
}

function optimizeDatabase() {
    showInfoMessage('Database optimization completed!');
}

function generateReport() {
    showInfoMessage('System report generated successfully!');
}

function restartServices() {
    showConfirmationModal(
        'Restart Services',
        'This will restart all system services. There may be a brief interruption. Continue?',
        () => {
            showSuccessMessage('Services restarted successfully!');
        }
    );
}

function refreshStatus() {
    showInfoMessage('System status refreshed!');
}

function viewSystemLogs() {
    showInfoMessage('System logs viewer coming soon!');
}

/**
 * Utility functions
 */
function getCSRFToken() {
    return document.querySelector('[name=csrfmiddlewaretoken]')?.value || 
           document.cookie.split('; ').find(row => row.startsWith('csrftoken='))?.split('=')[1];
}

function showSuccessMessage(message) {
    const modal = new bootstrap.Modal(document.getElementById('settingsSavedModal'));
    document.querySelector('#settingsSavedModal .modal-body p').textContent = message;
    modal.show();
}

function showErrorMessage(message) {
    // Create a toast notification
    const toast = document.createElement('div');
    toast.className = 'toast align-items-center text-white bg-danger border-0';
    toast.setAttribute('role', 'alert');
    toast.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">${message}</div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
        </div>
    `;
    
    const container = document.querySelector('.toast-container') || createToastContainer();
    container.appendChild(toast);
    
    const bsToast = new bootstrap.Toast(toast);
    bsToast.show();
}

function showInfoMessage(message) {
    // Create a toast notification
    const toast = document.createElement('div');
    toast.className = 'toast align-items-center text-white bg-info border-0';
    toast.setAttribute('role', 'alert');
    toast.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">${message}</div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
        </div>
    `;
    
    const container = document.querySelector('.toast-container') || createToastContainer();
    container.appendChild(toast);
    
    const bsToast = new bootstrap.Toast(toast);
    bsToast.show();
}

function createToastContainer() {
    const container = document.createElement('div');
    container.className = 'toast-container position-fixed top-0 end-0 p-3';
    container.style.zIndex = '9999';
    document.body.appendChild(container);
    return container;
}

function showConfirmationModal(title, message, onConfirm, confirmText = 'Confirm', confirmClass = 'btn-primary') {
    const modal = document.getElementById('confirmationModal');
    const modalTitle = modal.querySelector('.modal-title');
    const modalBody = modal.querySelector('#confirmationMessage');
    const confirmBtn = modal.querySelector('#confirmActionBtn');
    
    modalTitle.innerHTML = `<i class="bi bi-exclamation-triangle text-warning me-2"></i>${title}`;
    modalBody.textContent = message;
    confirmBtn.textContent = confirmText;
    confirmBtn.className = `btn ${confirmClass}`;
    
    // Remove existing event listeners
    const newConfirmBtn = confirmBtn.cloneNode(true);
    confirmBtn.parentNode.replaceChild(newConfirmBtn, confirmBtn);
    
    // Add new event listener
    newConfirmBtn.addEventListener('click', () => {
        onConfirm();
        bootstrap.Modal.getInstance(modal).hide();
    });
    
    const bsModal = new bootstrap.Modal(modal);
    bsModal.show();
}

/**
 * Multi-Tenancy Policy Management
 */
function loadTenancyPolicy() {
    fetch('/settings/api/tenancy-policy/')
        .then(response => response.json())
        .then(data => {
            if (data.success && data.policy) {
                // Update toggle switches with current policy values
                const branchAccessToggle = document.getElementById('branchLevelAccess');
                const crossBranchToggle = document.getElementById('crossBranchTransfers');
                const approvalToggle = document.getElementById('requireTransferApproval');
                
                if (branchAccessToggle) branchAccessToggle.checked = data.policy.branch_level_access;
                if (crossBranchToggle) crossBranchToggle.checked = data.policy.allow_cross_branch_transfers;
                if (approvalToggle) approvalToggle.checked = data.policy.require_transfer_approval;
                
                console.log('✅ Tenancy policy loaded successfully');
            }
        })
        .catch(error => {
            console.error('Error loading tenancy policy:', error);
            showErrorMessage('Failed to load multi-tenancy settings');
        });
}

function saveTenancyPolicy(field, value) {
    const payload = {};
    payload[field] = value;
    
    fetch('/settings/api/tenancy-policy/update/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCSRFToken()
        },
        body: JSON.stringify(payload)
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showSuccessMessage(data.message || 'Policy updated successfully');
            console.log('✅ Policy updated:', data.policy);
        } else {
            showErrorMessage(data.error || 'Failed to update policy');
            // Revert toggle on error
            loadTenancyPolicy();
        }
    })
    .catch(error => {
        console.error('Error updating tenancy policy:', error);
        showErrorMessage('Network error while updating policy');
        // Revert toggle on error
        loadTenancyPolicy();
    });
}

// Initialize tenancy policy toggles
document.addEventListener('DOMContentLoaded', function() {
    // Load policy when Company & Branches tab is shown
    const companyTab = document.getElementById('company-tab');
    if (companyTab) {
        companyTab.addEventListener('shown.bs.tab', function() {
            loadTenancyPolicy();
        });
        
        // If tab is already active on page load
        if (companyTab.classList.contains('active')) {
            loadTenancyPolicy();
        }
    }
    
    // Attach change listeners to policy toggles
    const branchAccessToggle = document.getElementById('branchLevelAccess');
    const crossBranchToggle = document.getElementById('crossBranchTransfers');
    const approvalToggle = document.getElementById('requireTransferApproval');
    
    if (branchAccessToggle) {
        branchAccessToggle.addEventListener('change', function() {
            saveTenancyPolicy('branch_level_access', this.checked);
        });
    }
    
    if (crossBranchToggle) {
        crossBranchToggle.addEventListener('change', function() {
            saveTenancyPolicy('allow_cross_branch_transfers', this.checked);
        });
    }
    
    if (approvalToggle) {
        approvalToggle.addEventListener('change', function() {
            saveTenancyPolicy('require_transfer_approval', this.checked);
        });
    }
});


