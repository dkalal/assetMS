/**
 * WORLD-CLASS DUPLICATE DETECTION UI COMPONENT
 * 
 * Real-time duplicate detection with intelligent UX:
 * - Debounced input validation (500ms)
 * - Progressive enhancement (works without JS)  
 * - Visual feedback with icons and colors
 * - Non-blocking warnings with user override
 * - Accessibility compliant (WCAG 2.1 AA)
 * 
 * Inspired by:
 * - ServiceNow ITAM form validation
 * - IBM Maximo duplicate warnings
 * - SAP EAM real-time checks
 */

class DuplicateDetector {
    constructor(options = {}) {
        this.options = {
            // API endpoint for duplicate checking
            apiUrl: '/assets/api/check-duplicates/',
            
            // Fields to monitor for duplicates
            watchFields: ['serial_number', 'asset_tag', 'qr_string'],
            
            // Debounce delay in milliseconds
            debounceDelay: 500,
            
            // Form selector
            formSelector: '#asset-form',
            
            // Category field selector
            categoryFieldSelector: '#id_category',
            
            // CSRF token name
            csrfTokenName: 'csrfmiddlewaretoken',
            
            ...options
        };
        
        this.form = document.querySelector(this.options.formSelector);
        this.categoryField = document.querySelector(this.options.categoryFieldSelector);
        this.debounceTimers = {};
        this.lastCheckData = {};
        this.duplicateWarnings = [];
        
        if (this.form) {
            this.init();
        }
    }
    
    init() {
        console.log('🔍 Initializing world-class duplicate detection...');
        
        // Setup field monitoring for both static and dynamic fields
        this.attachFieldListeners();
        
        // Monitor for dynamic field changes
        this.monitorDynamicFields();
        
        // Setup form submission handling
        this.setupFormSubmission();
        
        console.log('✅ Duplicate detection initialized successfully');
        console.log('🔍 Monitoring: Static fields + Dynamic category fields');
    }
    
    attachFieldListeners() {
        // Monitor both static fields (#id_serial_number) and dynamic fields (#id_dyn_serial_number)
        this.options.watchFields.forEach(fieldName => {
            // Try static field first
            let field = this.form.querySelector(`#id_${fieldName}`);
            
            // If not found, try dynamic field (category-specific)
            if (!field) {
                field = this.form.querySelector(`#id_dyn_${fieldName}`);
            }
            
            // If still not found, try by name attribute
            if (!field) {
                field = this.form.querySelector(`[name="${fieldName}"]`) ||
                        this.form.querySelector(`[name="dyn_${fieldName}"]`);
            }
            
            if (field && !field.hasAttribute('data-duplicate-monitored')) {
                console.log(`✅ Attaching duplicate detection to field: ${fieldName} (ID: ${field.id})`);
                this.setupFieldMonitoring(field, fieldName);
                this.createFeedbackElements(field, fieldName);
                field.setAttribute('data-duplicate-monitored', 'true');
            }
        });
    }
    
    monitorDynamicFields() {
        // Watch for dynamic field changes (when category changes)
        const observer = new MutationObserver((mutations) => {
            mutations.forEach((mutation) => {
                if (mutation.type === 'childList' && mutation.addedNodes.length > 0) {
                    // New fields added, re-scan and attach
                    console.log('🔄 Dynamic fields changed, re-scanning for duplicate detection fields...');
                    this.attachFieldListeners();
                }
            });
        });
        
        // Observe dynamic fields container
        const dynamicContainer = document.getElementById('dynamic-fields-container');
        if (dynamicContainer) {
            observer.observe(dynamicContainer, {
                childList: true,
                subtree: true
            });
            console.log('✅ Dynamic field monitoring active');
        }
        
        // Also listen to category changes to immediately scan
        if (this.categoryField) {
            this.categoryField.addEventListener('change', () => {
                console.log('🔄 Category changed, will re-scan for duplicate fields after dynamic fields load...');
                // Wait for dynamic fields to load (they're loaded via AJAX)
                setTimeout(() => {
                    this.attachFieldListeners();
                }, 500);
            });
        }
    }
    
    setupFieldMonitoring(field, fieldName) {
        // Monitor input changes with debouncing
        field.addEventListener('input', (e) => {
            this.debounceCheck(fieldName);
        });
        
        // Also check on blur for immediate feedback
        field.addEventListener('blur', (e) => {
            if (e.target.value.trim()) {
                this.checkDuplicates();
            }
        });
    }
    
