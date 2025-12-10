/**
 * Real-Time Form Validation Engine - World-Class Implementation
 * 
 * Provides instant validation feedback as users interact with forms.
 * Inspired by: ServiceNow ITAM, Salesforce, Stripe, Google Forms
 * 
 * Features:
 * - Real-time validation (debounced)
 * - Multiple validation rules per field
 * - Custom validators
 * - Visual feedback (success/error states)
 * - Accessible error messages (ARIA)
 * - Async validation support (API calls)
 * - Form-level validation
 * - Dependency validation (field depends on another)
 * 
 * Usage:
 *   const validator = new FormValidator('myForm', {
 *     fields: {
 *       email: {
 *         rules: ['required', 'email'],
 *         messages: { required: 'Email is required', email: 'Invalid email format' }
 *       }
 *     }
 *   });
 */

class FormValidator {
  /**
   * Initialize form validator
   * @param {string} formId - Form element ID
   * @param {Object} config - Validation configuration
   */
  constructor(formId, config = {}) {
    this.formId = formId;
    this.form = document.getElementById(formId);
    
    if (!this.form) {
      console.warn(`FormValidator: Form with ID "${formId}" not found`);
      return;
    }

    // Configuration
    this.config = {
      fields: config.fields || {},
      debounceDelay: config.debounceDelay || 500, // 500ms debounce
      validateOnBlur: config.validateOnBlur !== false,
      validateOnInput: config.validateOnInput !== false,
      showSuccessState: config.showSuccessState !== false,
      scrollToError: config.scrollToError !== false,
      onValidate: config.onValidate || null,
      onError: config.onError || null,
    };

    // State
    this.errors = {};
    this.debounceTimers = {};
    this.asyncValidators = new Map();

    // Built-in validators
    this.validators = this.getBuiltInValidators();

    // Initialize
    this.init();
  }

  /**
   * Initialize validator
   */
  init() {
    // Attach event listeners
    this.attachListeners();

    // Prevent default HTML5 validation
    this.form.setAttribute('novalidate', 'true');

    // Handle form submission
    this.form.addEventListener('submit', (e) => {
      if (!this.validateAll()) {
        e.preventDefault();
        e.stopPropagation();
        
        // Scroll to first error
        if (this.config.scrollToError) {
          this.scrollToFirstError();
        }
      }
    });

    console.log(`✅ FormValidator initialized for "${this.formId}"`);
  }

  /**
   * Get built-in validators
   * @returns {Object} Validator functions
   */
  getBuiltInValidators() {
    return {
      required: (value) => {
        if (typeof value === 'string') {
          return value.trim().length > 0;
        }
        return value !== null && value !== undefined && value !== '';
      },

      email: (value) => {
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return !value || emailRegex.test(value);
      },

      url: (value) => {
        try {
          new URL(value);
          return true;
        } catch {
          return !value || false;
        }
      },

      minLength: (value, min) => {
        return !value || value.length >= parseInt(min);
      },

      maxLength: (value, max) => {
        return !value || value.length <= parseInt(max);
      },

      min: (value, min) => {
        return !value || parseFloat(value) >= parseFloat(min);
      },

      max: (value, max) => {
        return !value || parseFloat(value) <= parseFloat(max);
      },

      pattern: (value, pattern) => {
        const regex = new RegExp(pattern);
        return !value || regex.test(value);
      },

      number: (value) => {
        return !value || !isNaN(value);
      },

      integer: (value) => {
        return !value || (Number.isInteger(parseFloat(value)) && !value.includes('.'));
      },

      alpha: (value) => {
        return !value || /^[a-zA-Z]+$/.test(value);
      },

      alphanumeric: (value) => {
        return !value || /^[a-zA-Z0-9]+$/.test(value);
      },

      phone: (value) => {
        const phoneRegex = /^[\d\s\-\+\(\)]+$/;
        return !value || phoneRegex.test(value);
      },

      date: (value) => {
        return !value || !isNaN(Date.parse(value));
      },

      match: (value, fieldName) => {
        const matchField = this.form.elements[fieldName];
        return !value || !matchField || value === matchField.value;
      },
    };
  }

  /**
   * Attach event listeners to form fields
   */
  attachListeners() {
    for (const [fieldName, fieldConfig] of Object.entries(this.config.fields)) {
      const field = this.form.elements[fieldName];
      if (!field) {
        console.warn(`Field "${fieldName}" not found in form`);
        continue;
      }

      // Validate on input (debounced)
      if (this.config.validateOnInput) {
        field.addEventListener('input', () => {
          this.validateFieldDebounced(fieldName);
        });
      }

      // Validate on blur (immediate)
      if (this.config.validateOnBlur) {
        field.addEventListener('blur', () => {
          this.validateField(fieldName);
        });
      }

      // Clear error on focus
      field.addEventListener('focus', () => {
        this.clearFieldError(fieldName);
      });
    }
  }

  /**
   * Validate field with debounce
   * @param {string} fieldName - Field name
   */
  validateFieldDebounced(fieldName) {
    // Clear existing timer
    if (this.debounceTimers[fieldName]) {
      clearTimeout(this.debounceTimers[fieldName]);
    }

    // Set new timer
    this.debounceTimers[fieldName] = setTimeout(() => {
      this.validateField(fieldName);
    }, this.config.debounceDelay);
  }

