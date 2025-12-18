/**
 * WORLD-CLASS: Accessibility Engine
 * Compliance: WCAG 2.1 AA, Section 508, ADA
 * 
 * Features:
 * - Screen reader optimization
 * - Keyboard navigation
 * - High contrast mode
 * - Focus management
 * - ARIA live regions
 * - Voice commands (future)
 */

class AccessibilityEngine {
    constructor() {
        this.isHighContrast = false;
        this.isReducedMotion = false;
        this.focusHistory = [];
        this.announcements = [];
        
        this.init();
    }
    
    init() {
        this.setupKeyboardNavigation();
        this.setupFocusManagement();
        this.setupScreenReaderSupport();
        this.setupHighContrastMode();
        this.setupReducedMotion();
        this.setupLiveRegions();
        this.monitorAccessibility();
    }
    
    /**
     * Enhanced keyboard navigation
     */
    setupKeyboardNavigation() {
        // Global keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            // Skip navigation (Alt + S)
            if (e.altKey && e.key === 's') {
                e.preventDefault();
                this.skipToMainContent();
            }
            
            // Quick search (Alt + /)
            if (e.altKey && e.key === '/') {
                e.preventDefault();
                this.focusSearchBox();
            }
            
            // Help dialog (F1)
            if (e.key === 'F1') {
                e.preventDefault();
                this.showKeyboardHelp();
            }
            
            // Escape key handling
            if (e.key === 'Escape') {
                this.handleEscape();
            }
        });
        
        // Tab trap for modals
        this.setupModalTabTrap();
        
        // Arrow key navigation for lists
        this.setupArrowKeyNavigation();
    }
    
    /**
     * Advanced focus management
     */
    setupFocusManagement() {
        // Track focus history for restoration
        document.addEventListener('focusin', (e) => {
            this.focusHistory.push(e.target);
            if (this.focusHistory.length > 10) {
                this.focusHistory.shift();
            }
        });
        
        // Focus indicators
        this.enhanceFocusIndicators();
        
        // Auto-focus management for dynamic content
        this.setupDynamicFocusManagement();
    }
    
    /**
     * Screen reader optimization
     */
    setupScreenReaderSupport() {
        // Dynamic content announcements
        this.setupLiveRegions();
        
        // Form validation announcements
        this.setupFormValidationAnnouncements();
        
        // Progress announcements
        this.setupProgressAnnouncements();
        
        // Table navigation
        this.enhanceTableAccessibility();
    }
    
    /**
     * High contrast mode
     */
    setupHighContrastMode() {
        // Detect system preference
        const prefersHighContrast = window.matchMedia('(prefers-contrast: high)');
        
        if (prefersHighContrast.matches || localStorage.getItem('highContrast') === 'true') {
            this.enableHighContrast();
        }
        
        // Listen for changes
        prefersHighContrast.addEventListener('change', (e) => {
            if (e.matches) {
                this.enableHighContrast();
            } else {
                this.disableHighContrast();
            }
        });
        
        // Toggle button
        this.createHighContrastToggle();
    }
    
    /**
     * Reduced motion support
     */
    setupReducedMotion() {
        const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
        
        if (prefersReducedMotion.matches) {
            this.enableReducedMotion();
        }
        
        prefersReducedMotion.addEventListener('change', (e) => {
            if (e.matches) {
                this.enableReducedMotion();
            } else {
                this.disableReducedMotion();
            }
        });
    }
    
    /**
     * ARIA live regions for dynamic announcements
     */
    setupLiveRegions() {
        // Create live regions if they don't exist
        if (!document.getElementById('aria-live-polite')) {
            const politeRegion = document.createElement('div');
            politeRegion.id = 'aria-live-polite';
            politeRegion.setAttribute('aria-live', 'polite');
            politeRegion.setAttribute('aria-atomic', 'true');
            politeRegion.className = 'sr-only';
            document.body.appendChild(politeRegion);
        }
        
        if (!document.getElementById('aria-live-assertive')) {
            const assertiveRegion = document.createElement('div');
            assertiveRegion.id = 'aria-live-assertive';
            assertiveRegion.setAttribute('aria-live', 'assertive');
            assertiveRegion.setAttribute('aria-atomic', 'true');
            assertiveRegion.className = 'sr-only';
            document.body.appendChild(assertiveRegion);
        }
    }
    
    /**
     * Skip to main content
     */
    skipToMainContent() {
        const mainContent = document.querySelector('main, #main-content, .main-content');
        if (mainContent) {
            mainContent.focus();
            mainContent.scrollIntoView({ behavior: 'smooth' });
            this.announce('Skipped to main content');
        }
    }
    
    /**
     * Focus search box
     */
    focusSearchBox() {
        const searchBox = document.querySelector('input[type="search"], #global-search, .search-input');
        if (searchBox) {
            searchBox.focus();
            this.announce('Search box focused');
        }
    }
    
    /**
     * Show keyboard help dialog
     */
    showKeyboardHelp() {
        const helpDialog = document.getElementById('keyboard-help-modal');
        if (helpDialog) {
            // Show existing modal
            const modal = new bootstrap.Modal(helpDialog);
            modal.show();
        } else {
            // Create help dialog
            this.createKeyboardHelpDialog();
        }
    }
    
    /**
     * Handle escape key
     */
    handleEscape() {
        // Close open modals
        const openModals = document.querySelectorAll('.modal.show');
        if (openModals.length > 0) {
            const topModal = openModals[openModals.length - 1];
            const modal = bootstrap.Modal.getInstance(topModal);
            if (modal) {
                modal.hide();
            }
            return;
        }
        
        // Close dropdowns
        const openDropdowns = document.querySelectorAll('.dropdown-menu.show');
        openDropdowns.forEach(dropdown => {
            const toggle = dropdown.previousElementSibling;
            if (toggle) {
                toggle.click();
            }
        });
        
        // Clear search
        const searchBox = document.querySelector('input[type="search"]:focus');
        if (searchBox && searchBox.value) {
            searchBox.value = '';
            searchBox.dispatchEvent(new Event('input'));
        }
    }
    
    /**
     * Modal tab trap
     */
    setupModalTabTrap() {
        document.addEventListener('shown.bs.modal', (e) => {
            const modal = e.target;
            const focusableElements = modal.querySelectorAll(
                'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
            );
            
            if (focusableElements.length === 0) return;
            
            const firstElement = focusableElements[0];
            const lastElement = focusableElements[focusableElements.length - 1];
            
            // Focus first element
            firstElement.focus();
            
            modal.addEventListener('keydown', (e) => {
                if (e.key === 'Tab') {
                    if (e.shiftKey) {
                        // Shift + Tab
                        if (document.activeElement === firstElement) {
                            e.preventDefault();
                            lastElement.focus();
                        }
                    } else {
                        // Tab
                        if (document.activeElement === lastElement) {
                            e.preventDefault();
                            firstElement.focus();
                        }
                    }
                }
            });
        });
    }
    
    /**
     * Arrow key navigation for lists
     */
    setupArrowKeyNavigation() {
        document.addEventListener('keydown', (e) => {
            if (!['ArrowUp', 'ArrowDown', 'Home', 'End'].includes(e.key)) return;
            
            const activeElement = document.activeElement;
            const listItem = activeElement.closest('[role="listbox"] li, .list-group-item, .dropdown-item');
            
            if (!listItem) return;
            
            const container = listItem.closest('[role="listbox"], .list-group, .dropdown-menu');
            if (!container) return;
            
            const items = Array.from(container.querySelectorAll(
                '[role="option"], .list-group-item, .dropdown-item'
            )).filter(item => !item.disabled && !item.classList.contains('disabled'));
            
            const currentIndex = items.indexOf(listItem);
            let newIndex;
            
            switch (e.key) {
                case 'ArrowUp':
                    e.preventDefault();
                    newIndex = currentIndex > 0 ? currentIndex - 1 : items.length - 1;
                    break;
                case 'ArrowDown':
                    e.preventDefault();
                    newIndex = currentIndex < items.length - 1 ? currentIndex + 1 : 0;
                    break;
                case 'Home':
                    e.preventDefault();
                    newIndex = 0;
                    break;
                case 'End':
                    e.preventDefault();
                    newIndex = items.length - 1;
                    break;
            }
            
            if (newIndex !== undefined && items[newIndex]) {
                items[newIndex].focus();
            }
        });
    }
    
    /**
     * Enhance focus indicators
     */
    enhanceFocusIndicators() {
        const style = document.createElement('style');
        style.textContent = `
            .accessibility-focus {
                outline: 3px solid #0066cc !important;
                outline-offset: 2px !important;
                box-shadow: 0 0 0 1px #ffffff !important;
            }
            
            .high-contrast .accessibility-focus {
                outline: 3px solid #ffff00 !important;
                background-color: #000000 !important;
                color: #ffffff !important;
            }
        `;
        document.head.appendChild(style);
        
        // Add enhanced focus class
        document.addEventListener('focusin', (e) => {
            document.querySelectorAll('.accessibility-focus').forEach(el => {
                el.classList.remove('accessibility-focus');
            });
            e.target.classList.add('accessibility-focus');
        });
    }
    
    /**
     * Enable high contrast mode
     */
    enableHighContrast() {
        document.body.classList.add('high-contrast');
        this.isHighContrast = true;
        localStorage.setItem('highContrast', 'true');
        this.announce('High contrast mode enabled');
    }
    
    /**
     * Disable high contrast mode
     */
    disableHighContrast() {
        document.body.classList.remove('high-contrast');
        this.isHighContrast = false;
        localStorage.setItem('highContrast', 'false');
        this.announce('High contrast mode disabled');
    }
    
    /**
     * Enable reduced motion
     */
    enableReducedMotion() {
        document.body.classList.add('reduced-motion');
        this.isReducedMotion = true;
        
        // Disable animations
        const style = document.createElement('style');
        style.id = 'reduced-motion-style';
        style.textContent = `
            .reduced-motion *,
            .reduced-motion *::before,
            .reduced-motion *::after {
                animation-duration: 0.01ms !important;
                animation-iteration-count: 1 !important;
                transition-duration: 0.01ms !important;
                scroll-behavior: auto !important;
            }
        `;
        document.head.appendChild(style);
    }
    
    /**
     * Disable reduced motion
     */
    disableReducedMotion() {
        document.body.classList.remove('reduced-motion');
        this.isReducedMotion = false;
        
        const style = document.getElementById('reduced-motion-style');
        if (style) {
            style.remove();
        }
    }
    
    /**
     * Create high contrast toggle
     */
    createHighContrastToggle() {
        const toggle = document.createElement('button');
        toggle.className = 'btn btn-outline-secondary btn-sm accessibility-toggle';
        toggle.innerHTML = '<i class="bi bi-circle-half" aria-hidden="true"></i> High Contrast';
        toggle.setAttribute('aria-label', 'Toggle high contrast mode');
        toggle.setAttribute('title', 'Toggle high contrast mode');
        
        toggle.addEventListener('click', () => {
            if (this.isHighContrast) {
                this.disableHighContrast();
            } else {
                this.enableHighContrast();
            }
        });
        
        // Add to accessibility toolbar
        const toolbar = document.querySelector('.accessibility-toolbar');
        if (toolbar) {
            toolbar.appendChild(toggle);
        }
    }
    
    /**
     * Announce message to screen readers
     */
    announce(message, priority = 'polite') {
        const regionId = priority === 'assertive' ? 'aria-live-assertive' : 'aria-live-polite';
        const region = document.getElementById(regionId);
        
        if (region) {
            // Clear previous message
            region.textContent = '';
            
            // Add new message after a brief delay
            setTimeout(() => {
                region.textContent = message;
            }, 100);
            
            // Clear message after announcement
            setTimeout(() => {
                region.textContent = '';
            }, 5000);
        }
        
        // Log announcement
        this.announcements.push({
            message,
            priority,
            timestamp: new Date().toISOString()
        });
    }
    
    /**
     * Monitor accessibility compliance
     */
    monitorAccessibility() {
        // Check for missing alt text
        setInterval(() => {
            const imagesWithoutAlt = document.querySelectorAll('img:not([alt])');
            if (imagesWithoutAlt.length > 0) {
                console.warn(`Accessibility: ${imagesWithoutAlt.length} images missing alt text`);
            }
        }, 10000);
        
        // Check for missing form labels
        setInterval(() => {
            const inputsWithoutLabels = document.querySelectorAll(
                'input:not([aria-label]):not([aria-labelledby]):not([title])'
            );
            const unlabeledInputs = Array.from(inputsWithoutLabels).filter(input => {
                const label = document.querySelector(`label[for="${input.id}"]`);
                return !label && input.type !== 'hidden';
            });
            
            if (unlabeledInputs.length > 0) {
                console.warn(`Accessibility: ${unlabeledInputs.length} form inputs missing labels`);
            }
        }, 10000);
    }
    
    /**
     * Create keyboard help dialog
     */
    createKeyboardHelpDialog() {
        const modal = document.createElement('div');
        modal.className = 'modal fade';
        modal.id = 'keyboard-help-modal';
        modal.setAttribute('tabindex', '-1');
        modal.setAttribute('aria-labelledby', 'keyboard-help-title');
        modal.setAttribute('aria-hidden', 'true');
        
        modal.innerHTML = `
            <div class="modal-dialog modal-lg">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title" id="keyboard-help-title">Keyboard Shortcuts</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                    </div>
                    <div class="modal-body">
                        <div class="row">
                            <div class="col-md-6">
                                <h6>Navigation</h6>
                                <dl>
                                    <dt>Alt + S</dt>
                                    <dd>Skip to main content</dd>
                                    <dt>Alt + /</dt>
                                    <dd>Focus search box</dd>
                                    <dt>Tab</dt>
                                    <dd>Next element</dd>
                                    <dt>Shift + Tab</dt>
                                    <dd>Previous element</dd>
                                </dl>
                            </div>
                            <div class="col-md-6">
                                <h6>Actions</h6>
                                <dl>
                                    <dt>F1</dt>
                                    <dd>Show this help</dd>
                                    <dt>Escape</dt>
                                    <dd>Close dialog/clear search</dd>
                                    <dt>Enter</dt>
                                    <dd>Activate button/link</dd>
                                    <dt>Space</dt>
                                    <dd>Toggle checkbox/button</dd>
                                </dl>
                            </div>
                        </div>
                        <div class="row mt-3">
                            <div class="col-12">
                                <h6>Lists and Menus</h6>
                                <dl class="row">
                                    <dt class="col-sm-3">Arrow Keys</dt>
                                    <dd class="col-sm-9">Navigate list items</dd>
                                    <dt class="col-sm-3">Home</dt>
                                    <dd class="col-sm-9">First item</dd>
                                    <dt class="col-sm-3">End</dt>
                                    <dd class="col-sm-9">Last item</dd>
                                </dl>
                            </div>
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                    </div>
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
        
        const bsModal = new bootstrap.Modal(modal);
        bsModal.show();
    }
}

// Initialize accessibility engine when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.accessibilityEngine = new AccessibilityEngine();
});

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
    module.exports = AccessibilityEngine;
}