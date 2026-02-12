// Asset List Page JS (moved from inline script in asset_list.html for CSP compliance)

document.addEventListener('DOMContentLoaded', function() {
  // Custom modal open/close logic
  const openExportModalBtn = document.getElementById('openExportModal');
  const exportModalCustom = document.getElementById('exportModalCustom');
  const closeExportModalBtn = document.getElementById('closeExportModal');
  if (openExportModalBtn && exportModalCustom && closeExportModalBtn) {
    openExportModalBtn.addEventListener('click', () => {
      exportModalCustom.classList.add('active');
      exportModalCustom.focus();
    });
    closeExportModalBtn.addEventListener('click', () => {
      exportModalCustom.classList.remove('active');
    });
    exportModalCustom.addEventListener('click', (e) => {
      if (e.target === exportModalCustom) {
        exportModalCustom.classList.remove('active');
      }
    });
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && exportModalCustom.classList.contains('active')) {
        exportModalCustom.classList.remove('active');
      }
    });
  }

  // Asset selection logic
  const selectAllCheckbox = document.getElementById('select-all-assets');
  const assetCheckboxes = document.querySelectorAll('.asset-checkbox');
  if (selectAllCheckbox && assetCheckboxes.length) {
    selectAllCheckbox.addEventListener('change', function() {
      assetCheckboxes.forEach(cb => { cb.checked = this.checked; });
      updateExportSummary();
    });
    assetCheckboxes.forEach(cb => {
      cb.addEventListener('change', updateExportSummary);
    });
  }
  function getSelectedAssetIds() {
    return Array.from(assetCheckboxes).filter(cb => cb.checked).map(cb => cb.value);
  }
  function updateExportSummary() {
    const selected = getSelectedAssetIds();
    const summary = document.getElementById('export-summary');
    const hiddenInput = document.getElementById('selected-asset-ids');
    if (summary && hiddenInput) {
      if (selected.length > 0) {
        summary.textContent = `You are exporting ${selected.length} selected asset${selected.length > 1 ? 's' : ''}.`;
        hiddenInput.value = selected.join(',');
      } else {
        summary.textContent = 'You are exporting all filtered assets.';
        hiddenInput.value = '';
      }
    }
  }

  // Dynamically populate export columns
  function getColumns() {
    let columns = [
      {key: 'ID', label: 'ID'},
      {key: 'Category', label: 'Category'},
      {key: 'Status', label: 'Status'},
      {key: 'Assigned To', label: 'Assigned To'},
      {key: 'Created', label: 'Created'},
      {key: 'Updated', label: 'Updated'}
    ];
    // Dynamic fields: pass via data attribute or window variable if needed
    if (window.assetDynamicFields && Array.isArray(window.assetDynamicFields)) {
      window.assetDynamicFields.forEach(function(field) {
        columns.push({key: field.key, label: field.label});
      });
    }
    return columns;
  }
  function renderExportColumns() {
    const columns = getColumns();
    const container = document.getElementById('export-columns-list');
    if (!container) return;
    container.innerHTML = '';
    columns.forEach(col => {
      const div = document.createElement('div');
      div.className = 'col-md-4 mb-1';
      div.innerHTML = `<div class='form-check'>
        <input class='form-check-input export-col' type='checkbox' name='columns' value='${col.key}' id='col_${col.key}' checked>
        <label class='form-check-label' for='col_${col.key}'>${col.label}</label>
      </div>`;
      container.appendChild(div);
    });
    const controls = document.createElement('div');
    controls.className = 'col-12 mb-2';
    controls.innerHTML = `<button type='button' class='btn btn-sm btn-link' id='selectAllExportColsBtn'>Select All</button> |
      <button type='button' class='btn btn-sm btn-link' id='deselectAllExportColsBtn'>Deselect All</button>`;
    container.prepend(controls);
    document.getElementById('selectAllExportColsBtn').addEventListener('click', function() {
      selectAllExportCols(true);
    });
    document.getElementById('deselectAllExportColsBtn').addEventListener('click', function() {
      selectAllExportCols(false);
    });
  }
  function selectAllExportCols(val) {
    document.querySelectorAll('.export-col').forEach(cb => { cb.checked = val; });
  }
  // On DOM ready, render columns and update summary
  renderExportColumns();
  updateExportSummary();
  // Ensure only checked columns are submitted
  const exportForm = document.getElementById('export-form');
  if (exportForm) {
    exportForm.addEventListener('submit', function(e) {
      document.querySelectorAll('.export-col').forEach(cb => {
        if (!cb.checked) cb.disabled = true;
      });
    });
  }

  // Loading overlay for table during navigation/filtering (UI-only)
  const overlay = document.getElementById('asset-table-loading-overlay');
  const filterForm = document.querySelector('form[method="get"]');
  function showOverlay() {
    if (!overlay) return;
    overlay.classList.remove('d-none');
    overlay.setAttribute('aria-hidden', 'false');
  }
  // Show overlay on filter submit
  if (filterForm) {
    filterForm.addEventListener('submit', function() {
      showOverlay();
    });
  }
  // Show overlay on pagination/tab clicks
  document.addEventListener('click', function(e) {
    try {
      const a = e.target.closest('a');
      if (!a) return;
      const href = a.getAttribute('href') || '';
      // Trigger overlay on known navigations within list
      if (href.includes('page=') || a.closest('.section-tabs') || a.closest('.pagination')) {
        showOverlay();
      }
    } catch (_) { /* no-op */ }
  }, true);

  // CSRF helper
  function getCSRFToken() {
    return document.querySelector('input[name="csrfmiddlewaretoken"]')?.value || '';
  }

  // Single asset delete
  function handleSingleDelete(assetId, assetName) {
    if (!confirm(`Are you sure you want to delete asset '${assetName}'? This action cannot be undone.`)) return;
    fetch(`/assets/${assetId}/delete/`, {
      method: 'POST',
      headers: {
        'X-CSRFToken': getCSRFToken(),
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
      body: JSON.stringify({}),
    })
    .then(res => res.json())
    .then(data => {
      // WORLD-CLASS: Deletion is deprecated; redirect to disposal workflow to preserve audit trail.
      if (data && (data.action === 'redirect' || data.deprecated === true) && data.redirect_url) {
        window.location.href = data.redirect_url;
        return;
      }

      if (data.success) {
        document.querySelector(`button.delete-asset[data-asset-id="${assetId}"]`).closest('tr').remove();
        alert(data.message);
      } else {
        alert(data.error || 'Delete failed.');
      }
    })
    .catch(() => alert('Delete failed due to network or server error.'));
  }

  // Bulk asset delete - WORLD-CLASS: Show disposal info instead
  function handleBulkDelete() {
    const ids = getSelectedAssetIds();
    if (!ids.length) return alert('No assets selected.');
    
    // Show world-class informative modal
    showDisposalInfoModal(ids.length);
  }
  
  function showDisposalInfoModal(count) {
    // Check if modal already exists
    let modal = document.getElementById('disposalInfoModal');
    if (modal) {
      // Show existing modal
      modal.style.display = 'block';
      return;
    }
    
    // Create modal
    modal = document.createElement('div');
    modal.id = 'disposalInfoModal';
    modal.className = 'modal fade show';
    modal.style.display = 'block';
    modal.style.background = 'rgba(0,0,0,0.5)';
    modal.innerHTML = `
      <div class="modal-dialog modal-dialog-centered">
        <div class="modal-content">
          <div class="modal-header bg-warning bg-opacity-10">
            <h5 class="modal-title">
              <i class="bi bi-info-circle me-2 text-warning"></i>
              Bulk Deletion Not Available
            </h5>
            <button type="button" class="btn-close" onclick="this.closest('.modal').style.display='none'"></button>
          </div>
          <div class="modal-body">
            <div class="alert alert-info mb-3">
              <i class="bi bi-shield-check me-2"></i>
              <strong>Audit Compliance Requirement</strong>
            </div>
            <p><strong>To maintain audit compliance</strong>, assets must be disposed through the proper disposal workflow.</p>
            <p class="mb-2">This ensures:</p>
            <ul class="mb-3">
              <li>Complete audit trail (who, when, why)</li>
              <li>Approval process (if required by your organization)</li>
              <li>SOC2/GDPR compliance</li>
              <li>Proper documentation for asset disposal</li>
            </ul>
            <p class="mb-0">
              <strong>Next steps:</strong> Please dispose of assets individually through their detail pages, 
              or contact your administrator to set up a bulk disposal workflow.
            </p>
          </div>
          <div class="modal-footer">
            <button type="button" class="btn btn-secondary" onclick="this.closest('.modal').style.display='none'">
              <i class="bi bi-x me-1"></i>Close
            </button>
          </div>
        </div>
      </div>
    `;
    
    document.body.appendChild(modal);
    
    // Close on backdrop click
    modal.addEventListener('click', (e) => {
      if (e.target === modal) {
        modal.style.display = 'none';
      }
    });
  }

  // Attach event listeners

  // Single delete buttons
  document.querySelectorAll('button.delete-asset').forEach(btn => {
    btn.addEventListener('click', function() {
      const assetId = this.getAttribute('data-asset-id');
      const assetName = this.getAttribute('data-asset-name');
      handleSingleDelete(assetId, assetName);
    });
  });

  // Bulk delete button
  const bulkDeleteBtn = document.getElementById('deleteSelectedAssets');
  if (bulkDeleteBtn) {
    bulkDeleteBtn.addEventListener('click', handleBulkDelete);
  }
});