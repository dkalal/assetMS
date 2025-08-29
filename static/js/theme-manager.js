/**
 * Enterprise Theme Manager
 * Handles system-wide theme switching with persistence
 */
class EnterpriseThemeManager {
    constructor() {
        this.currentTheme = 'light';
        this.storageKey = 'enterprise-theme-preference';
        this.init();
    }

    init() {
        this.loadThemePreference();
        this.createThemeToggle();
        this.bindEvents();
        this.detectSystemPreference();
        this.applyTheme(this.currentTheme);
    }

    loadThemePreference() {
        // Load from localStorage
        const saved = localStorage.getItem(this.storageKey);
        if (saved && ['light', 'dark'].includes(saved)) {
            this.currentTheme = saved;
        } else {
            // Detect system preference
            this.currentTheme = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
        }
    }

    saveThemePreference() {
        localStorage.setItem(this.storageKey, this.currentTheme);
        
        // Send to server for user profile
        if (window.fetch && document.body.classList.contains('authenticated')) {
            fetch('/api/user/theme-preference/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify({ theme: this.currentTheme })
            }).catch(() => {
                // Silent fail - theme still works locally
            });
        }
    }

    createThemeToggle() {
        // Only create if not exists
        if (document.getElementById('enterpriseThemeToggle')) return;

        const toggle = document.createElement('button');
        toggle.id = 'enterpriseThemeToggle';
        toggle.className = 'theme-toggle';
        toggle.setAttribute('aria-label', 'Toggle theme');
        toggle.innerHTML = '<i class="bi bi-moon-fill"></i>';
        
        document.body.appendChild(toggle);
        this.toggleButton = toggle;
    }

    bindEvents() {
        // Theme toggle click
        if (this.toggleButton) {
            this.toggleButton.addEventListener('click', () => {
                this.toggleTheme();
            });
        }

        // System theme change detection
        window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
            if (!localStorage.getItem(this.storageKey)) {
                this.currentTheme = e.matches ? 'dark' : 'light';
                this.applyTheme(this.currentTheme);
            }
        });

        // Keyboard shortcut (Ctrl/Cmd + Shift + T)
        document.addEventListener('keydown', (e) => {
            if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key === 'T') {
                e.preventDefault();
                this.toggleTheme();
            }
        });
    }

    detectSystemPreference() {
        // Respect system preference if no saved preference
        if (!localStorage.getItem(this.storageKey)) {
            const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
            this.currentTheme = prefersDark ? 'dark' : 'light';
        }
    }

    toggleTheme() {
        this.currentTheme = this.currentTheme === 'light' ? 'dark' : 'light';
        this.applyTheme(this.currentTheme);
        this.saveThemePreference();
        this.announceThemeChange();
    }

    applyTheme(theme) {
        // Apply to document and body immediately
        document.documentElement.setAttribute('data-theme', theme);
        document.body.setAttribute('data-theme', theme);
        
        // Remove old theme class and add new one
        document.body.classList.remove('theme-light', 'theme-dark');
        document.body.classList.add('theme-' + theme);
        
        // Update toggle button icon
        if (this.toggleButton) {
            const icon = this.toggleButton.querySelector('i');
            if (icon) {
                icon.className = theme === 'dark' ? 'bi bi-sun-fill' : 'bi bi-moon-fill';
            }
        }

        // Update meta theme-color for mobile browsers
        this.updateMetaThemeColor(theme);
        
        // Force style recalculation for all elements
        const allElements = document.querySelectorAll('*');
        allElements.forEach(el => {
            if (el.style) {
                el.style.transition = 'none';
                el.offsetHeight; // Trigger reflow
                el.style.transition = '';
            }
        });
        
        // Dispatch custom event for other components
        window.dispatchEvent(new CustomEvent('themeChanged', {
            detail: { theme, previousTheme: this.currentTheme }
        }));

        console.log(`🎨 Theme switched to: ${theme}`);
    }

    updateMetaThemeColor(theme) {
        let metaTheme = document.querySelector('meta[name="theme-color"]');
        if (!metaTheme) {
            metaTheme = document.createElement('meta');
            metaTheme.name = 'theme-color';
            document.head.appendChild(metaTheme);
        }
        
        metaTheme.content = theme === 'dark' ? '#1a1a1a' : '#ffffff';
    }

    announceThemeChange() {
        // Accessibility announcement
        const announcement = document.createElement('div');
        announcement.setAttribute('aria-live', 'polite');
        announcement.setAttribute('aria-atomic', 'true');
        announcement.className = 'sr-only';
        announcement.textContent = `Theme switched to ${this.currentTheme} mode`;
        
        document.body.appendChild(announcement);
        setTimeout(() => announcement.remove(), 1000);
    }

    getCSRFToken() {
        const cookies = document.cookie.split(';');
        for (let cookie of cookies) {
            const [name, value] = cookie.trim().split('=');
            if (name === 'csrftoken') {
                return value;
            }
        }
        return '';
    }

    // Public API
    getCurrentTheme() {
        return this.currentTheme;
    }

    setTheme(theme) {
        if (['light', 'dark'].includes(theme)) {
            this.currentTheme = theme;
            this.applyTheme(theme);
            this.saveThemePreference();
        }
    }

    // Auto theme based on time
    enableAutoTheme() {
        const hour = new Date().getHours();
        const autoTheme = (hour >= 18 || hour <= 6) ? 'dark' : 'light';
        this.setTheme(autoTheme);
        
        // Set up automatic switching
        setInterval(() => {
            const currentHour = new Date().getHours();
            const newAutoTheme = (currentHour >= 18 || currentHour <= 6) ? 'dark' : 'light';
            if (newAutoTheme !== this.currentTheme) {
                this.setTheme(newAutoTheme);
            }
        }, 60000); // Check every minute
    }
}

// Initialize theme immediately (before DOM ready)
(function() {
    const savedTheme = localStorage.getItem('enterprise-theme-preference') || 
                      (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
    
    // Apply theme to document and body immediately
    document.documentElement.setAttribute('data-theme', savedTheme);
    
    // Wait for body to be available
    const applyToBody = () => {
        if (document.body) {
            document.body.setAttribute('data-theme', savedTheme);
            document.body.classList.add('theme-' + savedTheme);
        } else {
            setTimeout(applyToBody, 10);
        }
    };
    applyToBody();
    
    console.log(`🎨 Theme pre-initialized: ${savedTheme}`);
})();

// Initialize theme manager when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    if (!window.enterpriseThemeManager) {
        window.enterpriseThemeManager = new EnterpriseThemeManager();
        console.log('🎨 Enterprise Theme Manager initialized');
    }
});

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
    module.exports = EnterpriseThemeManager;
}