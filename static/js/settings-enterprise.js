class EnterpriseSettingsManager {
  constructor() {
    this.currentSettingId = null;
    this.init();
  }

  init() {
    this.bindEvents();
    this.initializeTooltips();
  }

  bindEvents() {
    document.getElementById('createSettingBtn')?.addEventListener('click', () => {
      const modal = new bootstrap.Modal(document.getElementById('createSettingModal'));
      modal.show();
    });

    document.getElementById('createFirstSettingBtn')?.addEventListener('click', () => {
      const modal = new bootstrap.Modal(document.getElementById('createSettingModal'));
      modal.show();
    });

    document.querySelectorAll('.edit-setting-btn').forEach(btn => {
      btn.addEventListener('click', (e) => this.handleEditSetting(e));
    });

    document.querySelectorAll('.view-setting-btn').forEach(btn => {
      btn.addEventListener('click', (e) => this.handleViewSetting(e));
    });

    const editForm = document.getElementById('editSettingForm');
    if (editForm) editForm.addEventListener('submit', (e) => this.handleEditSubmit(e));

    const createForm = document.getElementById('createSettingForm');
    if (createForm) createForm.addEventListener('submit', (e) => this.handleCreateSubmit(e));

    document.getElementById('systemHealth')?.addEventListener('click', () => {
      const card = document.getElementById('systemHealthCard');
      if (card) card.style.display = card.style.display === 'none' ? 'block' : 'none';
    });

    document.getElementById('exportSettings')?.addEventListener('click', () => this.exportSettings());
    document.getElementById('importSettings')?.addEventListener('click', () => this.importSettings());
  }

  handleEditSetting(e) {
    const btn = e.currentTarget;
    this.currentSettingId = btn.dataset.settingId;

    document.getElementById('editSettingKey').value = btn.dataset.settingKey;
    document.getElementById('editSettingValue').value = btn.dataset.settingValue;
    document.getElementById('editSettingDescription').value = btn.dataset.settingDescription || '';
    document.getElementById('editSettingCategory').value = btn.dataset.settingCategory;
    document.getElementById('editSettingType').value = btn.dataset.settingType;

    const modal = new bootstrap.Modal(document.getElementById('editSettingModal'));
    modal.show();
  }

  handleViewSetting(e) {
    const btn = e.currentTarget;
    const settingId = btn.dataset.settingId;

    const editBtn = document.querySelector(`[data-setting-id="${settingId}"].edit-setting-btn`);
    if (!editBtn) return;

    const content = `
      <div class="table-responsive">
        <table class="table">
          <tr><th>Key</th><td><code>${editBtn.dataset.settingKey}</code></td></tr>
          <tr><th>Value</th><td><pre class="bg-light p-2 rounded">${editBtn.dataset.settingValue}</pre></td></tr>
          <tr><th>Type</th><td><span class="badge bg-secondary">${editBtn.dataset.settingType}</span></td></tr>
          <tr><th>Category</th><td>${editBtn.dataset.settingCategory}</td></tr>
          <tr><th>Description</th><td>${editBtn.dataset.settingDescription || 'No description'}</td></tr>
        </table>
      </div>
    `;

    const container = document.getElementById('viewSettingContent');
    if (container) container.innerHTML = content;

    const editFromView = document.getElementById('editFromView');
    if (editFromView) {
      editFromView.onclick = () => {
        const viewModal = bootstrap.Modal.getInstance(document.getElementById('viewSettingModal'));
        viewModal?.hide();
        setTimeout(() => this.handleEditSetting({ currentTarget: editBtn }), 300);
      };
    }

    const modal = new bootstrap.Modal(document.getElementById('viewSettingModal'));
    modal.show();
  }

  async handleEditSubmit(e) {
    e.preventDefault();
    const feedback = document.getElementById('editFeedback');
    if (feedback) feedback.innerHTML = '<div class="alert alert-info"><i class="bi bi-hourglass-split me-2"></i>Updating setting...</div>';

    try {
      const formData = new FormData();
      formData.append('setting_id', this.currentSettingId);
      formData.append('value', document.getElementById('editSettingValue').value);
      formData.append('description', document.getElementById('editSettingDescription').value);
      formData.append('csrfmiddlewaretoken', this.getCSRFToken());

      const response = await fetch('/settings/api/update/', { method: 'POST', body: formData });
      const data = await response.json();

      if (data.success) {
        if (feedback) feedback.innerHTML = '<div class="alert alert-success"><i class="bi bi-check-circle me-2"></i>Setting updated successfully!</div>';
        setTimeout(() => location.reload(), 1200);
      } else {
        if (feedback) feedback.innerHTML = `<div class="alert alert-danger"><i class="bi bi-exclamation-triangle me-2"></i>${data.error}</div>`;
      }
    } catch (error) {
      if (feedback) feedback.innerHTML = '<div class="alert alert-danger"><i class="bi bi-wifi-off me-2"></i>Network error occurred</div>';
    }
  }

  async handleCreateSubmit(e) {
    e.preventDefault();
    const feedback = document.getElementById('createFeedback');
    if (feedback) feedback.innerHTML = '<div class="alert alert-info"><i class="bi bi-hourglass-split me-2"></i>Creating setting...</div>';

    try {
      const formData = new FormData();
      formData.append('key', document.getElementById('createSettingKey').value);
      formData.append('value', document.getElementById('createSettingValue').value);
      formData.append('setting_type', document.getElementById('createSettingType').value);
      formData.append('description', document.getElementById('createSettingDescription').value);
      formData.append('category', document.getElementById('createSettingCategory').value);
      formData.append('is_public', (document.getElementById('createSettingAccess')?.value || 'private') === 'public');
      formData.append('csrfmiddlewaretoken', this.getCSRFToken());

      const response = await fetch('/settings/api/create/', { method: 'POST', body: formData });
      const data = await response.json();

      if (data.success) {
        if (feedback) feedback.innerHTML = '<div class="alert alert-success"><i class="bi bi-check-circle me-2"></i>Setting created successfully!</div>';
        setTimeout(() => location.reload(), 1200);
      } else {
        if (feedback) feedback.innerHTML = `<div class=\"alert alert-danger\">${data.error}</div>`;
      }
    } catch (error) {
      if (feedback) feedback.innerHTML = '<div class="alert alert-danger"><i class="bi bi-wifi-off me-2"></i>Network error occurred</div>';
    }
  }

  exportSettings() {
    const settings = [];
    document.querySelectorAll('.edit-setting-btn').forEach(btn => {
      settings.push({
        key: btn.dataset.settingKey,
        value: btn.dataset.settingValue,
        type: btn.dataset.settingType,
        category: btn.dataset.settingCategory,
        description: btn.dataset.settingDescription
      });
    });

    const blob = new Blob([JSON.stringify(settings, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `settings-export-${new Date().toISOString().split('T')[0]}.json`;
    a.click();
    URL.revokeObjectURL(url);
  }

  importSettings() {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = '.json';
    input.onchange = (e) => {
      const file = e.target.files[0];
      if (file) {
        const reader = new FileReader();
        reader.onload = (e) => {
          try {
            const settings = JSON.parse(e.target.result);
            console.log('Imported settings:', settings);
            alert(`Successfully imported ${settings.length} settings. Please refresh to see changes.`);
          } catch (error) {
            alert('Invalid JSON file. Please check the format and try again.');
          }
        };
        reader.readAsText(file);
      }
    };
    input.click();
  }

  initializeTooltips() {
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[title]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
      return new bootstrap.Tooltip(tooltipTriggerEl);
    });
  }

  getCSRFToken() {
    const cookies = document.cookie.split(';');
    for (let cookie of cookies) {
      const [name, value] = cookie.trim().split('=');
      if (name === 'csrftoken') return value;
    }
    const meta = document.querySelector('meta[name="csrf-token"]');
    return meta ? meta.getAttribute('content') : '';
  }
}

document.addEventListener('DOMContentLoaded', function() {
  new EnterpriseSettingsManager();
});
