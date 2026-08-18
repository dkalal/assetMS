(() => {
  'use strict';

  const root = document.querySelector('[data-maintenance-center]');
  if (!root) return;

  const searchInput = document.getElementById('maintenanceSearch');
  const clearSearch = document.getElementById('clearMaintenanceSearch');
  const searchStatus = document.getElementById('maintenanceSearchStatus');
  const noResults = document.getElementById('maintenanceNoResults');

  const applySearch = () => {
    const query = searchInput.value.trim().toLocaleLowerCase();
    const records = [...root.querySelectorAll('[data-maintenance-record]')];
    let visible = 0;
    records.forEach((record) => {
      const matches = !query || (record.dataset.search || '').toLocaleLowerCase().includes(query);
      record.hidden = !matches;
      if (matches) visible += 1;
    });
    if (searchStatus) searchStatus.textContent = query ? `${visible} matching items shown.` : '';
    noResults?.classList.toggle('d-none', visible > 0 || !query);
  };

  searchInput?.addEventListener('input', applySearch);
  clearSearch?.addEventListener('click', () => {
    searchInput.value = '';
    applySearch();
    searchInput.focus();
  });

  ['maintenanceStartModal', 'maintenanceCompleteModal', 'maintenanceCancelModal'].forEach((id) => {
    const modal = document.getElementById(id);
    modal?.addEventListener('show.bs.modal', (event) => {
      const trigger = event.relatedTarget;
      const form = modal.querySelector('form');
      if (!trigger || !form) return;
      form.action = trigger.dataset.actionUrl || '';
      modal.querySelectorAll('[data-modal-asset]').forEach((element) => { element.textContent = trigger.dataset.asset || 'Asset'; });
      modal.querySelectorAll('[data-modal-branch]').forEach((element) => { element.textContent = trigger.dataset.branch || 'Not assigned'; });
      modal.querySelectorAll('[data-modal-scheduled]').forEach((element) => { element.textContent = trigger.dataset.scheduledFor || 'Not recorded'; });
      form.reset();
      form.classList.remove('was-validated');
    });
  });

  root.ownerDocument.querySelectorAll('.needs-validation').forEach((form) => {
    form.addEventListener('submit', (event) => {
      if (!form.checkValidity()) {
        event.preventDefault();
        event.stopPropagation();
      }
      form.classList.add('was-validated');
    });
  });
})();
