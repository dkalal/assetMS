(() => {
  'use strict';

  const root = document.querySelector('[data-asset-detail]');
  if (!root) return;

  const csrfToken = () => {
    const formToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value;
    if (formToken) return formToken;
    const cookie = document.cookie.split('; ').find((item) => item.startsWith('csrftoken='));
    return cookie ? decodeURIComponent(cookie.split('=').slice(1).join('=')) : '';
  };

  const announce = (message, type = 'info') => {
    if (typeof window.showToast === 'function') {
      window.showToast(message, type);
      return;
    }
    let region = document.querySelector('.app-feedback');
    if (!region) {
      region = document.createElement('div');
      region.className = 'app-feedback';
      region.setAttribute('aria-live', 'polite');
      document.querySelector('.app-content')?.prepend(region);
    }
    const alert = document.createElement('div');
    alert.className = `alert alert-${type === 'error' ? 'danger' : type}`;
    alert.setAttribute('role', 'status');
    alert.textContent = message;
    region?.append(alert);
  };

  const readResponse = async (response) => {
    const data = await response.json().catch(() => ({}));
    if (response.ok && data.success !== false) return data;
    if (data.error) throw new Error(data.error);
    if (data.errors) {
      const first = Object.values(data.errors).flat()[0];
      throw new Error(first || 'The request could not be completed.');
    }
    throw new Error('The request could not be completed.');
  };

  document.querySelector('[data-print-page]')?.addEventListener('click', () => window.print());
  document.querySelectorAll('[data-copy-value]').forEach((button) => {
    button.addEventListener('click', async () => {
      try {
        await navigator.clipboard.writeText(button.dataset.copyValue || '');
        announce('Asset reference copied.', 'success');
      } catch {
        announce('Unable to copy the asset reference.', 'warning');
      }
    });
  });

  const transferForm = document.getElementById('transferAssetForm');
  const branchSelect = document.getElementById('transferBranchFilter');
  const userSelect = document.getElementById('transferToUser');
  const userStatus = document.getElementById('transferUserStatus');
  const transferError = document.getElementById('transferError');

  const setTransferError = (message = '') => {
    if (!transferError) return;
    transferError.textContent = message;
    transferError.classList.toggle('d-none', !message);
  };

  branchSelect?.addEventListener('change', async () => {
    const branchId = branchSelect.value;
    userSelect.disabled = true;
    userSelect.replaceChildren(new Option(branchId ? 'Loading recipients…' : 'Select a branch first', ''));
    if (userStatus) userStatus.textContent = '';
    if (!branchId) return;

    try {
      const url = new URL(root.dataset.usersUrl, window.location.origin);
      url.searchParams.set('branch_id', branchId);
      url.searchParams.set('exclude_user_id', root.dataset.userId);
      const data = await readResponse(await fetch(url, { credentials: 'same-origin' }));
      userSelect.replaceChildren(new Option('Select recipient', ''));
      (data.users || []).forEach((user) => {
        userSelect.add(new Option(`${user.full_name} (${user.role})`, user.id));
      });
      userSelect.disabled = !data.users?.length;
      if (userStatus) userStatus.textContent = data.users?.length ? `${data.users.length} recipients available.` : 'No eligible recipients were found in this branch.';
    } catch (error) {
      userSelect.replaceChildren(new Option('Unable to load recipients', ''));
      setTransferError(error.message);
    }
  });

  transferForm?.addEventListener('submit', async (event) => {
    event.preventDefault();
    setTransferError();
    if (!transferForm.reportValidity()) return;
    const reason = document.getElementById('transferReason').value.trim();
    if (reason.length < 10) {
      setTransferError('Provide a business reason of at least 10 characters.');
      return;
    }
    const recipient = userSelect.selectedOptions[0]?.textContent || 'the selected recipient';
    if (!window.confirm(`Initiate this transfer to ${recipient}?`)) return;

    const submit = document.getElementById('executeTransferBtn');
    submit.disabled = true;
    submit.setAttribute('aria-busy', 'true');
    try {
      await readResponse(await fetch(root.dataset.transferUrl, {
        method: 'POST',
        credentials: 'same-origin',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken() },
        body: JSON.stringify({
          asset_id: Number(root.dataset.assetId),
          asset_uuid: root.dataset.assetUuid,
          to_user_id: Number(userSelect.value),
          to_branch_id: Number(branchSelect.value),
          initiator_comment: reason,
          context: { priority: document.getElementById('transferPriority').value },
        }),
      }));
      announce('Transfer initiated. The approval workflow is now in progress.', 'success');
      bootstrap.Modal.getInstance(document.getElementById('transferAssetModal'))?.hide();
      window.setTimeout(() => window.location.reload(), 600);
    } catch (error) {
      setTransferError(error.message);
      submit.disabled = false;
      submit.removeAttribute('aria-busy');
    }
  });

  const maintenanceForm = document.getElementById('maintenanceRequestForm');
  const maintenanceError = document.getElementById('maintenanceRequestError');
  maintenanceForm?.addEventListener('submit', async (event) => {
    event.preventDefault();
    maintenanceError?.classList.add('d-none');
    if (!maintenanceForm.reportValidity()) return;
    const reason = document.getElementById('maintenanceReason').value.trim();
    const submit = document.getElementById('submitMaintenanceRequest');
    submit.disabled = true;
    submit.setAttribute('aria-busy', 'true');
    try {
      const data = await readResponse(await fetch(root.dataset.maintenanceRequestUrl, {
        method: 'POST',
        credentials: 'same-origin',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken() },
        body: JSON.stringify({ reason }),
      }));
      announce(data.message || 'Maintenance request submitted.', 'success');
      bootstrap.Modal.getInstance(document.getElementById('maintenanceRequestModal'))?.hide();
      document.getElementById('requestMaintenanceBtn')?.setAttribute('disabled', 'disabled');
    } catch (error) {
      if (maintenanceError) {
        maintenanceError.textContent = error.message;
        maintenanceError.classList.remove('d-none');
      }
      submit.disabled = false;
      submit.removeAttribute('aria-busy');
    }
  });
})();