    createFeedbackElements(field, fieldName) {
        // Create feedback container (even if no standard container found)
        const feedbackId = `${fieldName}_duplicate_feedback`;
        let feedbackEl = document.getElementById(feedbackId);
        
        if (!feedbackEl) {
            feedbackEl = document.createElement('div');
            feedbackEl.id = feedbackId;
            feedbackEl.className = 'duplicate-feedback mt-2';
            feedbackEl.setAttribute('aria-live', 'polite');
            feedbackEl.setAttribute('role', 'status');
            feedbackEl.style.minHeight = '24px';
            
            // Insert after the field (or after its next sibling if it's a help text)
            const nextElement = field.nextSibling;
            if (nextElement && nextElement.classList && nextElement.classList.contains('form-text')) {
                // Insert after help text
                nextElement.parentNode.insertBefore(feedbackEl, nextElement.nextSibling);
            } else {
                // Insert directly after field
                field.parentNode.insertBefore(feedbackEl, field.nextSibling);
            }
            
            console.log(`✅ Feedback element created for ${fieldName} (ID: ${feedbackId})`);
        }
        
        // Add visual indicator to field
        field.classList.add('duplicate-check-field');
        field.style.transition = 'border-color 0.3s ease, box-shadow 0.3s ease';
    }
    
    debounceCheck(fieldName) {
        // Clear existing timer
        if (this.debounceTimers[fieldName]) {
            clearTimeout(this.debounceTimers[fieldName]);
        }
        
        // Set new timer
        this.debounceTimers[fieldName] = setTimeout(() => {
            this.checkDuplicates();
        }, this.options.debounceDelay);
    }
    
    async checkDuplicates() {
        const formData = this.getFormData();
        
        // Skip if no relevant data
        if (!this.hasRelevantData(formData)) {
            this.clearAllFeedback();
            return;
        }
        
        // Skip if data hasn't changed
        const dataKey = JSON.stringify(formData);
        if (this.lastCheckData[dataKey]) {
            return;
        }
        
        try {
            this.showCheckingState();
            
            const response = await this.callDuplicateAPI(formData);
            
            if (response.success) {
                this.handleDuplicateResponse(response);
                this.lastCheckData[dataKey] = response;
            } else {
                this.showError('Error checking for duplicates. Please try again.');
            }
            
        } catch (error) {
            console.error('Duplicate check failed:', error);
            this.showError('Network error. Please check your connection.');
        } finally {
            this.hideCheckingState();
        }
    }
    
    getFormData() {
        const data = {};
        
        // Get watched fields (both static and dynamic)
        this.options.watchFields.forEach(fieldName => {
            // Try static field first
            let field = this.form.querySelector(`#id_${fieldName}`);
            
            // If not found, try dynamic field
            if (!field) {
                field = this.form.querySelector(`#id_dyn_${fieldName}`);
            }
            
            // If still not found, try by name
            if (!field) {
                field = this.form.querySelector(`[name="${fieldName}"]`) ||
                        this.form.querySelector(`[name="dyn_${fieldName}"]`);
            }
            
            if (field && field.value && field.value.trim()) {
                data[fieldName] = field.value.trim();
            }
        });
        
        // Get category ID (required for backend validation)
        if (this.categoryField && this.categoryField.value) {
            data.category_id = parseInt(this.categoryField.value);
        }
        
        // Get all other dynamic fields for comprehensive duplicate checking
        this.form.querySelectorAll('[id^="id_dyn_"]').forEach(field => {
            if (field.value && field.value.trim()) {
                const fieldName = field.id.replace('id_dyn_', '');
                // Only add if not already added by watchFields
                if (!data[fieldName]) {
                    data[fieldName] = field.value.trim();
                }
            }
        });
        
        // Get exclude ID (for edit forms)
        if (this.options.excludeAssetId) {
            data.exclude_asset_id = this.options.excludeAssetId;
        }
        
        console.log('📋 Form data collected for duplicate check:', data);
        
        return data;
    }
    
    hasRelevantData(data) {
        return this.options.watchFields.some(field => data[field]);
    }
    
