/**
 * Enterprise Table Enhancer - Automatically upgrades all tables to enterprise standard
 */

class TableEnhancer {
  constructor() {
    this.enhancedTables = new Set();
    this.debugMode = window.location.search.includes('debug=true');
    this.init();
  }
  
  log(message, type = 'info') {
    if (this.debugMode) {
      const prefix = '🏢 [TableEnhancer]';
      switch(type) {
        case 'error':
          console.error(`${prefix} ❌`, message);
          break;
        case 'warn':
          console.warn(`${prefix} ⚠️`, message);
          break;
        case 'success':
          console.log(`${prefix} ✅`, message);
          break;
        default:
          console.log(`${prefix} ℹ️`, message);
      }
    }
  }

  init() {
    // Enhance existing tables
    this.enhanceAllTables();
    
    // Watch for dynamically added tables
    this.observeNewTables();
    
    // Add global table utilities
    this.addGlobalUtilities();
  }

  enhanceAllTables() {
    const tables = document.querySelectorAll('table:not(.enterprise-table):not([data-enhanced])');
    this.log(`Found ${tables.length} tables to enhance`);
    tables.forEach((table, index) => {
      this.log(`Enhancing table ${index + 1}/${tables.length}: ${table.id || 'unnamed'}`);
      this.enhanceTable(table);
    });
    this.log(`Successfully enhanced ${tables.length} tables`, 'success');
  }

  enhanceTable(table) {
    // Skip if already enhanced
    if (this.enhancedTables.has(table) || 
        table.closest('.enterprise-table-container') ||
        table.classList.contains('enterprise-table') ||
        table.hasAttribute('data-enhanced')) {
      return;
    }
    
    // Mark as being processed
    table.setAttribute('data-enhanced', 'true');

    try {
      // Determine table type and apply appropriate enhancements
      const tableType = this.detectTableType(table);
      const options = this.getOptionsForTableType(tableType);
      
      this.log(`Table type detected: ${tableType}, Options: ${JSON.stringify(options)}`);
      
      // Apply enterprise styling
      this.applyEnterpriseStructure(table, options);
      
      // Initialize enterprise table functionality
      const enterpriseTable = new EnterpriseTable(table, options);
      table.enterpriseTable = enterpriseTable;
      
      this.enhancedTables.add(table);
      this.log(`Table enhanced successfully: ${table.id}`, 'success');
      
    } catch (error) {
      this.log(`Failed to enhance table ${table.id}: ${error.message}`, 'error');
      table.removeAttribute('data-enhanced');
    }
  }

  detectTableType(table) {
    const tableId = table.id;
    const tableClasses = table.className;
    const parentClasses = table.closest('[class*="dashboard"], [class*="settings"], [class*="assets"]')?.className || '';

    // Dashboard tables
    if (tableId.includes('activity') || tableId.includes('log') || parentClasses.includes('dashboard')) {
      return 'dashboard';
    }

    // Settings tables
    if (tableId.includes('settings') || parentClasses.includes('settings')) {
      return 'settings';
    }

    // Asset tables
    if (tableId.includes('asset') || parentClasses.includes('assets')) {
      return 'assets';
    }

    // Security tables
    if (tableId.includes('security') || tableId.includes('audit')) {
      return 'security';
    }

    // Report tables
    if (tableId.includes('report') || parentClasses.includes('report')) {
      return 'reports';
    }

    return 'default';
  }

  getOptionsForTableType(type) {
    const baseOptions = {
      sortable: true,
      selectable: false,
      searchable: true,
      pagination: true,
      pageSize: 20,
      maxHeight: '600px'
    };

    const typeOptions = {
      dashboard: {
        ...baseOptions,
        maxHeight: '400px',
        pageSize: 15,
        selectable: false
      },
      settings: {
        ...baseOptions,
        maxHeight: '500px',
        pageSize: 10,
        selectable: false
      },
      assets: {
        ...baseOptions,
        maxHeight: '700px',
        pageSize: 25,
        selectable: true
      },
      security: {
        ...baseOptions,
        maxHeight: '400px',
        pageSize: 20,
        selectable: false
      },
      reports: {
        ...baseOptions,
        maxHeight: '800px',
        pageSize: 50,
        selectable: true
      },
      default: baseOptions
    };

    return typeOptions[type] || typeOptions.default;
  }

  applyEnterpriseStructure(table, options) {
    // Add status badge styling to status columns
    this.enhanceStatusColumns(table);
    
    // Add action button styling
    this.enhanceActionColumns(table);
    
    // Add checkbox styling
    this.enhanceCheckboxes(table);
    
    // Add loading capability
    this.addLoadingCapability(table);
  }

  enhanceStatusColumns(table) {
    const statusCells = table.querySelectorAll('td, th');
    statusCells.forEach(cell => {
      const text = cell.textContent.toLowerCase().trim();
      
      // Common status values
      const statusMap = {
        'active': 'active',
        'inactive': 'inactive',
        'maintenance': 'maintenance',
        'retired': 'retired',
        'pending': 'maintenance',
        'approved': 'active',
        'rejected': 'retired',
        'success': 'active',
        'failed': 'retired',
        'warning': 'maintenance',
        'error': 'retired'
      };

      if (statusMap[text]) {
        // Don't modify if already has status badge
        if (!cell.querySelector('.status-badge')) {
          const badge = document.createElement('span');
          badge.className = `status-badge ${statusMap[text]}`;
          badge.textContent = cell.textContent;
          cell.innerHTML = '';
          cell.appendChild(badge);
        }
      }
    });
  }

