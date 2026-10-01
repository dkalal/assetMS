(function () {
  'use strict';

  const filterForm = document.getElementById('asset-filter-form');
  const recordPanel = document.querySelector('.record-panel');
  const checkboxes = Array.from(document.querySelectorAll('.asset-checkbox'));
  const selectAll = document.getElementById('select-all-assets');
  const toolbar = document.getElementById('asset-selection-toolbar');
  const count = document.getElementById('asset-selection-count');
  const clear = document.getElementById('clear-asset-selection');

  document.querySelectorAll('[data-remove-filter]').forEach(function (button) {
    button.addEventListener('click', function () {
      const url = new URL(window.location.href);
      url.searchParams.delete(button.dataset.removeFilter);
      url.searchParams.delete('page');
      window.location.assign(url.toString());
    });
  });

  if (filterForm) {
    filterForm.addEventListener('submit', function () {
      if (recordPanel) {
        recordPanel.setAttribute('aria-busy', 'true');
        recordPanel.classList.add('is-loading');
      }
    });
  }

  function selectedIds() {
    return new Set(checkboxes.filter(function (item) { return item.checked; }).map(function (item) { return item.value; }));
  }

  function updateSelection() {
    const selected = selectedIds();
    if (toolbar && count) {
      toolbar.hidden = selected.size === 0;
      count.textContent = selected.size + (selected.size === 1 ? ' selected' : ' selected');
    }
    if (selectAll) {
      const allIds = new Set(checkboxes.map(function (item) { return item.value; }));
      selectAll.checked = allIds.size > 0 && selected.size === allIds.size;
      selectAll.indeterminate = selected.size > 0 && selected.size < allIds.size;
    }
  }

  checkboxes.forEach(function (checkbox) {
    checkbox.addEventListener('change', function () {
      checkboxes.forEach(function (peer) {
        if (peer.dataset.assetId === checkbox.dataset.assetId) peer.checked = checkbox.checked;
      });
      updateSelection();
    });
  });

  if (selectAll) {
    selectAll.addEventListener('change', function () {
      checkboxes.forEach(function (checkbox) { checkbox.checked = selectAll.checked; });
      updateSelection();
    });
  }

  if (clear) {
    clear.addEventListener('click', function () {
      checkboxes.forEach(function (checkbox) { checkbox.checked = false; });
      updateSelection();
      if (selectAll) selectAll.focus();
    });
  }

  const pageSize = document.getElementById('page-size');
  if (pageSize && pageSize.form) {
    pageSize.addEventListener('change', function () { pageSize.form.requestSubmit(); });
  }

  updateSelection();
}());
