(() => {
  'use strict';

  const page = document.getElementById('retirementApprovalPage');
  if (!page) return;

  const state = { pending: [], approved: [], selected: null };
  const elements = {
    feedback: document.getElementById('retirementApprovalFeedback'),
    pendingLoading: document.getElementById('pendingRetirementLoading'),
    pendingList: document.getElementById('pendingRetirementList'),
    pendingEmpty: document.getElementById('pendingRetirementEmpty'),
    approvedLoading: document.getElementById('approvedRetirementLoading'),
    approvedList: document.getElementById('approvedRetirementList'),
    approvedEmpty: document.getElementById('approvedRetirementEmpty'),
    search: document.getElementById('retirementSearch'),
    sort: document.getElementById('retirementSort'),
  };

  const csrfToken = () => document.querySelector('[name=csrfmiddlewaretoken]')?.value
    || document.cookie.split('; ').find((row) => row.startsWith('csrftoken='))?.split('=')[1]
    || '';
  const escapeHTML = (value) => String(value ?? '').replace(/[&<>"']/g, (character) => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;',
  })[character]);
  const safeToken = (value) => String(value || '').replace(/[^a-z0-9_-]/gi, '').toLowerCase();
  const displayDate = (value) => value ? new Intl.DateTimeFormat(undefined, { dateStyle: 'medium' }).format(new Date(value)) : '—';
  const actionURL = (template, id) => template.replace(page.dataset.urlPlaceholder, encodeURIComponent(id));

  function showFeedback(message, type = 'info') {
    elements.feedback.innerHTML = `<div class="alert alert-${type} retirement-toast" role="status">${escapeHTML(message)}</div>`;
  }

  async function requestJSON(url, options = {}) {
    const response = await fetch(url, { credentials: 'same-origin', ...options });
    let data = {};
    try { data = await response.json(); } catch (_) { data = {}; }
    if (!response.ok || data.success === false) throw new Error(data.error || 'The request could not be completed.');
    return data;
  }

  function filtered(records) {
    const term = (elements.search?.value || '').trim().toLowerCase();
    const sort = elements.sort?.value || 'oldest';
    const result = records.filter((item) => {
      if (!term) return true;
      return [item.user?.name, item.user?.email, item.user?.branch].some((value) => String(value || '').toLowerCase().includes(term));
    });
    result.sort((a, b) => {
      const first = sort === 'effective_date' ? a.effective_date : a.request_date;
      const second = sort === 'effective_date' ? b.effective_date : b.request_date;
      return (sort === 'newest' ? -1 : 1) * (new Date(first) - new Date(second));
    });
    return result;
  }

  function pendingCard(item) {
    return `
      <article class="retirement-request">
        <div class="min-w-0">
          <div class="d-flex flex-wrap align-items-center gap-2">
            <h3>${escapeHTML(item.user?.name || item.user?.email || 'Employee')}</h3>
            <span class="status-badge status-badge--${safeToken(item.status)}">${escapeHTML(item.status_display || item.status)}</span>
          </div>
          <p>${escapeHTML(item.reason_category_display || item.reason_category)} · ${escapeHTML(item.reason || '')}</p>
          <div class="retirement-request__meta">
            <span>${escapeHTML(item.user?.email)}</span>
            <span>${escapeHTML(item.user?.branch)}</span>
            <span>Effective ${escapeHTML(displayDate(item.effective_date))}</span>
            <span>${escapeHTML(item.asset_count ?? 0)} assigned assets</span>
          </div>
        </div>
        <div class="retirement-request__actions">
          <button type="button" class="btn btn-sm btn-success" data-retirement-action="approve" data-id="${escapeHTML(item.id)}" data-name="${escapeHTML(item.user?.name || item.user?.email)}">Approve</button>
          <button type="button" class="btn btn-sm btn-outline-danger" data-retirement-action="reject" data-id="${escapeHTML(item.id)}" data-name="${escapeHTML(item.user?.name || item.user?.email)}">Reject</button>
        </div>
      </article>`;
  }

  function approvedCard(item) {
    const canStart = page.dataset.canProcess === 'true' && item.status === 'approved';
    return `
      <article class="retirement-request retirement-request--processing">
        <div class="min-w-0">
          <div class="d-flex flex-wrap align-items-center gap-2">
            <h3>${escapeHTML(item.user?.name || item.user?.email || 'Employee')}</h3>
            <span class="status-badge status-badge--${safeToken(item.status)}">${escapeHTML(item.status_display || item.status)}</span>
          </div>
          <p>${escapeHTML(item.reason_category_display || item.reason_category)} · Effective ${escapeHTML(displayDate(item.effective_date))}</p>
          <div class="retirement-request__meta">
            <span>${escapeHTML(item.user?.email)}</span>
            <span>${escapeHTML(item.asset_count ?? 0)} assigned assets</span>
            <span>Approved by ${escapeHTML(item.approved_by || '—')}</span>
          </div>
        </div>
        <div class="retirement-request__actions">
          ${canStart ? `<button type="button" class="btn btn-sm btn-primary" data-retirement-action="start" data-id="${escapeHTML(item.id)}" data-name="${escapeHTML(item.user?.name || item.user?.email)}">Start processing</button>` : ''}
        </div>
      </article>`;
  }

  function renderLists() {
    const pending = filtered(state.pending);
    elements.pendingLoading.hidden = true;
    elements.pendingList.hidden = pending.length === 0;
    elements.pendingEmpty.hidden = pending.length !== 0;
    elements.pendingList.innerHTML = pending.map(pendingCard).join('');
    document.getElementById('pendingRetirementRange').textContent = `${pending.length} of ${state.pending.length} requests shown`;

    if (elements.approvedList) {
      const approved = filtered(state.approved);
      elements.approvedLoading.hidden = true;
      elements.approvedList.hidden = approved.length === 0;
      elements.approvedEmpty.hidden = approved.length !== 0;
      elements.approvedList.innerHTML = approved.map(approvedCard).join('');
    }
  }

  async function loadQueue() {
    elements.pendingLoading.hidden = false;
    if (elements.approvedLoading) elements.approvedLoading.hidden = false;
    try {
      const jobs = [
        requestJSON(page.dataset.statsUrl),
        requestJSON(page.dataset.pendingUrl),
      ];
      if (page.dataset.canProcess === 'true') jobs.push(requestJSON(page.dataset.approvedUrl));
      const [stats, pending, approved] = await Promise.all(jobs);
      document.getElementById('pendingRetirementCount').textContent = stats.pending_approvals ?? 0;
      document.getElementById('approvedRetirementCount').textContent = stats.approved_requests ?? 0;
      document.getElementById('progressRetirementCount').textContent = stats.in_progress ?? 0;
      document.getElementById('upcomingRetirementCount').textContent = stats.upcoming_effective_dates_30d ?? 0;
      state.pending = Array.isArray(pending.requests) ? pending.requests : [];
      state.approved = Array.isArray(approved?.requests) ? approved.requests : [];
      renderLists();
    } catch (error) {
      elements.pendingLoading.hidden = true;
      if (elements.approvedLoading) elements.approvedLoading.hidden = true;
      showFeedback(error.message, 'danger');
    }
  }

  function openActionModal(button) {
    const action = button.dataset.retirementAction;
    state.selected = { id: button.dataset.id, name: button.dataset.name, action };
    const modalIds = { approve: 'approveRetirementModal', reject: 'rejectRetirementModal', start: 'startRetirementModal' };
    const summaryIds = { approve: 'approveRetirementSummary', reject: 'rejectRetirementSummary', start: 'startRetirementSummary' };
    document.getElementById(summaryIds[action]).textContent = `${action === 'start' ? 'Start processing' : action === 'approve' ? 'Approve' : 'Reject'} the retirement request for ${state.selected.name}?`;
    bootstrap.Modal.getOrCreateInstance(document.getElementById(modalIds[action])).show();
  }

  async function performAction(action, button) {
    if (!state.selected || state.selected.action !== action) return;
    const config = {
      approve: { template: page.dataset.approveUrlTemplate, body: { comments: document.getElementById('approvalComments').value.trim() }, modal: 'approveRetirementModal', success: 'Retirement request approved.' },
      reject: { template: page.dataset.rejectUrlTemplate, body: { rejection_reason: document.getElementById('rejectionReason').value.trim() }, modal: 'rejectRetirementModal', success: 'Retirement request rejected.' },
      start: { template: page.dataset.startUrlTemplate, body: {}, modal: 'startRetirementModal', success: 'Retirement processing started.' },
    }[action];
    if (action === 'reject' && config.body.rejection_reason.length < 10) {
      document.getElementById('rejectionReason').reportValidity();
      showFeedback('Provide a rejection reason of at least 10 characters.', 'warning');
      return;
    }
    button.disabled = true;
    try {
      const result = await requestJSON(actionURL(config.template, state.selected.id), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': decodeURIComponent(csrfToken()) },
        body: JSON.stringify(config.body),
      });
      bootstrap.Modal.getInstance(document.getElementById(config.modal))?.hide();
      showFeedback(result.message || config.success, 'success');
      state.selected = null;
      await loadQueue();
    } catch (error) {
      showFeedback(error.message, 'danger');
    } finally {
      button.disabled = false;
    }
  }

  document.addEventListener('click', (event) => {
    const actionButton = event.target.closest('[data-retirement-action]');
    if (actionButton) openActionModal(actionButton);
  });
  elements.search?.addEventListener('input', renderLists);
  elements.sort?.addEventListener('change', renderLists);
  document.getElementById('refreshRetirementQueue')?.addEventListener('click', loadQueue);
  document.getElementById('confirmApproveRetirement')?.addEventListener('click', (event) => performAction('approve', event.currentTarget));
  document.getElementById('confirmRejectRetirement')?.addEventListener('click', (event) => performAction('reject', event.currentTarget));
  document.getElementById('confirmStartRetirement')?.addEventListener('click', (event) => performAction('start', event.currentTarget));
  document.addEventListener('DOMContentLoaded', loadQueue, { once: true });
})();
