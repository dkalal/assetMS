/**
 * Enterprise Table System - Professional sticky header tables with advanced features
 */

// Global ID registry to prevent conflicts
class EnterpriseIdRegistry {
  constructor() {
    this.usedIds = new Set();
  }
  
  generateUniqueId(prefix = 'enterprise') {
    let id;
    let attempts = 0;
    const maxAttempts = 1000;
    
    do {
      const timestamp = Date.now();
      const random = Math.random().toString(36).substr(2, 9);
      id = `${prefix}_${timestamp}_${random}`;
      attempts++;
    } while (this.usedIds.has(id) && attempts < maxAttempts);
    
    if (attempts >= maxAttempts) {
      throw new Error('Unable to generate unique ID after maximum attempts');
    }
    
    this.usedIds.add(id);
    return id;
  }
  
  releaseId(id) {
    this.usedIds.delete(id);
  }
  
  isIdUsed(id) {
    return this.usedIds.has(id) || document.getElementById(id) !== null;
  }
}

// Global instance
const enterpriseIdRegistry = new EnterpriseIdRegistry();

class EnterpriseTable {
  constructor(tableElement, options = {}) {
    this.table = tableElement;
    this.tableId = this.generateUniqueId(tableElement);
    this.options = {
      sortable: true,
      selectable: true,
      searchable: true,
      pagination: true,
      pageSize: 20,
      maxHeight: '600px',
      stickyHeader: true,
      ...options
    };
    
    this.currentSort = { column: null, direction: null };
    this.selectedRows = new Set();
    this.currentPage = 1;
    this.filteredData = [];
    this.originalData = [];
    this.paginationIds = null;
    
    this.init();
  }
  
  generateUniqueId(element) {
    if (element.id && !enterpriseIdRegistry.isIdUsed(element.id)) {
      enterpriseIdRegistry.usedIds.add(element.id);
      return element.id;
    }
    
    const uniqueId = enterpriseIdRegistry.generateUniqueId('table');
    element.id = uniqueId;
    return uniqueId;
  }

  init() {
    this.wrapTable();
    this.enhanceHeader();
    this.addEventListeners();
    this.initializeData();
    
    if (this.options.searchable) {
      this.addSearchBox();
    }
    
    if (this.options.pagination) {
      this.addPagination();
    }
  }

  wrapTable() {
    // Create enterprise table structure
    const container = document.createElement('div');
    container.className = 'enterprise-table-container';
    
    const wrapper = document.createElement('div');
    wrapper.className = 'enterprise-table-wrapper';
    wrapper.style.maxHeight = this.options.maxHeight;
    
    // Replace original table classes
    this.table.className = 'enterprise-table';
    
    // Wrap the table
    this.table.parentNode.insertBefore(container, this.table);
    container.appendChild(wrapper);
    wrapper.appendChild(this.table);
    
    this.container = container;
    this.wrapper = wrapper;
  }

  enhanceHeader() {
    const thead = this.table.querySelector('thead');
    if (!thead) return;

    const headers = thead.querySelectorAll('th');
    headers.forEach((header, index) => {
      // Skip checkbox column and action columns
      if (header.querySelector('input[type="checkbox"]') || 
          header.textContent.toLowerCase().includes('action')) {
        return;
      }

      if (this.options.sortable) {
        header.classList.add('sortable');
        header.setAttribute('data-column', index);
        header.style.cursor = 'pointer';
      }
    });
  }

  addEventListeners() {
    // Sort functionality
    if (this.options.sortable) {
      this.table.addEventListener('click', (e) => {
        const header = e.target.closest('th.sortable');
        if (header) {
          this.handleSort(header);
        }
      });
    }

    // Row selection
    if (this.options.selectable) {
      this.table.addEventListener('change', (e) => {
        if (e.target.type === 'checkbox') {
          this.handleRowSelection(e.target);
        }
      });
    }

    // Row hover effects
    this.table.addEventListener('mouseenter', (e) => {
      if (e.target.closest('tbody tr')) {
        e.target.closest('tbody tr').style.transform = 'translateY(-1px)';
      }
    }, true);

    this.table.addEventListener('mouseleave', (e) => {
      if (e.target.closest('tbody tr')) {
        e.target.closest('tbody tr').style.transform = '';
      }
    }, true);
  }