  enhanceActionColumns(table) {
    const actionCells = table.querySelectorAll('td:last-child, th:last-child');
    actionCells.forEach(cell => {
      // Skip if header
      if (cell.tagName === 'TH') return;

      const buttons = cell.querySelectorAll('button, a.btn');
      if (buttons.length > 0) {
        // Wrap in action container
        const actionContainer = document.createElement('div');
        actionContainer.className = 'table-actions';
        
        buttons.forEach(button => {
          // Convert to table action button
          button.classList.remove('btn-sm', 'btn-outline-primary', 'btn-outline-secondary', 'btn-outline-danger');
          button.classList.add('table-action-btn');
          
          // Add appropriate styling based on content
          const buttonText = button.textContent.toLowerCase();
          if (buttonText.includes('edit') || button.querySelector('.bi-pencil')) {
            button.classList.add('primary');
          } else if (buttonText.includes('delete') || button.querySelector('.bi-trash')) {
            button.classList.add('danger');
          }
          
          actionContainer.appendChild(button);
        });
        
        cell.innerHTML = '';
        cell.appendChild(actionContainer);
      }
    });
  }

  enhanceCheckboxes(table) {
    const checkboxes = table.querySelectorAll('input[type="checkbox"]');
    checkboxes.forEach(checkbox => {
      if (!checkbox.classList.contains('table-checkbox')) {
        checkbox.classList.add('table-checkbox');
      }
    });
  }

  addLoadingCapability(table) {
    // Add data attributes for loading states
    table.setAttribute('data-loading', 'false');
    
    // Add methods to show/hide loading
    table.showLoading = function() {
      this.setAttribute('data-loading', 'true');
      const container = this.closest('.enterprise-table-container');
      if (container && !container.querySelector('.enterprise-table-loading')) {
        const loadingDiv = document.createElement('div');
        loadingDiv.className = 'enterprise-table-loading';
        loadingDiv.innerHTML = '<div class="spinner"></div>';
        container.appendChild(loadingDiv);
      }
    };
    
    table.hideLoading = function() {
      this.setAttribute('data-loading', 'false');
      const container = this.closest('.enterprise-table-container');
      if (container) {
        const loadingDiv = container.querySelector('.enterprise-table-loading');
        if (loadingDiv) loadingDiv.remove();
      }
    };
  }

  observeNewTables() {
    const observer = new MutationObserver((mutations) => {
      mutations.forEach((mutation) => {
        mutation.addedNodes.forEach((node) => {
          if (node.nodeType === Node.ELEMENT_NODE) {
            // Check if the added node is a table
            if (node.tagName === 'TABLE') {
              this.enhanceTable(node);
            }
            
            // Check for tables within the added node
            const tables = node.querySelectorAll?.('table:not(.enterprise-table):not([data-enhanced])');
            tables?.forEach(table => this.enhanceTable(table));
          }
        });
      });
    });

    observer.observe(document.body, {
      childList: true,
      subtree: true
    });
  }

  addGlobalUtilities() {
    // Add global table utilities to window
    window.TableUtils = {
      refreshTable: (tableId) => {
        const table = document.getElementById(tableId);
        if (table && table.enterpriseTable) {
          table.enterpriseTable.refreshTable();
        }
      },
      
      showTableLoading: (tableId) => {
        const table = document.getElementById(tableId);
        if (table && table.showLoading) {
          table.showLoading();
        }
      },
      
      hideTableLoading: (tableId) => {
        const table = document.getElementById(tableId);
        if (table && table.hideLoading) {
          table.hideLoading();
        }
      },
      
      getSelectedRows: (tableId) => {
        const table = document.getElementById(tableId);
        if (table && table.enterpriseTable) {
          return table.enterpriseTable.getSelectedRows();
        }
        return [];
      },
      
      clearSelection: (tableId) => {
        const table = document.getElementById(tableId);
        if (table && table.enterpriseTable) {
          table.enterpriseTable.clearSelection();
        }
      }
    };

    // Add CSS for enhanced elements
    this.addDynamicStyles();
  }

  addDynamicStyles() {
    const style = document.createElement('style');
    style.textContent = `
      /* Dynamic table enhancements */
      .table-enhanced {
        transition: all 0.3s ease;
      }
      
      .table-loading {
        opacity: 0.6;
        pointer-events: none;
      }
      
      /* Smooth transitions for status changes */
      .status-badge {
        transition: all 0.2s ease;
      }
      
      .status-badge:hover {
        transform: scale(1.05);
      }
      
      /* Enhanced action buttons */
      .table-actions .table-action-btn {
        transition: all 0.15s ease;
      }
      
      .table-actions .table-action-btn:not(:last-child) {
        margin-right: 4px;
      }
      
      /* Responsive table improvements */
      @media (max-width: 768px) {
        .enterprise-table-container {
          margin: 0 -15px;
          border-radius: 0;
        }
        
        .enterprise-table thead th {
          font-size: 0.75rem;
          padding: 8px 6px;
        }
        
        .enterprise-table tbody td {
          font-size: 0.75rem;
          padding: 8px 6px;
        }
      }
    `;
    
    document.head.appendChild(style);
  }
}

// Initialize table enhancer when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
  // Small delay to ensure all other scripts have loaded
  setTimeout(() => {
    new TableEnhancer();
  }, 100);
});

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
  module.exports = TableEnhancer;
}