    async callDuplicateAPI(data) {
        const csrfToken = this.getCSRFToken();
        
        const response = await fetch(this.options.apiUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken,
                'X-Requested-With': 'XMLHttpRequest'
            },
            body: JSON.stringify(data)
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        return await response.json();
    }
    
    getCSRFToken() {
        const csrfInput = this.form.querySelector(`[name="${this.options.csrfTokenName}"]`);
        if (csrfInput) {
            return csrfInput.value;
        }
        
        // Fallback: get from cookie
        const cookies = document.cookie.split(';');
        for (const cookie of cookies) {
            const [name, value] = cookie.trim().split('=');
            if (name === 'csrftoken') {
                return value;
            }
        }
        
        return '';
    }
    
    handleDuplicateResponse(response) {
        this.clearAllFeedback();
        
        // Handle hard constraint errors (blocking)
        if (response.has_blocking_errors) {
            this.showBlockingErrors(response.hard_constraint_errors);
        }
        
        // Handle soft duplicate warnings (non-blocking)
        if (response.has_warnings && response.potential_duplicates.length > 0) {
            this.showDuplicateWarnings(response.potential_duplicates);
        }
        
        // Show success state if no issues
        if (!response.has_blocking_errors && !response.has_warnings) {
            this.showSuccessState();
        }
    }
    
    showBlockingErrors(errors) {
        Object.keys(errors).forEach(fieldName => {
            // Find field (try static first, then dynamic)
            let field = this.form.querySelector(`#id_${fieldName}`) ||
                       this.form.querySelector(`#id_dyn_${fieldName}`) ||
                       this.form.querySelector(`[name="${fieldName}"]`) ||
                       this.form.querySelector(`[name="dyn_${fieldName}"]`);
            
            const feedbackEl = document.getElementById(`${fieldName}_duplicate_feedback`);
            
            if (field) {
                // Apply strong visual styling
                field.classList.add('is-invalid');
                field.style.borderColor = '#dc3545 !important';
                field.style.borderWidth = '3px';
                field.style.borderStyle = 'solid';
                field.style.boxShadow = '0 0 0 0.25rem rgba(220, 53, 69, 0.25)';
                
                console.log(`🚫 RED border applied to field: ${field.id || field.name}`);
            }
            
            if (feedbackEl) {
                feedbackEl.innerHTML = `
                    <div class="alert alert-danger p-2 mb-0 mt-1" role="alert" style="font-size: 0.9rem;">
                        <i class="bi bi-exclamation-triangle-fill me-2"></i>
                        <strong>Duplicate detected:</strong> ${errors[fieldName][0]}
                    </div>
                `;
                feedbackEl.style.display = 'block';
                
                console.log(`🚫 Error message displayed in element: ${feedbackEl.id}`);
            } else {
                console.warn(`⚠️ Feedback element not found: ${fieldName}_duplicate_feedback`);
            }
        });
    }
    
    showDuplicateWarnings(duplicates) {
        // Show warnings for the first duplicate field found
        const firstDuplicate = duplicates[0];
        const matchingFields = firstDuplicate.matching_fields || [];
        
        matchingFields.forEach(fieldName => {
            // Find field (try static first, then dynamic)
            let field = this.form.querySelector(`#id_${fieldName}`) ||
                       this.form.querySelector(`#id_dyn_${fieldName}`) ||
                       this.form.querySelector(`[name="${fieldName}"]`) ||
                       this.form.querySelector(`[name="dyn_${fieldName}"]`);
            
            const feedbackEl = document.getElementById(`${fieldName}_duplicate_feedback`);
            
            if (field) {
                // Apply strong yellow/orange styling
                field.classList.add('border-warning');
                field.style.borderColor = '#ffc107';
                field.style.borderWidth = '3px';
                field.style.borderStyle = 'solid';
                field.style.boxShadow = '0 0 0 0.25rem rgba(255, 193, 7, 0.25)';
                
                console.log(`⚠️ YELLOW border applied to field: ${field.id || field.name}`);
            }
            
            if (feedbackEl) {
                const similarityLevel = firstDuplicate.similarity_level;
                const iconClass = similarityLevel === 'high' ? 'bi-exclamation-triangle' : 'bi-info-circle';
                const alertClass = similarityLevel === 'high' ? 'alert-warning' : 'alert-info';
                
                feedbackEl.innerHTML = `
                    <div class="${alertClass} p-2 mb-0 mt-1" role="alert" style="font-size: 0.9rem;">
                        <i class="bi ${iconClass}-fill me-2"></i>
                        <strong>Similar asset found:</strong> 
                        ${firstDuplicate.similarity_score}% match with existing asset
                        <button type="button" class="btn btn-link btn-sm p-0 ms-2" 
                                onclick="duplicateDetector.showDuplicateDetails('${firstDuplicate.uuid}')">
                            View Details
                        </button>
                    </div>
                `;
                feedbackEl.style.display = 'block';
                
                console.log(`⚠️ Warning message displayed in element: ${feedbackEl.id}`);
            } else {
                console.warn(`⚠️ Feedback element not found: ${fieldName}_duplicate_feedback`);
            }
        });
        
        // Store warnings for form submission
        this.duplicateWarnings = duplicates;
    }
    
