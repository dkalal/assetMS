/**
 * Branch Selector Enhancement
 * 
 * Provides enhanced UX for branch switching with:
 * - Loading states
 * - Error handling
 * - Visual feedback
 * - Accessibility
 * - Debug logging
 * 
 * @version 1.0.0
 * @author Asset Management System
 */

(function() {
  'use strict';

  // Configuration
  const CONFIG = {
    selectorId: 'branch-select-topbar',
    formId: 'branch-switch-form',
    loadingClass: 'branch-switching',
    debugMode: false // Set to true for console logging
  };

  // Utility: Debug logger
  function debug(...args) {
    if (CONFIG.debugMode) {
      void args;
    }
  }

  // Initialize on DOM ready
  document.addEventListener('DOMContentLoaded', function() {
    const selector = document.getElementById(CONFIG.selectorId);
    const form = document.getElementById(CONFIG.formId);

    if (!selector || !form) {
      debug('Branch selector or form not found - user may not have branches');
      return;
    }

    debug('Initializing branch selector', {
      currentValue: selector.value,
      optionCount: selector.options.length
    });

    // Validate options on load
    validateOptions(selector);

    // Add change event listener with enhanced UX
    selector.addEventListener('change', function(e) {
      const selectedValue = e.target.value;
      const selectedOption = e.target.options[e.target.selectedIndex];
      
      debug('Branch changed', {
        value: selectedValue,
        text: selectedOption?.text,
        isHQ: selectedOption?.dataset?.isHq
      });

      // Validate selection
      if (!selectedValue || selectedValue === '') {
        showError('Please select a valid branch');
        e.preventDefault();
        return false;
      }

      // Add loading state
      addLoadingState(selector, form);

      // Submit form (already has onchange="this.form.submit()")
      // The form will submit automatically, but we add visual feedback
    });

    // Handle form submission
    form.addEventListener('submit', function(e) {
      const selectedValue = selector.value;
      
      if (!selectedValue || selectedValue === '') {
        e.preventDefault();
        showError('Please select a branch before switching');
        removeLoadingState(selector, form);
        return false;
      }

      debug('Form submitting', { branchId: selectedValue });
    });

    // Keyboard accessibility enhancement
    selector.addEventListener('keydown', function(e) {
      // Enter key should submit
      if (e.key === 'Enter') {
        e.preventDefault();
        form.submit();
      }
      
      // Escape key should blur
      if (e.key === 'Escape') {
        e.target.blur();
      }
    });
  });

  /**
   * Validate dropdown options
   * Logs warnings if empty or invalid options are found
   */
  function validateOptions(selector) {
    const options = Array.from(selector.options);
    const emptyOptions = options.filter(opt => !opt.value || opt.value === '');
    const invalidOptions = options.filter(opt => !opt.text || opt.text.trim() === '');

    if (emptyOptions.length > 0) {
      console.warn('[BranchSelector] Found empty option values:', emptyOptions.length);
      debug('Empty options:', emptyOptions);
    }

    if (invalidOptions.length > 0) {
      console.warn('[BranchSelector] Found invalid option text:', invalidOptions.length);
      debug('Invalid options:', invalidOptions);
    }

    if (options.length === 0) {
      console.warn('[BranchSelector] No options available in dropdown');
    }

    debug('Validation complete', {
      total: options.length,
      empty: emptyOptions.length,
      invalid: invalidOptions.length
    });
  }

  /**
   * Add loading state to selector and form
   */
  function addLoadingState(selector, form) {
    // Disable selector
    selector.disabled = true;
    selector.classList.add(CONFIG.loadingClass);

    // Add loading indicator
    const label = form.querySelector('label[for="' + CONFIG.selectorId + '"]');
    if (label) {
      const spinner = document.createElement('span');
      spinner.className = 'spinner-border spinner-border-sm ms-1';
      spinner.setAttribute('role', 'status');
      spinner.setAttribute('aria-hidden', 'true');
      spinner.id = 'branch-loading-spinner';
      label.appendChild(spinner);
    }

    // Update ARIA
    selector.setAttribute('aria-busy', 'true');
    selector.setAttribute('aria-label', 'Switching branch, please wait...');

    debug('Loading state added');
  }

  /**
   * Remove loading state
   */
  function removeLoadingState(selector, form) {
    // Re-enable selector
    selector.disabled = false;
    selector.classList.remove(CONFIG.loadingClass);

    // Remove spinner
    const spinner = document.getElementById('branch-loading-spinner');
    if (spinner) {
      spinner.remove();
    }

    // Restore ARIA
    selector.setAttribute('aria-busy', 'false');
    selector.setAttribute('aria-label', 'Select branch');

    debug('Loading state removed');
  }

  /**
   * Show error message
   */
  function showError(message) {
    // Use toast if available
    if (typeof window.showToast === 'function') {
      window.showToast(message, 'warning');
    } else {
      // Fallback to alert
      alert(message);
    }

    console.error('[BranchSelector]', message);
  }

  // Expose debug toggle for development
  window.BranchSelector = {
    enableDebug: function() {
      CONFIG.debugMode = true;
    },
    disableDebug: function() {
      CONFIG.debugMode = false;
    },
    getConfig: function() {
      return { ...CONFIG };
    }
  };

})();
