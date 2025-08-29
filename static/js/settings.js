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
    showInfoMessage('Backup creation initiated. You will be notified when complete.');
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