  handleSort(header) {
    const column = header.getAttribute('data-column');
    const currentDirection = this.currentSort.column === column ? this.currentSort.direction : null;
    
    // Clear previous sort indicators
    this.table.querySelectorAll('th').forEach(th => {
      th.classList.remove('sort-asc', 'sort-desc');
    });

    // Determine new sort direction
    let newDirection;
    if (currentDirection === 'asc') {
      newDirection = 'desc';
    } else if (currentDirection === 'desc') {
      newDirection = null; // Reset to original order
    } else {
      newDirection = 'asc';
    }

    this.currentSort = { column, direction: newDirection };

    // Apply sort indicator
    if (newDirection) {
      header.classList.add(`sort-${newDirection}`);
    }

    // Perform sort
    this.sortTable(column, newDirection);
  }

  sortTable(columnIndex, direction) {
    const tbody = this.table.querySelector('tbody');
    const rows = Array.from(tbody.querySelectorAll('tr'));

    if (!direction) {
      // Reset to original order
      this.restoreOriginalOrder();
      return;
    }

    rows.sort((a, b) => {
      const aCell = a.cells[columnIndex];
      const bCell = b.cells[columnIndex];
      
      if (!aCell || !bCell) return 0;

      let aValue = aCell.textContent.trim();
      let bValue = bCell.textContent.trim();

      // Try to parse as numbers
      const aNum = parseFloat(aValue.replace(/[^0-9.-]/g, ''));
      const bNum = parseFloat(bValue.replace(/[^0-9.-]/g, ''));

      if (!isNaN(aNum) && !isNaN(bNum)) {
        return direction === 'asc' ? aNum - bNum : bNum - aNum;
      }

      // Try to parse as dates
      const aDate = new Date(aValue);
      const bDate = new Date(bValue);

      if (!isNaN(aDate.getTime()) && !isNaN(bDate.getTime())) {
        return direction === 'asc' ? aDate - bDate : bDate - aDate;
      }

      // String comparison
      const comparison = aValue.localeCompare(bValue);
      return direction === 'asc' ? comparison : -comparison;
    });

    // Re-append sorted rows
    rows.forEach(row => tbody.appendChild(row));
  }

  restoreOriginalOrder() {
    // Implementation would restore original row order
    // For now, we'll just refresh the table
    this.refreshTable();
  }

  handleRowSelection(checkbox) {
    const row = checkbox.closest('tr');
    const rowId = row.getAttribute('data-id') || row.rowIndex;

    if (checkbox.checked) {
      this.selectedRows.add(rowId);
      row.classList.add('selected');
    } else {
      this.selectedRows.delete(rowId);
      row.classList.remove('selected');
    }

    // Handle select all checkbox
    if (checkbox.closest('thead')) {
      const bodyCheckboxes = this.table.querySelectorAll('tbody input[type="checkbox"]');
      bodyCheckboxes.forEach(cb => {
        const bodyRow = cb.closest('tr');
        const bodyRowId = bodyRow.getAttribute('data-id') || bodyRow.rowIndex;
        
        cb.checked = checkbox.checked;
        if (checkbox.checked) {
          this.selectedRows.add(bodyRowId);
          bodyRow.classList.add('selected');
        } else {
          this.selectedRows.delete(bodyRowId);
          bodyRow.classList.remove('selected');
        }
      });
    } else {
      // Update select all checkbox state
      const selectAllCheckbox = this.table.querySelector('thead input[type="checkbox"]');
      if (selectAllCheckbox) {
        const bodyCheckboxes = this.table.querySelectorAll('tbody input[type="checkbox"]');
        const checkedBoxes = this.table.querySelectorAll('tbody input[type="checkbox"]:checked');
        selectAllCheckbox.checked = bodyCheckboxes.length === checkedBoxes.length;
        selectAllCheckbox.indeterminate = checkedBoxes.length > 0 && checkedBoxes.length < bodyCheckboxes.length;
      }
    }

    // Emit selection change event
    this.table.dispatchEvent(new CustomEvent('selectionChange', {
      detail: { selectedRows: Array.from(this.selectedRows) }
    }));
  }

