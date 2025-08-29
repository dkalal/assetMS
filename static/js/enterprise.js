/**
 * Enterprise Asset Management JavaScript Framework
 * Provides modern, accessible, and performant UI components
 */

class EnterpriseFramework {
  constructor() {
    this.init();
  }

  init() {
    this.initAccessibility();
    this.initResponsive();
    this.initModals();
    this.initForms();
    this.initTables();
    this.initTooltips();
    this.initKeyboardNavigation();
  }

  // Accessibility Enhancements
  initAccessibility() {
    // Add skip link
    if (!document.querySelector('.skip-link')) {
      const skipLink = document.createElement('a');
      skipLink.href = '#main-content';
      skipLink.className = 'skip-link sr-only';
      skipLink.textContent = 'Skip to main content';
      skipLink.addEventListener('focus', () => skipLink.classList.remove('sr-only'));
      skipLink.addEventListener('blur', () => skipLink.classList.add('sr-only'));
      document.body.insertBefore(skipLink, document.body.firstChild);
    }

    // Add main content landmark
    const mainContent = document.querySelector('.main-content');
    if (mainContent && !mainContent.id) {
      mainContent.id = 'main-content';
    }

    // Enhance form accessibility
    document.querySelectorAll('.form-control').forEach(input => {
      const label = document.querySelector(`label[for="${input.id}"]`);
      if (!label && input.previousElementSibling?.classList.contains('form-label')) {
        const labelId = `label-${input.id || Math.random().toString(36).substr(2, 9)}`;
        input.previousElementSibling.id = labelId;
        input.setAttribute('aria-labelledby', labelId);
      }
    });

    // Add ARIA labels to buttons without text
    document.querySelectorAll('button:not([aria-label])').forEach(btn => {
      const icon = btn.querySelector('i[class*="bi-"]');
      if (icon && !btn.textContent.trim()) {
        const iconClass = Array.from(icon.classList).find(cls => cls.startsWith('bi-'));
        if (iconClass) {
          const label = iconClass.replace('bi-', '').replace('-', ' ');
          btn.setAttribute('aria-label', label);
        }
      }
    });
  }

  // Responsive Enhancements
  initResponsive() {
    // Mobile navigation toggle
    const createMobileToggle = () => {
      const navbar = document.querySelector('.navbar');
      if (!navbar || navbar.querySelector('.mobile-toggle')) return;

      const toggle = document.createElement('button');
      toggle.className = 'btn btn-outline mobile-toggle lg:hidden';
      toggle.innerHTML = '<i class="bi bi-list"></i>';
      toggle.setAttribute('aria-label', 'Toggle navigation');
      
      const navItems = navbar.querySelector('.navbar-nav, .d-flex');
      if (navItems) {
        toggle.addEventListener('click', () => {
          navItems.classList.toggle('show');
          toggle.setAttribute('aria-expanded', navItems.classList.contains('show'));
        });
        navbar.appendChild(toggle);
      }
    };

    createMobileToggle();

    // Responsive tables
    document.querySelectorAll('.table').forEach(table => {
      if (!table.closest('.table-container')) {
        const container = document.createElement('div');
        container.className = 'table-container';
        table.parentNode.insertBefore(container, table);
        container.appendChild(table);
      }
    });

    // Handle window resize
    let resizeTimeout;
    window.addEventListener('resize', () => {
      clearTimeout(resizeTimeout);
      resizeTimeout = setTimeout(() => {
        this.handleResize();
      }, 150);
    });
  }

  handleResize() {
    // Update mobile navigation
    const mobileToggle = document.querySelector('.mobile-toggle');
    const navItems = document.querySelector('.navbar-nav, .navbar .d-flex');
    
    if (window.innerWidth >= 1024) {
      if (navItems) navItems.classList.remove('show');
      if (mobileToggle) mobileToggle.setAttribute('aria-expanded', 'false');
    }
  }

