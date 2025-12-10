/**
 * User Self-Service Branch Transfer Request
 * 
 * WORLD-CLASS: Modern, accessible, performant transfer request modal.
 * 
 * Features:
 * - Bootstrap 5 modal with smooth animations
 * - Real-time form validation
 * - Character counter for reason field
 * - Date picker for effective date
 * - Loading states and error handling
 * - Toast notifications
 * - WCAG 2.1 AA compliant
 * - Mobile responsive
 * 
 * Inspired by:
 * - ServiceNow ITAM: Clean forms, real-time validation
 * - IBM Maximo: Professional UI, clear feedback
 * - SAP Fiori: Modern design, accessibility
 * - Snipe-IT: Simple, intuitive UX
 * 
 * @author Asset Management System
 * @version 1.0
 */

class UserTransferRequestModal {
    constructor() {
        this.modal = null;
        this.form = null;
        this.submitButton = null;
        this.branchSelect = null;
        this.reasonTextarea = null;
        this.effectiveDateInput = null;
        this.characterCounter = null;
        
        this.minReasonLength = 10;
        this.maxReasonLength = 500;
        
        this.init();
    }
    
    /**
     * Initialize modal and event listeners
     */
    init() {
        // Wait for DOM to be ready
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => this.setup());
        } else {
            this.setup();
        }
    }
    
    /**
     * Setup modal elements and event listeners
     */
    setup() {
        // Get modal element
        const modalElement = document.getElementById('userTransferRequestModal');
        if (!modalElement) {
            console.warn('User transfer request modal not found');
            return;
        }
        
        // Initialize Bootstrap modal
        this.modal = new bootstrap.Modal(modalElement);
        
        // Get form elements
        this.form = modalElement.querySelector('#userTransferRequestForm');
        this.submitButton = modalElement.querySelector('#submitTransferRequest');
        this.branchSelect = modalElement.querySelector('#transferToBranch');
        this.reasonTextarea = modalElement.querySelector('#transferReason');
        this.effectiveDateInput = modalElement.querySelector('#transferEffectiveDate');
        this.characterCounter = modalElement.querySelector('#reasonCharCount');
        
        if (!this.form) {
            console.error('Transfer request form not found');
            return;
        }
        
        // Setup event listeners
        this.setupEventListeners();
        
        // Setup date picker constraints
        this.setupDatePicker();
    }
    
    /**
     * Setup all event listeners
     */
    setupEventListeners() {
        // Form submission
        this.form.addEventListener('submit', (e) => this.handleSubmit(e));
        
        // Real-time validation for reason field
        if (this.reasonTextarea) {
            this.reasonTextarea.addEventListener('input', () => this.validateReason());
            this.reasonTextarea.addEventListener('blur', () => this.validateReason());
        }
        
        // Branch selection validation
        if (this.branchSelect) {
            this.branchSelect.addEventListener('change', () => this.validateBranch());
        }
        
        // Reset form when modal is hidden
        const modalElement = document.getElementById('userTransferRequestModal');
        if (modalElement) {
            modalElement.addEventListener('hidden.bs.modal', () => this.resetForm());
        }
    }
    
    /**
     * Setup date picker with constraints
     */
    setupDatePicker() {
        if (!this.effectiveDateInput) return;
        
        // Set minimum date to today
        const today = new Date().toISOString().split('T')[0];
        this.effectiveDateInput.setAttribute('min', today);
        
        // Set maximum date to 1 year from now
        const maxDate = new Date();
        maxDate.setFullYear(maxDate.getFullYear() + 1);
        this.effectiveDateInput.setAttribute('max', maxDate.toISOString().split('T')[0]);
    }
    
    /**
     * Validate reason field
     * @returns {boolean} True if valid
     */
    validateReason() {
        if (!this.reasonTextarea) return false;
        
        const reason = this.reasonTextarea.value.trim();
        const length = reason.length;
        
        // Update character counter
        if (this.characterCounter) {
            this.characterCounter.textContent = `${length}/${this.maxReasonLength}`;
            
            // Color coding
            if (length < this.minReasonLength) {
                this.characterCounter.className = 'form-text text-danger';
            } else if (length > this.maxReasonLength * 0.9) {
                this.characterCounter.className = 'form-text text-warning';
            } else {
                this.characterCounter.className = 'form-text text-success';
            }
        }
        
        // Validation
        let isValid = true;
        let message = '';
        
        if (length === 0) {
            isValid = false;
            message = 'Reason is required';
        } else if (length < this.minReasonLength) {
            isValid = false;
            message = `Reason must be at least ${this.minReasonLength} characters`;
        } else if (length > this.maxReasonLength) {
            isValid = false;
            message = `Reason cannot exceed ${this.maxReasonLength} characters`;
        }
        
        // Update UI
        if (isValid) {
            this.reasonTextarea.classList.remove('is-invalid');
            this.reasonTextarea.classList.add('is-valid');
        } else {
            this.reasonTextarea.classList.remove('is-valid');
            this.reasonTextarea.classList.add('is-invalid');
            
            const feedback = this.reasonTextarea.nextElementSibling;
            if (feedback && feedback.classList.contains('invalid-feedback')) {
                feedback.textContent = message;
            }
        }
        
        return isValid;
    }
    
    /**
     * Validate branch selection
     * @returns {boolean} True if valid
     */
    validateBranch() {
        if (!this.branchSelect) return false;
        
        const isValid = this.branchSelect.value !== '';
        
        if (isValid) {
            this.branchSelect.classList.remove('is-invalid');
            this.branchSelect.classList.add('is-valid');
        } else {
            this.branchSelect.classList.remove('is-valid');
            this.branchSelect.classList.add('is-invalid');
        }
        
        return isValid;
    }
    
    /**
     * Validate entire form
     * @returns {boolean} True if valid
     */
    validateForm() {
        const isBranchValid = this.validateBranch();
        const isReasonValid = this.validateReason();
        
        return isBranchValid && isReasonValid;
    }
    
    /**
     * Handle form submission
     * @param {Event} e - Submit event
     */
    async handleSubmit(e) {
        e.preventDefault();
        
        // Validate form
        if (!this.validateForm()) {
            this.showToast('Please fix the errors before submitting', 'danger');
            return;
        }
        
        // Get form data
        const formData = {
            to_branch_id: parseInt(this.branchSelect.value),
            reason: this.reasonTextarea.value.trim(),
            effective_date: this.effectiveDateInput.value || null,
            metadata: {}
        };
        
        // Disable submit button and show loading state
        this.setLoading(true);
        
        try {
            // Submit request
            const response = await fetch('/users/api/transfer/user-initiate/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCsrfToken()
                },
                body: JSON.stringify(formData)
            });
            
            const data = await response.json();
            
            if (data.success) {
                // Success
                this.showToast(data.message, 'success');
                this.modal.hide();
                
                // Reload page after short delay to show updated requests
                setTimeout(() => {
                    window.location.reload();
                }, 1500);
            } else {
                // Error from server
                this.showToast(data.error || 'Failed to submit transfer request', 'danger');
                this.setLoading(false);
            }
        } catch (error) {
            console.error('Transfer request error:', error);
            this.showToast('An error occurred. Please try again.', 'danger');
            this.setLoading(false);
        }
    }
    
    /**
     * Set loading state
     * @param {boolean} loading - True to show loading state
     */
    setLoading(loading) {
        if (!this.submitButton) return;
        
        if (loading) {
            this.submitButton.disabled = true;
            this.submitButton.innerHTML = `
                <span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>
                Submitting...
            `;
        } else {
            this.submitButton.disabled = false;
            this.submitButton.innerHTML = `
                <i class="bi bi-send me-2"></i>Submit Request
            `;
        }
    }
    
    /**
     * Reset form to initial state
     */
    resetForm() {
        if (!this.form) return;
        
        // Reset form
        this.form.reset();
        
        // Remove validation classes
        this.form.querySelectorAll('.is-valid, .is-invalid').forEach(el => {
            el.classList.remove('is-valid', 'is-invalid');
        });
        
        // Reset character counter
        if (this.characterCounter) {
            this.characterCounter.textContent = `0/${this.maxReasonLength}`;
            this.characterCounter.className = 'form-text text-muted';
        }
        
        // Reset submit button
        this.setLoading(false);
    }
    
    /**
     * Show toast notification
     * @param {string} message - Message to display
     * @param {string} type - Toast type (success, danger, warning, info)
     */
    showToast(message, type = 'info') {
        // Use global toast function if available
        if (typeof window.showToast === 'function') {
            window.showToast(message, type);
            return;
        }
        
        // Fallback: Create simple toast
        const toast = document.createElement('div');
        toast.className = `alert alert-${type} position-fixed top-0 end-0 m-3`;
        toast.style.zIndex = '9999';
        toast.textContent = message;
        
        document.body.appendChild(toast);
        
        setTimeout(() => {
            toast.remove();
        }, 5000);
    }
    
    /**
     * Get CSRF token from cookie
     * @returns {string} CSRF token
     */
    getCsrfToken() {
        const name = 'csrftoken';
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
     * Show modal
     */
    show() {
        if (this.modal) {
            this.modal.show();
        }
    }
    
    /**
     * Hide modal
     */
    hide() {
        if (this.modal) {
            this.modal.hide();
        }
    }
}

// Initialize when DOM is ready
let userTransferRequestModal;

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        userTransferRequestModal = new UserTransferRequestModal();
    });
} else {
    userTransferRequestModal = new UserTransferRequestModal();
}

// Export for use in other scripts
if (typeof module !== 'undefined' && module.exports) {
    module.exports = UserTransferRequestModal;
}
