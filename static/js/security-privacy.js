document.addEventListener('DOMContentLoaded', function() {
  // Initialize toggle switches
  document.querySelectorAll('.toggle-switch').forEach(toggle => {
    toggle.addEventListener('click', function() {
      this.classList.toggle('active');
      updateSecurityLevel();
    });
  });

  // Save settings
  document.getElementById('saveSecuritySettings')?.addEventListener('click', function() {
    saveSecuritySettings();
  });

  // Load initial data
  loadSecurityData();
  initializeRealTimeMonitoring();

  function updateSecurityLevel() {
    const activeToggles = document.querySelectorAll('.toggle-switch.active').length;
    const totalToggles = document.querySelectorAll('.toggle-switch').length;
    const percentage = totalToggles ? (activeToggles / totalToggles) * 100 : 0;
    const levelElement = document.getElementById('securityLevel');
    if (!levelElement) return;
    if (percentage >= 80) {
      levelElement.textContent = 'Security Level: High';
      levelElement.className = 'security-level security-high';
    } else if (percentage >= 50) {
      levelElement.textContent = 'Security Level: Medium';
      levelElement.className = 'security-level security-medium';
    } else {
      levelElement.textContent = 'Security Level: Low';
      levelElement.className = 'security-level security-low';
    }
  }

  async function loadSecurityData() {
    try {
      const response = await fetch('/settings/api/security/');
      const data = await response.json();
      if (data.success) {
        Object.entries(data.settings).forEach(([key, value]) => {
          const toggle = document.querySelector(`[data-setting="${key}"]`);
          if (toggle) toggle.classList.toggle('active', !!value);
          const input = document.getElementById(key);
          if (input) input.value = value;
        });
        updateSecurityLevel();
      }
    } catch (error) {
      console.error('Error loading security data:', error);
    }
  }

  // Real-time monitoring
  let previousMetrics = {};
  let pollingInterval = null;
  let isPolling = false;

  function initializeRealTimeMonitoring() { startPolling(); }

  function updateConnectionStatus(status) {
    const statusElement = document.getElementById('connectionStatus');
    if (!statusElement) return;
    const statusMap = {
      'connected': { text: 'Live', class: 'bg-success' },
      'connecting': { text: 'Connecting...', class: 'bg-warning' },
      'disconnected': { text: 'Offline', class: 'bg-danger' }
    };
    const config = statusMap[status];
    statusElement.textContent = config.text;
    statusElement.className = `badge ${config.class}`;
  }

  function updateMetrics(metrics) {
    updateMetricWithChange('activeUsers', metrics.active_users);
    updateMetricWithChange('failedLogins', metrics.failed_logins);
    updateMetricWithChange('activeSessions', metrics.active_sessions);
    updateMetricWithChange('securityAlerts', metrics.security_alerts);
    previousMetrics = { ...metrics };
  }

  function updateMetricWithChange(elementId, newValue) {
    const element = document.getElementById(elementId);
    const changeElement = document.getElementById(elementId + 'Change');
    const key = elementId.replace(/([A-Z])/g, '_$1').toLowerCase();
    const oldValue = previousMetrics[key] || 0;
    if (element) {
      element.classList.add('updating');
      setTimeout(() => element.classList.remove('updating'), 1000);
      element.textContent = newValue;
    }
    if (changeElement) {
      const change = newValue - oldValue;
      if (change > 0) {
        changeElement.innerHTML = '<i class="fas fa-arrow-up"></i> +' + change;
        changeElement.className = 'metric-change metric-up';
      } else if (change < 0) {
        changeElement.innerHTML = '<i class="fas fa-arrow-down"></i> ' + change;
        changeElement.className = 'metric-change metric-down';
      } else {
        changeElement.innerHTML = '<i class="fas fa-minus"></i> No change';
        changeElement.className = 'metric-change metric-same';
      }
    }
  }

  function updateActivityFeed(activities) {
    const feedElement = document.getElementById('activityFeed');
    if (!feedElement) return;
    if (!activities || activities.length === 0) {
      feedElement.innerHTML = '<div class="text-center p-4 text-muted"><i class="fas fa-info-circle"></i> No recent activities</div>';
      return;
    }
    const html = activities.map((activity, index) => {
      const timeAgo = getTimeAgo(new Date(activity.timestamp));
      const actionIcon = getActionIcon(activity.action);
      const actionColor = getActionColor(activity.action);
      const isNew = index < 3;
      return `
        <div class="activity-item ${isNew ? 'activity-new' : ''}">
          <div class="d-flex align-items-center">
            <div class="me-3"><i class="fas fa-${actionIcon} ${actionColor}"></i></div>
            <div class="flex-grow-1">
              <div class="fw-semibold">${activity.user__username || 'System'}</div>
              <div class="small text-muted">${formatAction(activity.action)}</div>
              <div class="small text-muted">
                <i class="fas fa-globe-americas me-1"></i>${activity.ip_address} • 
                <i class="fas fa-clock me-1"></i>${timeAgo}
              </div>
            </div>
          </div>
        </div>`;
    }).join('');
    feedElement.innerHTML = html;
    setTimeout(() => {
      document.querySelectorAll('.activity-new').forEach(el => el.classList.remove('activity-new'));
    }, 1000);
  }

  function getActionIcon(action) {
    const iconMap = { login: 'sign-in-alt', logout: 'sign-out-alt', failed_login: 'exclamation-triangle', password_change: 'key', account_locked: 'lock', profile_updated: 'user-edit' };
    return iconMap[action] || 'info-circle';
  }
  function getActionColor(action) {
    const colorMap = { login: 'text-success', logout: 'text-info', failed_login: 'text-danger', password_change: 'text-warning', account_locked: 'text-danger', profile_updated: 'text-primary' };
    return colorMap[action] || 'text-muted';
  }
  function formatAction(action) {
    const map = { login: 'Logged in', logout: 'Logged out', failed_login: 'Failed login attempt', password_change: 'Changed password', account_locked: 'Account locked', profile_updated: 'Updated profile' };
    return map[action] || action.replace('_', ' ');
  }
  function getTimeAgo(date) {
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);
    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    const diffHours = Math.floor(diffMins / 60);
    if (diffHours < 24) return `${diffHours}h ago`;
    const diffDays = Math.floor(diffHours / 24);
    return `${diffDays}d ago`;
  }
  function updateLastUpdateTime() {
    const now = new Date();
    const el = document.getElementById('lastUpdate');
    if (el) el.textContent = `Updated ${now.toLocaleTimeString()}`;
  }

  function startPolling() {
    if (isPolling) return;
    isPolling = true;
    updateConnectionStatus('connecting');
    loadMetricsAndActivities();
    pollingInterval = setInterval(loadMetricsAndActivities, 15000);
  }
  function stopPolling() {
    if (pollingInterval) {
      clearInterval(pollingInterval);
      pollingInterval = null;
    }
    isPolling = false;
    updateConnectionStatus('disconnected');
  }
  async function loadMetricsAndActivities() {
    try {
      const [metricsResponse, activitiesResponse] = await Promise.all([
        fetch('/settings/api/security-metrics/'),
        fetch('/settings/api/security-activities/')
      ]);
      const [metricsData, activitiesData] = await Promise.all([metricsResponse.json(), activitiesResponse.json()]);
      if (metricsData.success) {
        updateMetrics(metricsData.metrics);
        updateConnectionStatus('connected');
      }
      if (activitiesData.success) {
        updateActivityFeed(activitiesData.activities);
      }
      updateLastUpdateTime();
    } catch (error) {
      console.error('Polling error:', error);
      updateConnectionStatus('disconnected');
    }
  }

  window.addEventListener('beforeunload', () => { stopPolling(); });
  document.addEventListener('visibilitychange', () => { document.hidden ? stopPolling() : startPolling(); });

  async function saveSecuritySettings() {
    const button = document.getElementById('saveSecuritySettings');
    if (!button) return;
    const originalText = button.innerHTML;
    try {
      button.disabled = true;
      button.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Saving...';
      const settings = {};
      document.querySelectorAll('.toggle-switch').forEach(toggle => {
        const setting = toggle.dataset.setting;
        settings[setting] = toggle.classList.contains('active');
      });
      settings.sessionTimeout = document.getElementById('sessionTimeout')?.value;
      settings.maxLoginAttempts = document.getElementById('maxLoginAttempts')?.value;
      settings.dataRetention = document.getElementById('dataRetention')?.value;
      const formData = new FormData();
      formData.append('settings', JSON.stringify(settings));
      formData.append('csrfmiddlewaretoken', getCSRFToken());
      const response = await fetch('/settings/api/security/update/', { method: 'POST', body: formData });
      const data = await response.json();
      if (data.success) {
        showAlert('Security settings saved successfully!', 'success');
      } else {
        showAlert(data.error || 'Failed to save settings', 'danger');
      }
    } catch (error) {
      console.error('Error saving settings:', error);
      showAlert('Network error occurred', 'danger');
    } finally {
      button.disabled = false;
      button.innerHTML = originalText;
    }
  }

  function getCSRFToken() {
    const cookies = document.cookie.split(';');
    for (let cookie of cookies) {
      const [name, value] = cookie.trim().split('=');
      if (name === 'csrftoken') return value;
    }
    const meta = document.querySelector('meta[name="csrf-token"]');
    return meta ? meta.getAttribute('content') : '';
  }

  function showAlert(message, type) {
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
    alertDiv.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
    alertDiv.innerHTML = `${message}<button type="button" class="btn-close" data-bs-dismiss="alert"></button>`;
    document.body.appendChild(alertDiv);
    setTimeout(() => { if (alertDiv.parentNode) alertDiv.remove(); }, 5000);
  }
});
