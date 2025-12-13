(function(){
  document.addEventListener('DOMContentLoaded', function() {
    const editModal = document.getElementById('editSettingModal');
    const createModal = document.getElementById('createSettingModal');
    let currentSettingId = null;

    // Edit open
    document.querySelectorAll('.edit-setting-btn').forEach(btn => {
      btn.addEventListener('click', function() {
        currentSettingId = this.dataset.settingId;
        document.getElementById('editSettingKey').value = this.dataset.settingKey;
        document.getElementById('editSettingValue').value = this.dataset.settingValue;
        document.getElementById('editSettingDescription').value = this.dataset.settingDescription || '';
        if (document.getElementById('editSettingCategory')) {
          document.getElementById('editSettingCategory').value = this.dataset.settingCategory || '';
        }
        if (document.getElementById('editSettingType')) {
          document.getElementById('editSettingType').value = this.dataset.settingType || '';
        }
        // Fallback class-based modal toggle for minimal variant
        if (editModal) editModal.classList.add('active');
      });
    });

    // Create open
    document.getElementById('createSettingBtn')?.addEventListener('click', () => createModal?.classList.add('active'));
    document.getElementById('createFirstSettingBtn')?.addEventListener('click', () => createModal?.classList.add('active'));

    // Close handlers
    document.getElementById('closeEditModal')?.addEventListener('click', () => editModal?.classList.remove('active'));
    document.getElementById('closeCreateModal')?.addEventListener('click', () => createModal?.classList.remove('active'));
    document.getElementById('cancelEdit')?.addEventListener('click', () => editModal?.classList.remove('active'));
    document.getElementById('cancelCreate')?.addEventListener('click', () => createModal?.classList.remove('active'));

    // Submit edit
    document.getElementById('editSettingForm')?.addEventListener('submit', async function(e) {
      e.preventDefault();
      const feedback = document.getElementById('editFeedback');
      if (feedback) feedback.innerHTML = '<div class="alert alert-info">Updating setting...</div>';
      try {
        const formData = new FormData();
        formData.append('setting_id', currentSettingId);
        formData.append('value', document.getElementById('editSettingValue').value);
        formData.append('description', document.getElementById('editSettingDescription').value);
        formData.append('csrfmiddlewaretoken', document.querySelector('[name=csrfmiddlewaretoken]').value);
        const response = await fetch('/settings/api/update/', { method: 'POST', body: formData });
        const data = await response.json();
        if (data.success) {
          if (feedback) feedback.innerHTML = '<div class="alert alert-success">Setting updated successfully!</div>';
          setTimeout(() => location.reload(), 1000);
        } else {
          if (feedback) feedback.innerHTML = `<div class="alert alert-danger">${data.error}</div>`;
        }
      } catch (err) {
        if (feedback) feedback.innerHTML = '<div class="alert alert-danger">Network error occurred</div>';
      }
    });

    // Submit create
    document.getElementById('createSettingForm')?.addEventListener('submit', async function(e) {
      e.preventDefault();
      const feedback = document.getElementById('createFeedback');
      if (feedback) feedback.innerHTML = '<div class="alert alert-info">Creating setting...</div>';
      try {
        const formData = new FormData();
        formData.append('key', document.getElementById('createSettingKey').value);
        formData.append('value', document.getElementById('createSettingValue').value);
        formData.append('setting_type', document.getElementById('createSettingType').value);
        formData.append('description', document.getElementById('createSettingDescription').value);
        formData.append('category', document.getElementById('createSettingCategory').value);
        formData.append('is_public', document.getElementById('createSettingPublic')?.checked ? 'on' : '');
        formData.append('csrfmiddlewaretoken', document.querySelector('[name=csrfmiddlewaretoken]').value);
        const response = await fetch('/settings/api/create/', { method: 'POST', body: formData });
        const data = await response.json();
        if (data.success) {
          if (feedback) feedback.innerHTML = '<div class="alert alert-success">Setting created successfully!</div>';
          setTimeout(() => location.reload(), 1000);
        } else {
          if (feedback) feedback.innerHTML = `<div class=\"alert alert-danger\">${data.error}</div>`;
        }
      } catch (err) {
        if (feedback) feedback.innerHTML = '<div class="alert alert-danger">Network error occurred</div>';
      }
    });
  });
})();