  addSearchBox() {
    const searchId = `tableSearch_${this.tableId}`;
    
    const searchContainer = document.createElement('div');
    searchContainer.className = 'enterprise-table-search mb-3';
    searchContainer.innerHTML = `
      <div class="input-group">
        <span class="input-group-text">
          <i class="bi bi-search"></i>
        </span>
        <input type="text" class="form-control" placeholder="Search table..." id="${searchId}">
      </div>
    `;

    this.container.parentNode.insertBefore(searchContainer, this.container);

    const searchInput = searchContainer.querySelector(`#${searchId}`);
    searchInput.addEventListener('input', (e) => {
      this.filterTable(e.target.value);
    });
  }

  filterTable(searchTerm) {
    const rows = this.table.querySelectorAll('tbody tr');
    const term = searchTerm.toLowerCase();

    rows.forEach(row => {
      const text = row.textContent.toLowerCase();
      const shouldShow = !term || text.includes(term);
      row.style.display = shouldShow ? '' : 'none';
    });
  }

  addPagination() {
    const pageStartId = `pageStart_${this.tableId}`;
    const pageEndId = `pageEnd_${this.tableId}`;
    const totalRowsId = `totalRows_${this.tableId}`;
    const prevPageId = `prevPage_${this.tableId}`;
    const nextPageId = `nextPage_${this.tableId}`;
    const pageNumbersId = `pageNumbers_${this.tableId}`;
    
    const paginationContainer = document.createElement('div');
    paginationContainer.className = 'enterprise-table-pagination';
    paginationContainer.innerHTML = `
      <div class="pagination-info">
        Showing <span id="${pageStartId}">1</span>-<span id="${pageEndId}">20</span> of <span id="${totalRowsId}">0</span> entries
      </div>
      <div class="pagination-controls">
        <button class="pagination-btn" id="${prevPageId}" disabled>
          <i class="bi bi-chevron-left"></i> Previous
        </button>
        <div id="${pageNumbersId}"></div>
        <button class="pagination-btn" id="${nextPageId}">
          Next <i class="bi bi-chevron-right"></i>
        </button>
      </div>
    `;

    this.container.appendChild(paginationContainer);
    this.paginationIds = { pageStartId, pageEndId, totalRowsId, prevPageId, nextPageId, pageNumbersId };
    this.initializePagination();
  }

  initializePagination() {
    const prevBtn = this.container.querySelector(`#${this.paginationIds.prevPageId}`);
    const nextBtn = this.container.querySelector(`#${this.paginationIds.nextPageId}`);

    prevBtn.addEventListener('click', () => this.goToPage(this.currentPage - 1));
    nextBtn.addEventListener('click', () => this.goToPage(this.currentPage + 1));

    this.updatePagination();
  }

  goToPage(page) {
    const totalRows = this.table.querySelectorAll('tbody tr').length;
    const totalPages = Math.ceil(totalRows / this.options.pageSize);

    if (page < 1 || page > totalPages) return;

    this.currentPage = page;
    this.updatePagination();
    this.showPage(page);
  }

  showPage(page) {
    const rows = this.table.querySelectorAll('tbody tr');
    const startIndex = (page - 1) * this.options.pageSize;
    const endIndex = startIndex + this.options.pageSize;

    rows.forEach((row, index) => {
      row.style.display = (index >= startIndex && index < endIndex) ? '' : 'none';
    });
  }

