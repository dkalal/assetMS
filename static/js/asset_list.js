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
}); 