    showSuccessState() {
        this.options.watchFields.forEach(fieldName => {
            // Find field (try static first, then dynamic)
            let field = this.form.querySelector(`#id_${fieldName}`) ||
                       this.form.querySelector(`#id_dyn_${fieldName}`) ||
                       this.form.querySelector(`[name="${fieldName}"]`) ||
                       this.form.querySelector(`[name="dyn_${fieldName}"]`);
            
            if (field && field.value && field.value.trim()) {
                // Apply strong green styling
                field.classList.add('border-success');
                field.style.borderColor = '#28a745';
                field.style.borderWidth = '3px';
                field.style.borderStyle = 'solid';
                field.style.boxShadow = '0 0 0 0.25rem rgba(40, 167, 69, 0.25)';
                
                console.log(`✅ GREEN border applied to field: ${field.id || field.name}`);
                
                const feedbackEl = document.getElementById(`${fieldName}_duplicate_feedback`);
                if (feedbackEl) {
                    feedbackEl.innerHTML = `
                        <div class="alert alert-success p-2 mb-0 mt-1" role="alert" style="font-size: 0.9rem;">
                            <i class="bi bi-check-circle-fill me-2"></i>
                            <strong>No duplicates found</strong> - Safe to proceed
                        </div>
                    `;
                    feedbackEl.style.display = 'block';
                    
                    console.log(`✅ Success message displayed in element: ${feedbackEl.id}`);
                } else {
                    console.warn(`⚠️ Feedback element not found: ${fieldName}_duplicate_feedback`);
                }
            }
        });
    }
    
    showCheckingState() {
        this.options.watchFields.forEach(fieldName => {
            // Find field (try static first, then dynamic)
            let field = this.form.querySelector(`#id_${fieldName}`) ||
                       this.form.querySelector(`#id_dyn_${fieldName}`) ||
                       this.form.querySelector(`[name="${fieldName}"]`) ||
                       this.form.querySelector(`[name="dyn_${fieldName}"]`);
            
            if (field && field.value && field.value.trim()) {
                // Add subtle blue border while checking
                field.classList.add('duplicate-checking');
                field.style.borderColor = '#0d6efd';
                field.style.borderWidth = '2px';
                field.style.borderStyle = 'solid';
                
                const feedbackEl = document.getElementById(`${fieldName}_duplicate_feedback`);
                if (feedbackEl) {
                    feedbackEl.innerHTML = `
                        <div class="alert alert-info p-2 mb-0 mt-1" role="alert" style="font-size: 0.9rem;">
                            <div class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></div>
                            <strong>Checking for duplicates...</strong>
                        </div>
                    `;
                    feedbackEl.style.display = 'block';
                    
                    console.log(`⏳ Checking state displayed for field: ${field.id || field.name}`);
                }
            }
        });
    }
    
    hideCheckingState() {
        this.options.watchFields.forEach(fieldName => {
            // Find field (try static first, then dynamic)
            let field = this.form.querySelector(`#id_${fieldName}`) ||
                       this.form.querySelector(`#id_dyn_${fieldName}`) ||
                       this.form.querySelector(`[name="${fieldName}"]`) ||
                       this.form.querySelector(`[name="dyn_${fieldName}"]`);
            
            if (field) {
                field.classList.remove('duplicate-checking');
            }
        });
    }
    