  // Modern Modal System
  initModals() {
    // Create modal backdrop if not exists
    if (!document.querySelector('.modal-backdrop-enterprise')) {
      const backdrop = document.createElement('div');
      backdrop.className = 'modal-backdrop-enterprise';
      backdrop.style.cssText = `
        position: fixed; top: 0; left: 0; width: 100%; height: 100%;
        background: rgba(0, 0, 0, 0.5); z-index: 1050; display: none;
        backdrop-filter: blur(4px);
      `;
      document.body.appendChild(backdrop);
    }

    // Handle modal triggers
    document.addEventListener('click', (e) => {
      const trigger = e.target.closest('[data-modal-target]');
      if (trigger) {
        e.preventDefault();
        const targetId = trigger.getAttribute('data-modal-target');
        this.openModal(targetId);
      }

      const closeBtn = e.target.closest('[data-modal-close]');
      if (closeBtn) {
        e.preventDefault();
        this.closeModal();
      }
    });

    // Close modal on backdrop click
    document.querySelector('.modal-backdrop-enterprise')?.addEventListener('click', () => {
      this.closeModal();
    });

    // Close modal on Escape key
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && document.querySelector('.modal-backdrop-enterprise').style.display === 'flex') {
        this.closeModal();
      }
    });
  }

  openModal(modalId) {
    const modal = document.getElementById(modalId);
    const backdrop = document.querySelector('.modal-backdrop-enterprise');
    
    if (modal && backdrop) {
      backdrop.style.display = 'flex';
      backdrop.style.alignItems = 'center';
      backdrop.style.justifyContent = 'center';
      
      modal.style.display = 'block';
      modal.style.position = 'relative';
      modal.style.zIndex = '1051';
      
      // Focus management
      const focusableElements = modal.querySelectorAll(
        'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
      );
      if (focusableElements.length > 0) {
        focusableElements[0].focus();
      }

      // Trap focus
      this.trapFocus(modal);
      
      document.body.style.overflow = 'hidden';
      modal.setAttribute('aria-hidden', 'false');
    }
  }

  closeModal() {
    const backdrop = document.querySelector('.modal-backdrop-enterprise');
    const openModal = document.querySelector('[style*="z-index: 1051"]');
    
    if (backdrop) {
      backdrop.style.display = 'none';
    }
    
    if (openModal) {
      openModal.style.display = 'none';
      openModal.setAttribute('aria-hidden', 'true');
    }
    
    document.body.style.overflow = '';
    this.removeFocusTrap();
  }

  trapFocus(modal) {
    const focusableElements = modal.querySelectorAll(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
    );
    
    if (focusableElements.length === 0) return;
    
    const firstElement = focusableElements[0];
    const lastElement = focusableElements[focusableElements.length - 1];

    this.focusTrapHandler = (e) => {
      if (e.key === 'Tab') {
        if (e.shiftKey) {
          if (document.activeElement === firstElement) {
            e.preventDefault();
            lastElement.focus();
          }
        } else {
          if (document.activeElement === lastElement) {
            e.preventDefault();
            firstElement.focus();
          }
        }
      }
    };

    document.addEventListener('keydown', this.focusTrapHandler);
  }

  removeFocusTrap() {
    if (this.focusTrapHandler) {
      document.removeEventListener('keydown', this.focusTrapHandler);
      this.focusTrapHandler = null;
    }
  }

  // Enhanced Form Handling
  initForms() {
    // Add loading states
    document.querySelectorAll('form').forEach(form => {
      form.addEventListener('submit', (e) => {
        const submitBtn = form.querySelector('button[type="submit"]');
        if (submitBtn && !submitBtn.disabled) {
          this.setButtonLoading(submitBtn, true);
          
          // Auto-restore after 5 seconds if no response
          setTimeout(() => {
            this.setButtonLoading(submitBtn, false);
          }, 5000);
        }
      });
    });

    // Real-time validation
    document.querySelectorAll('.form-control').forEach(input => {
      input.addEventListener('blur', () => this.validateField(input));
      input.addEventListener('input', () => this.clearFieldError(input));
    });

    // Auto-resize textareas
    document.querySelectorAll('textarea').forEach(textarea => {
      textarea.addEventListener('input', () => {
        textarea.style.height = 'auto';
        textarea.style.height = textarea.scrollHeight + 'px';
      });
    });
  }

  setButtonLoading(button, loading) {
    if (loading) {
      button.dataset.originalText = button.innerHTML;
      button.innerHTML = '<i class="bi bi-hourglass-split"></i> Processing...';
      button.disabled = true;
      button.classList.add('loading');
    } else {
      button.innerHTML = button.dataset.originalText || button.innerHTML;
      button.disabled = false;
      button.classList.remove('loading');
    }
  }

  validateField(field) {
    const isValid = field.checkValidity();
    const errorElement = field.parentNode.querySelector('.field-error');
    
    if (!isValid) {
      field.classList.add('is-invalid');
      if (!errorElement) {
        const error = document.createElement('div');
        error.className = 'field-error text-error text-sm mt-2';
        error.textContent = field.validationMessage;
        field.parentNode.appendChild(error);
      }
    } else {
      field.classList.remove('is-invalid');
      if (errorElement) {
        errorElement.remove();
      }
    }
  }

  clearFieldError(field) {
    field.classList.remove('is-invalid');
    const errorElement = field.parentNode.querySelector('.field-error');
    if (errorElement) {
      errorElement.remove();
    }
  }

  // Enhanced Table Features
  initTables() {
    document.querySelectorAll('.table').forEach(table => {
      // Add sorting
      const headers = table.querySelectorAll('th[data-sort]');
      headers.forEach(header => {
        header.style.cursor = 'pointer';
        header.innerHTML += ' <i class="bi bi-arrow-down-up text-muted"></i>';
        header.addEventListener('click', () => this.sortTable(table, header));
      });

      // Add row selection
      if (table.querySelector('input[type="checkbox"]')) {
        this.initTableSelection(table);
      }
    });
  }

  sortTable(table, header) {
    const column = Array.from(header.parentNode.children).indexOf(header);
    const rows = Array.from(table.querySelectorAll('tbody tr'));
    const isAscending = !header.classList.contains('sort-asc');
    
    // Clear other sort indicators
    table.querySelectorAll('th').forEach(th => {
      th.classList.remove('sort-asc', 'sort-desc');
      const icon = th.querySelector('i');
      if (icon) icon.className = 'bi bi-arrow-down-up text-muted';
    });
    
    // Set current sort indicator
    header.classList.add(isAscending ? 'sort-asc' : 'sort-desc');
    const icon = header.querySelector('i');
    if (icon) {
      icon.className = isAscending ? 'bi bi-arrow-up' : 'bi bi-arrow-down';
    }
    
    rows.sort((a, b) => {
      const aVal = a.children[column].textContent.trim();
      const bVal = b.children[column].textContent.trim();
      
      const aNum = parseFloat(aVal);
      const bNum = parseFloat(bVal);
      
      if (!isNaN(aNum) && !isNaN(bNum)) {
        return isAscending ? aNum - bNum : bNum - aNum;
      }
      
      return isAscending ? aVal.localeCompare(bVal) : bVal.localeCompare(aVal);
    });
    
    const tbody = table.querySelector('tbody');
    rows.forEach(row => tbody.appendChild(row));
  }

  initTableSelection(table) {
    const selectAll = table.querySelector('thead input[type="checkbox"]');
    const rowCheckboxes = table.querySelectorAll('tbody input[type="checkbox"]');
    
    if (selectAll) {
      selectAll.addEventListener('change', () => {
        rowCheckboxes.forEach(checkbox => {
          checkbox.checked = selectAll.checked;
        });
      });
    }
    
    rowCheckboxes.forEach(checkbox => {
      checkbox.addEventListener('change', () => {
        if (selectAll) {
          selectAll.checked = Array.from(rowCheckboxes).every(cb => cb.checked);
        }
      });
    });
  }

  // Tooltip System
  initTooltips() {
    document.querySelectorAll('[title]').forEach(element => {
      const title = element.getAttribute('title');
      element.removeAttribute('title');
      element.setAttribute('data-tooltip', title);
      
      element.addEventListener('mouseenter', (e) => this.showTooltip(e, title));
      element.addEventListener('mouseleave', () => this.hideTooltip());
      element.addEventListener('focus', (e) => this.showTooltip(e, title));
      element.addEventListener('blur', () => this.hideTooltip());
    });
  }

  showTooltip(event, text) {
    const tooltip = document.createElement('div');
    tooltip.className = 'tooltip-enterprise';
    tooltip.textContent = text;
    tooltip.style.cssText = `
      position: absolute; z-index: 1060; padding: 0.5rem 0.75rem;
      background: var(--neutral-900); color: white; font-size: 0.875rem;
      border-radius: 0.375rem; pointer-events: none; white-space: nowrap;
    `;
    
    document.body.appendChild(tooltip);
    
    const rect = event.target.getBoundingClientRect();
    tooltip.style.left = rect.left + (rect.width / 2) - (tooltip.offsetWidth / 2) + 'px';
    tooltip.style.top = rect.top - tooltip.offsetHeight - 8 + 'px';
    
    // Adjust if tooltip goes off screen
    if (tooltip.offsetLeft < 0) {
      tooltip.style.left = '8px';
    }
    if (tooltip.offsetLeft + tooltip.offsetWidth > window.innerWidth) {
      tooltip.style.left = window.innerWidth - tooltip.offsetWidth - 8 + 'px';
    }
  }

  hideTooltip() {
    const tooltip = document.querySelector('.tooltip-enterprise');
    if (tooltip) {
      tooltip.remove();
    }
  }

  // Keyboard Navigation
  initKeyboardNavigation() {
    // Add keyboard navigation to custom components
    document.addEventListener('keydown', (e) => {
      // Handle dropdown navigation
      if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
        const dropdown = e.target.closest('.dropdown');
        if (dropdown && dropdown.classList.contains('show')) {
          e.preventDefault();
          const items = dropdown.querySelectorAll('.dropdown-item');
          const currentIndex = Array.from(items).indexOf(document.activeElement);
          const nextIndex = e.key === 'ArrowDown' 
            ? (currentIndex + 1) % items.length 
            : (currentIndex - 1 + items.length) % items.length;
          items[nextIndex].focus();
        }
      }
    });
  }

  // Utility Methods
  showNotification(message, type = 'info', duration = 5000) {
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.style.cssText = `
      position: fixed; top: 1rem; right: 1rem; z-index: 1070;
      padding: 1rem 1.5rem; border-radius: 0.5rem; color: white;
      max-width: 400px; box-shadow: var(--shadow-lg);
      transform: translateX(100%); transition: transform 0.3s ease;
    `;
    
    const colors = {
      success: 'var(--success)',
      error: 'var(--error)',
      warning: 'var(--warning)',
      info: 'var(--info)'
    };
    
    notification.style.background = colors[type] || colors.info;
    notification.textContent = message;
    
    document.body.appendChild(notification);
    
    // Animate in
    setTimeout(() => {
      notification.style.transform = 'translateX(0)';
    }, 100);
    
    // Auto remove
    setTimeout(() => {
      notification.style.transform = 'translateX(100%)';
      setTimeout(() => notification.remove(), 300);
    }, duration);
  }

  // Performance optimization
  debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
      const later = () => {
        clearTimeout(timeout);
        func(...args);
      };
      clearTimeout(timeout);
      timeout = setTimeout(later, wait);
    };
  }
}

// Initialize framework when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
  window.enterpriseFramework = new EnterpriseFramework();
});

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
  module.exports = EnterpriseFramework;
}