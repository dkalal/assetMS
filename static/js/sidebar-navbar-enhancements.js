/**
 * ============================================================================
 * PHASE 3: SIDEBAR & NAVBAR ENHANCEMENT SCRIPTS
 * ============================================================================
 * Provides interactive functionality for world-class navigation
 * ============================================================================
 */

(function() {
  'use strict';

  /**
   * Initialize when DOM is ready
   */
  function init() {
    enhanceNavbar();
    enhanceSidebar();
    setupSkipLink();
    setupKeyboardShortcuts();
  }

  /**
   * Enhance Navbar - Scroll Effects & Active States
   */
  function enhanceNavbar() {
    const navbar = document.querySelector('.enterprise-navbar');
    if (!navbar) return;

    let lastScroll = 0;

    window.addEventListener('scroll', () => {
      const currentScroll = window.pageYOffset;

      // Add 'scrolled' class when scrolled
      if (currentScroll > 20) {
        navbar.classList.add('scrolled');
      } else {
        navbar.classList.remove('scrolled');
      }

      lastScroll = currentScroll;
    }, { passive: true });

    // Highlight active search input
    const searchInput = navbar.querySelector('input[type="search"]');
    if (searchInput) {
      searchInput.addEventListener('focus', function() {
        this.parentElement.classList.add('focused');
      });

      searchInput.addEventListener('blur', function() {
        this.parentElement.classList.remove('focused');
      });
    }
  }

  /**
   * Enhance Sidebar - Active State Management & Smooth Scrolling
   */
  function enhanceSidebar() {
    const sidebar = document.querySelector('.dashboard-sidebar');
    if (!sidebar) return;

    // Smooth scroll to active link on page load
    const activeLink = sidebar.querySelector('.nav-link.active, .rail-item.active');
    if (activeLink) {
      setTimeout(() => {
        activeLink.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
      }, 300);
    }

    // Add ripple effect on click (optional)
    const navLinks = sidebar.querySelectorAll('.nav-link, .rail-item');
    navLinks.forEach(link => {
      link.addEventListener('click', function(e) {
        // Create ripple element
        const ripple = document.createElement('span');
        ripple.classList.add('ripple-effect');
        
        // Position ripple
        const rect = this.getBoundingClientRect();
        const size = Math.max(rect.width, rect.height);
        const x = e.clientX - rect.left - size / 2;
        const y = e.clientY - rect.top - size / 2;
        
        ripple.style.width = ripple.style.height = size + 'px';
        ripple.style.left = x + 'px';
        ripple.style.top = y + 'px';
        
        // Add to link
        this.appendChild(ripple);
        
        // Remove after animation
        setTimeout(() => ripple.remove(), 600);
      });
    });

    // Collapse sidebar sections (if needed)
    setupSidebarCollapse();
  }

  /**
   * Setup Sidebar Collapse for Mobile
   */
  function setupSidebarCollapse() {
    const mobileSidebarToggle = document.getElementById('mobile-sidebar-toggle');
    const sidebarBackdrop = document.getElementById('sidebar-backdrop');
    const body = document.body;
    const sidebar = document.querySelector('.dashboard-sidebar');

    // Mobile sidebar toggle button
    if (mobileSidebarToggle) {
      mobileSidebarToggle.addEventListener('click', () => {
        const isOpen = body.classList.toggle('sidebar-open');
        mobileSidebarToggle.setAttribute('aria-expanded', isOpen);
        
        if (sidebar) {
          sidebar.setAttribute('aria-hidden', !isOpen);
        }
      });
    }

    // Backdrop click closes sidebar
    if (sidebarBackdrop) {
      sidebarBackdrop.addEventListener('click', () => {
        body.classList.remove('sidebar-open');
        if (mobileSidebarToggle) {
          mobileSidebarToggle.setAttribute('aria-expanded', 'false');
        }
        if (sidebar) {
          sidebar.setAttribute('aria-hidden', 'true');
        }
      });
    }

    // Close sidebar on ESC key
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && body.classList.contains('sidebar-open')) {
        body.classList.remove('sidebar-open');
        if (mobileSidebarToggle) {
          mobileSidebarToggle.setAttribute('aria-expanded', 'false');
        }
        if (sidebar) {
          sidebar.setAttribute('aria-hidden', 'true');
        }
      }
    });

    // Close sidebar on route change (for SPA-like navigation)
    const navLinks = document.querySelectorAll('.dashboard-sidebar .nav-link, .dashboard-sidebar .rail-item');
    navLinks.forEach(link => {
      link.addEventListener('click', () => {
        if (window.innerWidth <= 991) {
          setTimeout(() => {
            body.classList.remove('sidebar-open');
            if (mobileSidebarToggle) {
              mobileSidebarToggle.setAttribute('aria-expanded', 'false');
            }
            if (sidebar) {
              sidebar.setAttribute('aria-hidden', 'true');
            }
          }, 200);
        }
      });
    });

    // Handle window resize
    let resizeTimer;
    window.addEventListener('resize', () => {
      clearTimeout(resizeTimer);
      resizeTimer = setTimeout(() => {
        // Close sidebar if resizing to desktop
        if (window.innerWidth > 991 && body.classList.contains('sidebar-open')) {
          body.classList.remove('sidebar-open');
          if (mobileSidebarToggle) {
            mobileSidebarToggle.setAttribute('aria-expanded', 'false');
          }
          if (sidebar) {
            sidebar.setAttribute('aria-hidden', 'false');
          }
        }
      }, 250);
    });
  }

  /**
   * Setup Skip to Main Content Link (Accessibility)
   */
  function setupSkipLink() {
    const skipLink = document.querySelector('.skip-to-main');
    const mainContent = document.querySelector('.dashboard-content, main[role="main"]');

    if (skipLink && mainContent) {
      skipLink.addEventListener('click', (e) => {
        e.preventDefault();
        mainContent.setAttribute('tabindex', '-1');
        mainContent.focus();
        mainContent.scrollIntoView({ behavior: 'smooth' });
      });
    }
  }

  /**
   * Setup Keyboard Shortcuts (Accessibility & Power Users)
   */
  function setupKeyboardShortcuts() {
    document.addEventListener('keydown', (e) => {
      // Ctrl/Cmd + K: Focus Search
      if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        const searchInput = document.querySelector('.enterprise-navbar input[type="search"]');
        if (searchInput) {
          searchInput.focus();
          searchInput.select();
        }
      }

      // Ctrl/Cmd + B: Toggle Sidebar (mobile)
      if ((e.ctrlKey || e.metaKey) && e.key === 'b' && window.innerWidth <= 900) {
        e.preventDefault();
        document.body.classList.toggle('sidebar-open');
      }

      // Alt + 1-9: Quick Navigation to Sidebar Items
      if (e.altKey && /^[1-9]$/.test(e.key)) {
        e.preventDefault();
        const index = parseInt(e.key) - 1;
        const navLinks = document.querySelectorAll('.dashboard-sidebar .nav-link, .dashboard-sidebar .rail-item');
        if (navLinks[index]) {
          navLinks[index].click();
        }
      }
    });
  }

  /**
   * Auto-close dropdowns when clicking outside (Enhancement)
   */
  function setupDropdownAutoClose() {
    const dropdowns = document.querySelectorAll('.dropdown');
    
    document.addEventListener('click', (e) => {
      dropdowns.forEach(dropdown => {
        const toggle = dropdown.querySelector('[data-bs-toggle="dropdown"]');
        const menu = dropdown.querySelector('.dropdown-menu');
        
        if (menu && menu.classList.contains('show')) {
          if (!dropdown.contains(e.target)) {
            const bsDropdown = bootstrap.Dropdown.getInstance(toggle);
            if (bsDropdown) {
              bsDropdown.hide();
            }
          }
        }
      });
    });
  }

  /**
   * Add smooth reveal animation for sidebar on page load
   */
  function addSidebarRevealAnimation() {
    const sidebar = document.querySelector('.dashboard-sidebar');
    if (!sidebar) return;

    sidebar.style.opacity = '0';
    sidebar.style.transform = 'translateX(-20px)';

    setTimeout(() => {
      sidebar.style.transition = 'opacity 0.3s ease, transform 0.3s ease';
      sidebar.style.opacity = '1';
      sidebar.style.transform = 'translateX(0)';
    }, 100);
  }

  /**
   * Tooltip Enhancement for Truncated Text
   */
  function enhanceTooltips() {
    const navLinks = document.querySelectorAll('.dashboard-sidebar .nav-link, .dashboard-sidebar .rail-item');
    
    navLinks.forEach(link => {
      const span = link.querySelector('span:not(.badge)');
      if (span && span.scrollWidth > span.clientWidth) {
        link.setAttribute('title', span.textContent.trim());
      }
    });
  }

  /**
   * Badge Pulse Animation for Unread Counts
   */
  function animateBadges() {
    const badges = document.querySelectorAll('.badge.bg-danger, .badge.bg-warning');
    
    badges.forEach(badge => {
      const count = parseInt(badge.textContent);
      if (count > 0) {
        badge.style.animation = 'pulse 2s infinite';
      }
    });
  }

  /**
   * Progressive Enhancement: Add CSS animations
   */
  function addCSSAnimations() {
    const style = document.createElement('style');
    style.textContent = `
      @keyframes pulse {
        0%, 100% { transform: scale(1); }
        50% { transform: scale(1.1); }
      }
      
      @keyframes ripple {
        to { transform: scale(4); opacity: 0; }
      }
      
      .ripple-effect {
        position: absolute;
        border-radius: 50%;
        background: rgba(107, 155, 209, 0.3);
        pointer-events: none;
        animation: ripple 0.6s ease-out;
      }
      
      .nav-link, .rail-item {
        position: relative;
        overflow: hidden;
      }
    `;
    document.head.appendChild(style);
  }

  // Initialize all enhancements
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  // Additional setup
  addCSSAnimations();
  addSidebarRevealAnimation();
  enhanceTooltips();
  animateBadges();
  setupDropdownAutoClose();

})();

/**
 * Export for use in other modules if needed
 */
if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    enhanceNavbar,
    enhanceSidebar
  };
}
