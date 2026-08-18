(() => {
  'use strict';

  const page = document.getElementById('retirementEmployeePage');
  if (!page) return;

  const elements = {
    loading: document.getElementById('retirementLoading'),
    status: document.getElementById('retirementStatus'),
    formPanel: document.getElementById('retirementFormPanel'),
    feedback: document.getElementById('retirementFeedback'),
    form: document.getElementById('retirementRequestForm'),
    submit: document.getElementById('submitRetirementButton'),
    cancel: document.getElementById('confirmCancelRetirement'),
  };
  let currentRetirement = null;

  const csrfToken = () => document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';
  const escapeHTML = (value) => String(value ?? '').replace(/[&<>"']/g, (character) => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;',
  })[character]);
  const displayDate = (value) => value ? new Intl.DateTimeFormat(undefined, { dateStyle: 'medium' }).format(new Date(value)) : '—';
  const displayLabel = (value) => String(value || '—').replaceAll('_', ' ').replace(/\b\w/g, (letter) => letter.toUpperCase());

  function showFeedback(message, type = 'info') {
    elements.feedback.innerHTML = `<div class="alert alert-${type} retirement-toast" role="status">${escapeHTML(message)}</div>`;
    elements.feedback.focus?.();
  }

  async function requestJSON(url, options = {}) {
    const response = await fetch(url, { credentials: 'same-origin', ...options });
    let data = {};
    try { data = await response.json(); } catch (_) { data = {}; }
    if (!response.ok || data.success === false) throw new Error(data.error || 'The request could not be completed.');
    return data;
  }

  function renderDetails(retirement) {
    const rows = [
      ['Request date', displayDate(retirement.request_date)],
      ['Effective date', displayDate(retirement.effective_date)],
      ['Reason category', displayLabel(retirement.reason_category)],
      ['Reason', retirement.reason, true],
    ];
    if (retirement.notes) rows.push(['Additional notes', retirement.notes, true]);
    if (retirement.reviewed_by) rows.push(['Reviewed by', retirement.reviewed_by]);
    if (retirement.approval_notes) rows.push(['Approval notes', retirement.approval_notes, true]);
    if (retirement.rejection_reason) rows.push(['Rejection reason', retirement.rejection_reason, true]);
    document.getElementById('retirementDetails').innerHTML = rows.map(([label, value, full]) =>
      `<div class="${full ? 'retirement-facts__full' : ''}"><dt>${escapeHTML(label)}</dt><dd>${escapeHTML(value)}</dd></div>`
    ).join('');
  }

  function renderTimeline(events) {
    const container = document.getElementById('retirementTimeline');
    container.innerHTML = events.length
      ? events.map((event) => `<li><strong>${escapeHTML(event.title || 'Update')}</strong><span>${escapeHTML(event.description || '')}</span><span>${escapeHTML(displayDate(event.date))}</span></li>`).join('')
      : '<li><strong>Request submitted</strong><span>No additional progress events yet.</span></li>';
  }

  function renderAssets(assets) {
    const panel = document.getElementById('retirementAssetsPanel');
    const container = document.getElementById('retirementAssets');
    panel.hidden = assets.length === 0;
    container.innerHTML = assets.map((asset) => `
      <article class="ui-record">
        <div><strong>${escapeHTML(asset.name)}</strong><span class="status-badge status-badge--${escapeHTML(asset.status)}">${escapeHTML(displayLabel(asset.status))}</span></div>
        <p>${escapeHTML(asset.category)} · ${escapeHTML(asset.branch)}</p>
      </article>`
    ).join('');
  }

  function renderStatus(retirement) {
    currentRetirement = retirement;
    elements.loading.hidden = true;
    elements.formPanel.hidden = true;
    elements.status.hidden = false;
    document.getElementById('retirementStatusText').textContent = retirement.status_display || displayLabel(retirement.status);
    document.getElementById('retirementEffectiveDate').textContent = displayDate(retirement.effective_date);
    document.getElementById('retirementAssetCount').textContent = retirement.asset_count ?? 0;
    document.getElementById('retirementAssetsPending').textContent = retirement.assets_pending ?? 0;
    renderDetails(retirement);
    renderTimeline(Array.isArray(retirement.timeline) ? retirement.timeline : []);
    renderAssets(Array.isArray(retirement.assets) ? retirement.assets : []);
    document.getElementById('retirementActionsPanel').hidden = !retirement.can_cancel;
  }

  async function loadStatus() {
    elements.loading.hidden = false;
    elements.status.hidden = true;
    elements.formPanel.hidden = true;
    try {
      const data = await requestJSON(page.dataset.statusUrl);
      if (data.has_request) renderStatus(data.retirement);
      else {
        elements.loading.hidden = true;
        elements.formPanel.hidden = false;
      }
    } catch (error) {
      elements.loading.hidden = true;
      elements.formPanel.hidden = false;
      showFeedback(error.message, 'danger');
    }
  }

  elements.form?.addEventListener('submit', async (event) => {
    event.preventDefault();
    if (!elements.form.reportValidity()) return;
    elements.submit.disabled = true;
    try {
      const result = await requestJSON(page.dataset.submitUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken() },
        body: JSON.stringify({
          effective_date: document.getElementById('effectiveDate').value,
          reason_category: document.getElementById('reasonCategory').value,
          reason: document.getElementById('reason').value.trim(),
          notes: document.getElementById('notes').value.trim(),
        }),
      });
      showFeedback(result.message || 'Retirement request submitted.', 'success');
      await loadStatus();
    } catch (error) {
      showFeedback(error.message, 'danger');
    } finally {
      elements.submit.disabled = false;
    }
  });

  elements.cancel?.addEventListener('click', async () => {
    const reason = document.getElementById('cancelReason');
    if (!reason.reportValidity() || reason.value.trim().length < 10 || !currentRetirement) return;
    elements.cancel.disabled = true;
    try {
      const result = await requestJSON(page.dataset.cancelUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken() },
        body: JSON.stringify({ retirement_id: currentRetirement.id, reason: reason.value.trim() }),
      });
      bootstrap.Modal.getInstance(document.getElementById('cancelRetirementModal'))?.hide();
      showFeedback(result.message || 'Retirement request cancelled.', 'success');
      await loadStatus();
    } catch (error) {
      showFeedback(error.message, 'danger');
    } finally {
      elements.cancel.disabled = false;
    }
  });

  document.getElementById('reason')?.addEventListener('input', (event) => {
    document.getElementById('reasonCharCount').textContent = event.target.value.length;
  });

  document.addEventListener('DOMContentLoaded', loadStatus, { once: true });
})();
