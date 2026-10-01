(function () {
  'use strict';
  const page = document.querySelector('.reports-center');
  const modalElement = document.getElementById('generateReportModal');
  const form = document.getElementById('generateReportForm');
  if (!page) return;

  document.querySelectorAll('[data-refresh]').forEach((button) => {
    button.addEventListener('click', () => window.location.reload());
  });
  if (!modalElement || !form) return;

  const type = document.getElementById('reportType');
  const personGroup = document.getElementById('individualUserGroup');
  const person = document.getElementById('individualUserSelect');
  const includeInactive = document.getElementById('includeInactiveUsers');
  const branch = document.getElementById('reportBranchSelect');
  const previewButton = document.getElementById('previewReportBtn');
  const previewPanel = document.getElementById('reportPreviewPanel');
  let downloading = false;

  function updateType() {
    const individual = type.value === 'individual';
    personGroup.hidden = !individual;
    person.required = individual;
    if (!individual) person.value = '';
  }

  function filterPeople() {
    const branchId = branch?.value || '';
    Array.from(person.options).forEach((option, index) => {
      if (index === 0) return;
      const active = option.dataset.active === 'true';
      const branches = (option.dataset.branchIds || '').split(',').filter(Boolean);
      const visible = (includeInactive.checked || active) && (!branchId || branches.includes(branchId));
      option.hidden = !visible;
      option.disabled = !visible;
    });
    if (person.selectedOptions[0]?.disabled) person.value = '';
  }

  function validateDates() {
    const from = form.elements.date_from;
    const to = form.elements.date_to;
    to.setCustomValidity(from.value && to.value && from.value > to.value ? 'End date must be on or after the start date.' : '');
  }

  function renderPreview(payload, isError) {
    previewPanel.classList.remove('d-none');
    previewPanel.classList.toggle('records-preview--error', isError);
    previewPanel.replaceChildren();
    if (isError) {
      previewPanel.textContent = payload;
      return;
    }
    const metrics = payload.metrics || {};
    const heading = document.createElement('strong');
    heading.textContent = 'Preview ready';
    const details = document.createElement('p');
    details.className = 'mb-0 mt-1';
    details.textContent = (metrics.total_rows || 0) + ' rows · ' + (metrics.total_columns || 0) +
      ' columns · quality ' + (metrics.data_quality_score || 0) + '%';
    previewPanel.append(heading, details);
  }

  async function preview() {
    validateDates();
    if (!form.checkValidity()) {
      form.reportValidity();
      return;
    }
    previewButton.disabled = true;
    try {
      const response = await fetch(page.dataset.previewUrl, {
        method: 'POST',
        credentials: 'same-origin',
        headers: {'Content-Type': 'application/json', 'X-CSRFToken': form.elements.csrfmiddlewaretoken.value},
        body: JSON.stringify({
          report_type: type.value,
          format: form.elements.format.value,
          status: form.elements.status.value,
          branch_id: form.elements.branch_id?.value || '',
          date_from: form.elements.date_from.value,
          date_to: form.elements.date_to.value,
          user_id: form.elements.user_id.value,
          preview_limit: 5
        })
      });
      const payload = await response.json();
      renderPreview(response.ok ? payload : (payload.error || 'Preview failed.'), !response.ok);
    } catch (error) {
      renderPreview('Preview could not be loaded. Try again.', true);
    } finally {
      previewButton.disabled = false;
    }
  }

  document.querySelectorAll('[data-report-type]').forEach((button) => {
    button.addEventListener('click', () => {
      type.value = button.dataset.reportType;
      updateType();
      bootstrap.Modal.getOrCreateInstance(modalElement).show();
    });
  });
  type.addEventListener('change', updateType);
  includeInactive.addEventListener('change', filterPeople);
  branch?.addEventListener('change', filterPeople);
  previewButton.addEventListener('click', preview);
  form.addEventListener('change', validateDates);
  form.addEventListener('submit', () => { downloading = true; });
  document.getElementById('downloadFrame')?.addEventListener('load', () => {
    if (downloading) window.setTimeout(() => window.location.reload(), 600);
  });
  updateType();
  filterPeople();
})();
