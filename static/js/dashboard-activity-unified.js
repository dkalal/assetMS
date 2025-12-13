/**
 * Dashboard Unified Activity Table
 * Handles the unified activity feed with filter tabs
 * World-Class Implementation: Clean, Modular, Performant
 */

(function() {
  'use strict';

  // Activity Filter State
  let currentFilter = 'all';
  let currentPage = 1;
  let totalPages = 1;
  let isLoading = false;

  // Activity Type Mapping
  const ACTIVITY_TYPES = {
    'assets': 'Asset',
    'transfers': 'Transfer',
    'scans': 'Scan',
    'maintenance': 'Maintenance',
    'audit': 'Audit'
  };

  // Activity Type Badge Colors (Blue Theme)
  const TYPE_COLORS = {
    'Asset': { bg: 'rgba(107, 155, 209, 0.1)', color: '#6B9BD1', icon: 'box-seam' },
    'Transfer': { bg: 'rgba(245, 158, 11, 0.1)', color: '#f59e0b', icon: 'arrow-left-right' },
    'Scan': { bg: 'rgba(59, 130, 246, 0.1)', color: '#3b82f6', icon: 'upc-scan' },
    'Maintenance': { bg: 'rgba(239, 68, 68, 0.1)', color: '#ef4444', icon: 'tools' },
    'Audit': { bg: 'rgba(107, 114, 128, 0.1)', color: '#6b7280', icon: 'clipboard-data' }
  };

  /**
   * Initialize the unified activity table
   */
  function initUnifiedActivityTable() {
    setupFilterButtons();
    setupPagination();
    loadActivities();
  }

  /**
   * Setup filter button click handlers
   */
  function setupFilterButtons() {
    const filterButtons = document.querySelectorAll('.activity-filter-btn');
    
    filterButtons.forEach(btn => {
      btn.addEventListener('click', function() {
        // Update active state
        filterButtons.forEach(b => {
          b.classList.remove('active');
          b.setAttribute('aria-selected', 'false');
        });
        this.classList.add('active');
        this.setAttribute('aria-selected', 'true');
        
        // Update filter and reload
        currentFilter = this.dataset.filter;
        currentPage = 1;
        loadActivities();
      });
    });
  }

  /**
   * Setup pagination button handlers
   */
  function setupPagination() {
    const prevBtn = document.getElementById('activity-prev');
    const nextBtn = document.getElementById('activity-next');

    if (prevBtn) {
      prevBtn.addEventListener('click', () => {
        if (currentPage > 1) {
          currentPage--;
          loadActivities();
        }
      });
    }

    if (nextBtn) {
      nextBtn.addEventListener('click', () => {
        if (currentPage < totalPages) {
          currentPage++;
          loadActivities();
        }
      });
    }
  }

  /**
   * Load activities from existing APIs and aggregate them
   * Uses existing backend APIs instead of creating new endpoint
   */
  async function loadActivities() {
    if (isLoading) return;
    isLoading = true;

    const tbody = document.getElementById('activity-table-body');
    const emptyState = document.getElementById('activity-empty-state');
    
    // Show loading state
    showLoadingState(tbody);
    if (emptyState) emptyState.style.display = 'none';

    try {
      // Fetch from all existing APIs in parallel
      const [assetsRes, scansRes, transfersRes, maintenanceRes, auditRes] = await Promise.all([
        fetch(`/recent-added-assets-api/?page=1&page_size=10`),
        fetch(`/recent-scans-api/?page=1&page_size=10`),
        fetch(`/recent-transfers-api/?page=1&page_size=10`),
        fetch(`/recent-maintenance-api/?page=1&page_size=10`),
        fetch(`/full-audit-log-api/?page=1&page_size=10`)
      ]);

      // Parse all responses
      const [assetsData, scansData, transfersData, maintenanceData, auditData] = await Promise.all([
        assetsRes.ok ? assetsRes.json() : { recent_added_assets: [] },
        scansRes.ok ? scansRes.json() : { recent_scans: [] },
        transfersRes.ok ? transfersRes.json() : { recent_transfers: [] },
        maintenanceRes.ok ? maintenanceRes.json() : { recent_maintenance: [] },
        auditRes.ok ? auditRes.json() : { audit_log: [] }
      ]);

      // Aggregate all activities
      const allActivities = [
        ...normalizeActivities(assetsData.recent_added_assets || [], 'assets'),
        ...normalizeActivities(scansData.recent_scans || [], 'scans'),
        ...normalizeActivities(transfersData.recent_transfers || [], 'transfers'),
        ...normalizeActivities(maintenanceData.recent_maintenance || [], 'maintenance'),
        ...normalizeActivities(auditData.audit_log || [], 'audit')
      ];

      // Sort by timestamp (newest first)
      allActivities.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));

      // Filter based on current filter
      const filteredActivities = currentFilter === 'all' 
        ? allActivities 
        : allActivities.filter(a => a.type === currentFilter);

      // Apply pagination
      const startIndex = (currentPage - 1) * 20;
      const endIndex = startIndex + 20;
      const paginatedActivities = filteredActivities.slice(startIndex, endIndex);
      const totalPages = Math.ceil(filteredActivities.length / 20);

      isLoading = false;
      renderActivities(paginatedActivities);
      updatePagination(currentPage, totalPages, filteredActivities.length);

    } catch (error) {
      isLoading = false;
      console.error('Failed to load activities:', error);
      showErrorState(tbody);
    }
  }

  /**
   * Normalize different activity formats into unified format
   */
  function normalizeActivities(activities, type) {
    return activities.map(activity => ({
      type: type,
      user: activity.user || activity.username || activity.performed_by || 'System',
      action: activity.action || activity.activity_type || activity.event_type || 'Updated',
      asset: activity.asset_name || activity.asset || activity.target || activity.description || 'N/A',
      timestamp: activity.timestamp || activity.created_at || activity.date || new Date().toISOString(),
      details: activity.details || activity.description || '',
      id: activity.id || Math.random().toString(36).substr(2, 9)
    }));
  }

  /**
   * Show loading state
   */
  function showLoadingState(tbody) {
    tbody.innerHTML = `
      <tr role="row">
        <td colspan="6" class="text-center py-5">
          <div class="spinner-border text-primary" role="status" style="width: 2rem; height: 2rem;">
            <span class="visually-hidden">Loading...</span>
          </div>
          <p class="text-muted mt-3 mb-0">Loading activities...</p>
        </td>
      </tr>
    `;
  }

  /**
   * Show error state
   */
  function showErrorState(tbody) {
    tbody.innerHTML = `
      <tr role="row">
        <td colspan="6" class="text-center py-5">
          <i class="bi bi-exclamation-triangle text-warning" style="font-size: 2rem;"></i>
          <p class="text-muted mt-3 mb-0">Failed to load activities. Please try again.</p>
          <button class="btn btn-sm btn-primary mt-2" onclick="location.reload()">
            <i class="bi bi-arrow-clockwise me-1"></i>Retry
          </button>
        </td>
      </tr>
    `;
  }

  /**
   * Render activities in the table
   */
  function renderActivities(activities) {
    const tbody = document.getElementById('activity-table-body');
    const emptyState = document.getElementById('activity-empty-state');

    if (!activities || activities.length === 0) {
      tbody.innerHTML = '';
      if (emptyState) emptyState.style.display = 'block';
      return;
    }

    if (emptyState) emptyState.style.display = 'none';

    const rows = activities.map(activity => {
      const typeLabel = ACTIVITY_TYPES[activity.type] || 'Activity';
      const typeConfig = TYPE_COLORS[typeLabel] || TYPE_COLORS['Audit'];
      
      // Format timestamp
      const timestamp = activity.timestamp ? new Date(activity.timestamp).toLocaleString() : '-';
      
      return `
        <tr role="row" style="transition: background-color 0.15s ease;">
          <td>
            <span class="activity-badge" style="
              display: inline-flex;
              align-items: center;
              padding: 0.25rem 0.75rem;
              border-radius: 12px;
              font-size: 0.75rem;
              font-weight: 600;
              background: ${typeConfig.bg};
              color: ${typeConfig.color};
            ">
              <i class="bi bi-${typeConfig.icon} me-1"></i>${escapeHtml(typeLabel)}
            </span>
          </td>
          <td style="font-weight: 500; color: var(--text-primary);">
            ${escapeHtml(activity.user)}
          </td>
          <td style="color: var(--text-secondary);">
            ${escapeHtml(activity.action)}
          </td>
          <td style="font-weight: 500; color: var(--text-primary);">
            ${escapeHtml(activity.asset)}
          </td>
          <td style="color: var(--text-muted); font-size: 0.875rem;">
            ${escapeHtml(timestamp)}
          </td>
          <td style="color: var(--text-muted); font-size: 0.875rem;">
            ${escapeHtml(activity.details || '-')}
          </td>
        </tr>
      `;
    }).join('');

    tbody.innerHTML = rows;
  }

  /**
   * Update pagination controls
   */
  function updatePagination(page, numPages, total) {
    currentPage = page;
    totalPages = numPages;

    const prevBtn = document.getElementById('activity-prev');
    const nextBtn = document.getElementById('activity-next');
    const pageInfo = document.getElementById('activity-page-info');

    if (prevBtn) {
      prevBtn.disabled = page <= 1;
    }

    if (nextBtn) {
      nextBtn.disabled = page >= numPages;
    }

    if (pageInfo) {
      if (numPages > 0) {
        pageInfo.textContent = `Page ${page} of ${numPages} (${total} total)`;
      } else {
        pageInfo.textContent = 'No results';
      }
    }
  }

  /**
   * Escape HTML to prevent XSS
   */
  function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = String(text);
    return div.innerHTML;
  }

  /**
   * Auto-refresh activities every 30 seconds
   */
  function startAutoRefresh() {
    setInterval(() => {
      if (!isLoading && document.visibilityState === 'visible') {
        loadActivities();
      }
    }, 30000); // 30 seconds
  }

  // Initialize when DOM is ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
      initUnifiedActivityTable();
      startAutoRefresh();
    });
  } else {
    initUnifiedActivityTable();
    startAutoRefresh();
  }

})();