    clearAllFeedback() {
        this.options.watchFields.forEach(fieldName => {
            // Find field (try static first, then dynamic)
            let field = this.form.querySelector(`#id_${fieldName}`) ||
                       this.form.querySelector(`#id_dyn_${fieldName}`) ||
                       this.form.querySelector(`[name="${fieldName}"]`) ||
                       this.form.querySelector(`[name="dyn_${fieldName}"]`);
            
            const feedbackEl = document.getElementById(`${fieldName}_duplicate_feedback`);
            
            if (field) {
                // Remove all styling classes
                field.classList.remove(
                    'is-invalid', 'border-danger', 'border-warning', 
                    'border-success', 'duplicate-checking'
                );
                // Reset all inline styles
                field.style.borderColor = '';
                field.style.borderWidth = '';
                field.style.borderStyle = '';
                field.style.boxShadow = '';
            }
            
            if (feedbackEl) {
                feedbackEl.innerHTML = '';
                feedbackEl.style.display = 'none';
            }
        });
    }
    
    showError(message) {
        // Show general error message
        const errorContainer = this.form.querySelector('.duplicate-general-error') || 
                             this.createGeneralErrorContainer();
        
        errorContainer.innerHTML = `
            <div class="alert alert-danger alert-sm" role="alert">
                <i class="bi bi-exclamation-triangle-fill me-2"></i>
                ${message}
            </div>
        `;
    }
    
    createGeneralErrorContainer() {
        const container = document.createElement('div');
        container.className = 'duplicate-general-error mb-3';
        
        // Insert at the top of the form
        const firstField = this.form.querySelector('.form-group, .mb-3, .field');
        if (firstField) {
            this.form.insertBefore(container, firstField);
        } else {
            this.form.appendChild(container);
        }
        
        return container;
    }
    
    setupFormSubmission() {
        this.form.addEventListener('submit', (e) => {
            // Check if there are blocking errors
            const hasBlockingErrors = this.form.querySelector('.is-invalid.duplicate-check-field');
            
            if (hasBlockingErrors) {
                e.preventDefault();
                this.showError('Please resolve duplicate conflicts before submitting.');
                return false;
            }
            
            // Show confirmation for warnings
            if (this.duplicateWarnings.length > 0) {
                const proceed = confirm(
                    `Warning: ${this.duplicateWarnings.length} similar asset(s) found. ` +
                    'Are you sure you want to proceed?'
                );
                
                if (!proceed) {
                    e.preventDefault();
                    return false;
                }
            }
        });
    }
    
    showDuplicateDetails(assetUuid) {
        // Open asset details in new tab/window
        const detailUrl = `/assets/${assetUuid}/`;
        window.open(detailUrl, '_blank');
    }
    
    // Public API for manual triggering
    triggerCheck() {
        this.checkDuplicates();
    }
    
    clearCache() {
        this.lastCheckData = {};
        this.duplicateWarnings = [];
    }
}

// Auto-initialize on DOM ready
document.addEventListener('DOMContentLoaded', function() {
    // Only initialize on asset forms
    if (document.querySelector('#asset-form, .asset-form')) {
        window.duplicateDetector = new DuplicateDetector({
            formSelector: '#asset-form, .asset-form'
        });
    }
});

// CSS for visual feedback (inject into page)
const duplicateDetectionStyles = `
<style>
.duplicate-check-field.border-success {
    border-color: #28a745 !important;
}

.duplicate-check-field.border-warning {
    border-color: #ffc107 !important;
}

.duplicate-check-field.border-danger {
    border-color: #dc3545 !important;
}

.duplicate-check-field.duplicate-checking {
    border-color: #007bff !important;
    box-shadow: 0 0 0 0.2rem rgba(0, 123, 255, 0.25);
}

.duplicate-feedback .alert-sm {
    font-size: 0.875rem;
    border-radius: 0.25rem;
}

.duplicate-feedback .btn-link {
    text-decoration: none;
    font-size: inherit;
}

.duplicate-feedback .btn-link:hover {
    text-decoration: underline;
}

@media (max-width: 576px) {
    .duplicate-feedback .alert-sm {
        font-size: 0.8rem;
        padding: 0.375rem 0.5rem;
    }
}
</style>
`;

// Inject styles
document.head.insertAdjacentHTML('beforeend', duplicateDetectionStyles);