  updatePagination() {
    if (!this.paginationIds) return;
    
    const totalRows = this.table.querySelectorAll('tbody tr').length;
    const totalPages = Math.ceil(totalRows / this.options.pageSize);
    const startRow = (this.currentPage - 1) * this.options.pageSize + 1;
    const endRow = Math.min(this.currentPage * this.options.pageSize, totalRows);

    // Update info
    this.container.querySelector(`#${this.paginationIds.pageStartId}`).textContent = startRow;
    this.container.querySelector(`#${this.paginationIds.pageEndId}`).textContent = endRow;
    this.container.querySelector(`#${this.paginationIds.totalRowsId}`).textContent = totalRows;

    // Update buttons
    const prevBtn = this.container.querySelector(`#${this.paginationIds.prevPageId}`);
    const nextBtn = this.container.querySelector(`#${this.paginationIds.nextPageId}`);

    prevBtn.disabled = this.currentPage === 1;
    nextBtn.disabled = this.currentPage === totalPages;

    prevBtn.classList.toggle('disabled', this.currentPage === 1);
    nextBtn.classList.toggle('disabled', this.currentPage === totalPages);
  }

  initializeData() {
    // Store original data for sorting/filtering
    const rows = Array.from(this.table.querySelectorAll('tbody tr'));
    this.originalData = rows.map(row => row.cloneNode(true));
  }

  refreshTable() {
    // Refresh table data and reset states
    this.selectedRows.clear();
    this.currentSort = { column: null, direction: null };
    this.currentPage = 1;

    // Clear sort indicators
    this.table.querySelectorAll('th').forEach(th => {
      th.classList.remove('sort-asc', 'sort-desc');
    });

    // Update pagination if enabled
    if (this.options.pagination) {
      this.updatePagination();
      this.showPage(1);
    }
  }

  showLoading() {
    if (this.container.querySelector('.enterprise-table-loading')) return;

    const loadingDiv = document.createElement('div');
    loadingDiv.className = 'enterprise-table-loading';
    loadingDiv.innerHTML = '<div class="spinner"></div>';
    this.container.appendChild(loadingDiv);
  }

  hideLoading() {
    const loadingDiv = this.container.querySelector('.enterprise-table-loading');
    if (loadingDiv) {
      loadingDiv.remove();
    }
  }

  getSelectedRows() {
    return Array.from(this.selectedRows);
  }

  clearSelection() {
    this.selectedRows.clear();
    this.table.querySelectorAll('input[type="checkbox"]').forEach(cb => {
      cb.checked = false;
      cb.indeterminate = false;
    });
    this.table.querySelectorAll('tr.selected').forEach(row => {
      row.classList.remove('selected');
    });
  }

  destroy() {
    // Release IDs from registry
    if (this.paginationIds) {
      Object.values(this.paginationIds).forEach(id => {
        enterpriseIdRegistry.releaseId(id);
      });
    }
    
    const searchId = `tableSearch_${this.tableId}`;
    enterpriseIdRegistry.releaseId(searchId);
    enterpriseIdRegistry.releaseId(this.tableId);
    
    // Clean up event listeners and restore original table
    this.container.replaceWith(this.table);
  }
}

// Auto-initialize tables with enterprise-table class
document.addEventListener('DOMContentLoaded', function() {
  const tables = document.querySelectorAll('.table, table');
  tables.forEach(table => {
    // Skip if already initialized
    if (table.closest('.enterprise-table-container')) return;
    
    // Initialize with default options
    new EnterpriseTable(table, {
      sortable: true,
      selectable: table.querySelector('input[type="checkbox"]') !== null,
      searchable: true,
      pagination: table.querySelectorAll('tbody tr').length > 20
    });
  });
});

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
  module.exports = EnterpriseTable;
}