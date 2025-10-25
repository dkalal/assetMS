/**
 * World-Class Global Search - Multi-Entity Search with Live Results
 * Searches across Assets, Users, Categories, and Branches
 * 
 * Features:
 * - Real-time search with debouncing (300ms)
 * - Dropdown results with icons and badges
 * - Keyboard navigation (Arrow keys, Enter, Escape)
 * - Click outside to close
 * - Loading states
 * - Error handling
 * - Accessibility (ARIA labels)
 */

(function() {
    'use strict';

    // Debounce function
    function debounce(fn, delay) {
        let timer;
        return function(...args) {
            clearTimeout(timer);
            timer = setTimeout(() => fn.apply(this, args), delay);
        };
    }

    // Get CSRF token
    function getCSRFToken() {
        return document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';
    }

    class GlobalSearch {
        constructor() {
            this.searchInput = document.getElementById('global-asset-search');
            this.searchForm = document.querySelector('form[role="search"]');
            this.resultsContainer = null;
            this.currentQuery = '';
            this.selectedIndex = -1;
            this.results = [];
            
            if (!this.searchInput) return;
            
            this.init();
        }

        init() {
            // Create results dropdown
            this.createResultsDropdown();
            
            // Bind events
            this.searchInput.addEventListener('input', debounce((e) => {
                this.handleInput(e);
            }, 300));
            
            this.searchInput.addEventListener('keydown', (e) => {
                this.handleKeydown(e);
            });
            
            this.searchInput.addEventListener('focus', () => {
                if (this.currentQuery && this.results.length > 0) {
                    this.showResults();
                }
            });
            
            // Click outside to close
            document.addEventListener('click', (e) => {
                if (!this.searchInput.contains(e.target) && !this.resultsContainer.contains(e.target)) {
                    this.hideResults();
                }
            });
        }

        createResultsDropdown() {
            // Create dropdown container
            this.resultsContainer = document.createElement('div');
            this.resultsContainer.className = 'global-search-results';
            this.resultsContainer.style.cssText = `
                position: absolute;
                top: 100%;
                left: 0;
                right: 0;
                background: white;
                border: 1px solid #dee2e6;
                border-radius: 8px;
                box-shadow: 0 4px 12px rgba(0,0,0,0.15);
                max-height: 400px;
                overflow-y: auto;
                z-index: 1050;
                display: none;
                margin-top: 4px;
            `;
            
            // Insert after search input's parent
            const inputGroup = this.searchInput.closest('.input-group');
            if (inputGroup) {
                inputGroup.style.position = 'relative';
                inputGroup.appendChild(this.resultsContainer);
            }
        }

        async handleInput(e) {
            const query = e.target.value.trim();
            this.currentQuery = query;
            
            if (query.length < 2) {
                this.hideResults();
                return;
            }
            
            // Show loading state
            this.showLoading();
            
            try {
                const response = await fetch(`/api/global-search/?q=${encodeURIComponent(query)}`, {
                    method: 'GET',
                    headers: {
                        'X-Requested-With': 'XMLHttpRequest',
                    }
                });
                
                const data = await response.json();
                
                if (data.success) {
                    this.results = data.results;
                    this.renderResults();
                } else {
                    this.showError(data.error || 'Search failed');
                }
            } catch (error) {
                console.error('Search error:', error);
                this.showError('Network error. Please try again.');
            }
        }

        showLoading() {
            this.resultsContainer.innerHTML = `
                <div class="p-3 text-center text-muted">
                    <div class="spinner-border spinner-border-sm me-2" role="status">
                        <span class="visually-hidden">Loading...</span>
                    </div>
                    Searching...
                </div>
            `;
            this.resultsContainer.style.display = 'block';
        }

        showError(message) {
            this.resultsContainer.innerHTML = `
                <div class="p-3 text-center text-danger">
                    <i class="bi bi-exclamation-circle me-2"></i>${message}
                </div>
            `;
            this.resultsContainer.style.display = 'block';
        }

        renderResults() {
            if (this.results.length === 0) {
                this.resultsContainer.innerHTML = `
                    <div class="p-3 text-center text-muted">
                        <i class="bi bi-search me-2"></i>No results found for "${this.currentQuery}"
                    </div>
                `;
                this.resultsContainer.style.display = 'block';
                return;
            }
            
            let html = '';
            
            // Group results by type
            const grouped = this.groupByType(this.results);
            
            for (const [type, items] of Object.entries(grouped)) {
                if (items.length === 0) continue;
                
                html += `
                    <div class="search-group">
                        <div class="search-group-header">${this.getTypeLabel(type)}</div>
                `;
                
                items.forEach((item, index) => {
                    const globalIndex = this.results.indexOf(item);
                    html += this.renderResultItem(item, globalIndex);
                });
                
                html += `</div>`;
            }
            
            this.resultsContainer.innerHTML = html;
            this.resultsContainer.style.display = 'block';
            this.selectedIndex = -1;
            
            // Add click handlers
            this.resultsContainer.querySelectorAll('.search-result-item').forEach((el, index) => {
                el.addEventListener('click', () => {
                    window.location.href = this.results[index].url;
                });
            });
        }

        renderResultItem(item, index) {
            return `
                <div class="search-result-item ${index === this.selectedIndex ? 'selected' : ''}" data-index="${index}">
                    <div class="d-flex align-items-center">
                        <i class="bi bi-${item.icon} me-3 text-primary" style="font-size: 1.25rem;"></i>
                        <div class="flex-grow-1">
                            <div class="fw-semibold">${this.escapeHtml(item.title)}</div>
                            <small class="text-muted">${this.escapeHtml(item.subtitle)}</small>
                        </div>
                        <span class="badge ${item.badge_class} ms-2">${this.escapeHtml(item.badge)}</span>
                    </div>
                </div>
            `;
        }

        groupByType(results) {
            const grouped = {
                asset: [],
                user: [],
                category: [],
                branch: []
            };
            
            results.forEach(item => {
                if (grouped[item.type]) {
                    grouped[item.type].push(item);
                }
            });
            
            return grouped;
        }

        getTypeLabel(type) {
            const labels = {
                asset: 'Assets',
                user: 'Users',
                category: 'Categories',
                branch: 'Branches'
            };
            return labels[type] || type;
        }

        handleKeydown(e) {
            if (!this.results.length) return;
            
            switch(e.key) {
                case 'ArrowDown':
                    e.preventDefault();
                    this.selectedIndex = Math.min(this.selectedIndex + 1, this.results.length - 1);
                    this.updateSelection();
                    break;
                    
                case 'ArrowUp':
                    e.preventDefault();
                    this.selectedIndex = Math.max(this.selectedIndex - 1, -1);
                    this.updateSelection();
                    break;
                    
                case 'Enter':
                    e.preventDefault();
                    if (this.selectedIndex >= 0) {
                        window.location.href = this.results[this.selectedIndex].url;
                    }
                    break;
                    
                case 'Escape':
                    this.hideResults();
                    this.searchInput.blur();
                    break;
            }
        }

        updateSelection() {
            const items = this.resultsContainer.querySelectorAll('.search-result-item');
            items.forEach((item, index) => {
                if (index === this.selectedIndex) {
                    item.classList.add('selected');
                    item.scrollIntoView({ block: 'nearest' });
                } else {
                    item.classList.remove('selected');
                }
            });
        }

        showResults() {
            this.resultsContainer.style.display = 'block';
        }

        hideResults() {
            this.resultsContainer.style.display = 'none';
            this.selectedIndex = -1;
        }

        escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }
    }

    // Initialize on DOM ready
    document.addEventListener('DOMContentLoaded', () => {
        new GlobalSearch();
    });

    // Add CSS styles
    const style = document.createElement('style');
    style.textContent = `
        .search-group {
            border-bottom: 1px solid #f0f0f0;
        }
        
        .search-group:last-child {
            border-bottom: none;
        }
        
        .search-group-header {
            padding: 8px 16px;
            background: #f8f9fa;
            font-size: 0.75rem;
            font-weight: 600;
            text-transform: uppercase;
            color: #6c757d;
            letter-spacing: 0.5px;
        }
        
        .search-result-item {
            padding: 12px 16px;
            cursor: pointer;
            transition: background-color 0.2s ease;
            border-left: 3px solid transparent;
        }
        
        .search-result-item:hover,
        .search-result-item.selected {
            background-color: #f8f9fa;
            border-left-color: #176B87;
        }
        
        .global-search-results::-webkit-scrollbar {
            width: 8px;
        }
        
        .global-search-results::-webkit-scrollbar-track {
            background: #f1f1f1;
            border-radius: 4px;
        }
        
        .global-search-results::-webkit-scrollbar-thumb {
            background: #888;
            border-radius: 4px;
        }
        
        .global-search-results::-webkit-scrollbar-thumb:hover {
            background: #555;
        }
    `;
    document.head.appendChild(style);
})();