  /**
   * Validate single field
   * @param {string} fieldName - Field name
   * @returns {boolean} True if valid
   */
  async validateField(fieldName) {
    const fieldConfig = this.config.fields[fieldName];
    if (!fieldConfig) return true;

    const field = this.form.elements[fieldName];
    if (!field) return true;

    const value = field.value;
    const rules = fieldConfig.rules || [];
    const messages = fieldConfig.messages || {};

    // Clear previous error
    delete this.errors[fieldName];

    // Validate each rule
    for (const rule of rules) {
      let isValid = true;
      let ruleName = rule;
      let ruleParam = null;

      // Parse rule with parameter (e.g., "minLength:5")
      if (typeof rule === 'string' && rule.includes(':')) {
        [ruleName, ruleParam] = rule.split(':');
      } else if (typeof rule === 'object') {
        ruleName = rule.name;
        ruleParam = rule.param;
      }

      // Get validator function
      const validator = this.validators[ruleName] || fieldConfig.customValidators?.[ruleName];

      if (!validator) {
        console.warn(`Validator "${ruleName}" not found`);
        continue;
      }

      // Run validation
      try {
        if (validator.constructor.name === 'AsyncFunction') {
          // Async validator
          isValid = await validator(value, ruleParam, field);
        } else {
          // Sync validator
          isValid = validator(value, ruleParam, field);
        }
      } catch (error) {
        console.error(`Validation error for "${fieldName}":`, error);
        isValid = false;
      }

      // Handle validation result
      if (!isValid) {
        const message = messages[ruleName] || `Invalid ${fieldName}`;
        this.errors[fieldName] = message;
        this.showFieldError(fieldName, message);
        
        // Call error callback
        if (this.config.onError) {
          this.config.onError(fieldName, message);
        }
        
        return false;
      }
    }

    // Field is valid
    this.showFieldSuccess(fieldName);
    
    // Call validate callback
    if (this.config.onValidate) {
      this.config.onValidate(fieldName, value);
    }
    
    return true;
  }

  /**
   * Validate all fields
   * @returns {boolean} True if all valid
   */
  async validateAll() {
    const fieldNames = Object.keys(this.config.fields);
    const validations = fieldNames.map(name => this.validateField(name));
    const results = await Promise.all(validations);
    return results.every(result => result === true);
  }

  /**
   * Show field error
   * @param {string} fieldName - Field name
   * @param {string} message - Error message
   */
  showFieldError(fieldName, message) {
    const field = this.form.elements[fieldName];
    if (!field) return;

    // Add error class
    field.classList.add('is-invalid');
    field.classList.remove('is-valid');

    // Set ARIA attributes
    field.setAttribute('aria-invalid', 'true');
    field.setAttribute('aria-describedby', `${fieldName}-error`);

    // Create or update error message
    let errorDiv = document.getElementById(`${fieldName}-error`);
    
    if (!errorDiv) {
      errorDiv = document.createElement('div');
      errorDiv.id = `${fieldName}-error`;
      errorDiv.className = 'invalid-feedback';
      errorDiv.setAttribute('role', 'alert');
      
      // Insert after field or after parent group
      const parent = field.closest('.mb-3, .form-group') || field.parentElement;
      parent.appendChild(errorDiv);
    }

    errorDiv.textContent = message;
    errorDiv.style.display = 'block';
  }

  /**
   * Show field success
   * @param {string} fieldName - Field name
   */
  showFieldSuccess(fieldName) {
    const field = this.form.elements[fieldName];
    if (!field) return;

    // Only show success state if configured
    if (this.config.showSuccessState) {
      field.classList.add('is-valid');
      field.classList.remove('is-invalid');
    } else {
      field.classList.remove('is-invalid', 'is-valid');
    }

    // Clear ARIA attributes
    field.removeAttribute('aria-invalid');
    field.removeAttribute('aria-describedby');

    // Hide error message
    const errorDiv = document.getElementById(`${fieldName}-error`);
    if (errorDiv) {
      errorDiv.style.display = 'none';
    }
  }

  /**
   * Clear field error
   * @param {string} fieldName - Field name
   */
  clearFieldError(fieldName) {
    const field = this.form.elements[fieldName];
    if (!field) return;

    field.classList.remove('is-invalid', 'is-valid');
    field.removeAttribute('aria-invalid');
    field.removeAttribute('aria-describedby');

    const errorDiv = document.getElementById(`${fieldName}-error`);
    if (errorDiv) {
      errorDiv.style.display = 'none';
    }

    delete this.errors[fieldName];
  }

  /**
   * Scroll to first error field
   */
  scrollToFirstError() {
    const firstErrorField = Object.keys(this.errors)[0];
    if (!firstErrorField) return;

    const field = this.form.elements[firstErrorField];
    if (!field) return;

    // Scroll with offset for fixed headers
    const offset = 100;
    const elementPosition = field.getBoundingClientRect().top;
    const offsetPosition = elementPosition + window.pageYOffset - offset;

    window.scrollTo({
      top: offsetPosition,
      behavior: 'smooth'
    });

    // Focus field
    field.focus();
  }

  /**
   * Add custom validator
   * @param {string} name - Validator name
   * @param {Function} validator - Validator function
   */
  addValidator(name, validator) {
    this.validators[name] = validator;
  }

  /**
   * Get validation errors
   * @returns {Object} Errors object
   */
  getErrors() {
    return { ...this.errors };
  }

  /**
   * Check if form is valid
   * @returns {boolean} True if valid
   */
  isValid() {
    return Object.keys(this.errors).length === 0;
  }

  /**
   * Reset validation
   */
  reset() {
    this.errors = {};
    
    // Clear all field states
    for (const fieldName of Object.keys(this.config.fields)) {
      this.clearFieldError(fieldName);
    }
  }

  /**
   * Destroy validator
   */
  destroy() {
    // Clear all timers
    for (const timer of Object.values(this.debounceTimers)) {
      clearTimeout(timer);
    }
    
    this.debounceTimers = {};
    this.errors = {};
    
    console.log('🛑 FormValidator destroyed');
  }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
  module.exports = FormValidator;
}
