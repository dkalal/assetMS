(function () {
  'use strict';

  const POLL_INTERVAL_MS = 30000;
  const ALERT_LIMIT = 10;
  const MODAL_LIMIT = 50;

  function getCSRFToken() {
    if (typeof window.getCSRFToken === 'function') {
      return window.getCSRFToken();
    }
    return (
      document.querySelector('[name=csrfmiddlewaretoken]')?.value ||
      document.cookie.split('; ').find((row) => row.startsWith('csrftoken='))?.split('=')[1] ||
      ''
    );
  }

  function isoToRelative(isoValue) {
    if (!isoValue) {
      return '';
    }
    try {
      const date = new Date(isoValue);
      const now = new Date();
      const diffMs = now - date;
      const diffMinutes = Math.round(diffMs / 60000);
      if (diffMinutes < 1) {
        return 'Just now';
      }
      if (diffMinutes < 60) {
        return `${diffMinutes} min${diffMinutes === 1 ? '' : 's'} ago`;
      }
      const diffHours = Math.round(diffMinutes / 60);
      if (diffHours < 24) {
        return `${diffHours} hour${diffHours === 1 ? '' : 's'} ago`;
      }
      const diffDays = Math.round(diffHours / 24);
      return `${diffDays} day${diffDays === 1 ? '' : 's'} ago`;
    } catch (err) {
      return '';
    }
  }

  class TransferAlertCenter {
    constructor() {
      this.root = document.getElementById('transferAlertsList');
      this.badge = document.getElementById('transferAlertsBadge');
      this.markAllBtn = document.getElementById('transferAlertsMarkAllBtn');
      this.manageBtn = document.getElementById('transferAlertsManageBtn');
      this.modalBody = document.getElementById('transferAlertsModalBody');
      this.modalInstance = null;
      this.activeAlertIds = [];
      this.alerts = []; // Store alerts for access in decision handlers

      const userMeta = document.querySelector('[data-user-role]');
      if (!userMeta || !this.root || !this.badge) {
        return;
      }

      this.userRole = (userMeta.dataset.userRole || 'user').toLowerCase();
      this.userId = parseInt(userMeta.dataset.userId || '0', 10) || 0;

      if (window.bootstrap && document.getElementById('transferAlertsModal')) {
        this.modalInstance = new window.bootstrap.Modal(document.getElementById('transferAlertsModal'));
      }

      this.bindEvents();
      this.refreshAlerts();
      this.startPolling();
    }

    bindEvents() {
      if (this.markAllBtn) {
        this.markAllBtn.addEventListener('click', () => {
          if (!this.activeAlertIds.length) {
            return;
          }
          this.markAlerts(this.activeAlertIds, 'mark_read');
        });
      }

      if (this.manageBtn && this.modalInstance) {
        this.manageBtn.addEventListener('click', () => {
          this.loadModalAlerts();
          this.modalInstance.show();
        });
      }

      const dropdown = document.getElementById('transferAlertsToggle');
      if (dropdown) {
        dropdown.addEventListener('show.bs.dropdown', () => {
          this.refreshAlerts();
        });
      }
    }

    startPolling() {
      setInterval(() => {
        this.refreshAlerts();
      }, POLL_INTERVAL_MS);
    }

    refreshAlerts() {
      this.fetchAlerts({ limit: ALERT_LIMIT, includeRead: false })
        .then((alerts) => {
          this.alerts = alerts; // Store alerts for decision handlers
          this.activeAlertIds = alerts.map((alert) => alert.id);
          this.renderAlerts(alerts, this.root, { compact: true });
          this.updateBadge(alerts.length);
        })
        .catch((err) => {
          console.error('Failed to load transfer alerts', err);
          this.renderError(this.root, 'Unable to load transfer alerts.');
        });
    }

    loadModalAlerts() {
      if (!this.modalBody) {
        return;
      }
      this.renderLoading(this.modalBody);
      this.fetchAlerts({ limit: MODAL_LIMIT, includeRead: true })
        .then((alerts) => {
          this.renderAlerts(alerts, this.modalBody, { compact: false });
        })
        .catch(() => {
          this.renderError(this.modalBody, 'Unable to load transfer alerts.');
        });
    }

    fetchAlerts({ limit, includeRead }) {
      const params = new URLSearchParams({ limit: String(limit || ALERT_LIMIT) });
      if (includeRead) {
        params.set('include_read', '1');
      }
      return fetch(`/assets/api/transfers/alerts/?${params.toString()}`, {
        headers: {
          'Accept': 'application/json',
          'Cache-Control': 'no-cache',
        },
      })
        .then((response) => {
          if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
          }
          return response.json();
        })
        .then((payload) => {
          if (!payload.success) {
            throw new Error(payload.error || 'Unknown error');
          }
          return payload.alerts || [];
        });
    }

    updateBadge(count) {
      if (!this.badge) {
        return;
      }
      if (count > 0) {
        this.badge.textContent = String(count);
        this.badge.classList.remove('d-none');
        this.markAllBtn?.removeAttribute('disabled');
      } else {
        this.badge.classList.add('d-none');
        this.markAllBtn?.setAttribute('disabled', 'disabled');
      }
    }

    renderLoading(target) {
      if (!target) {
        return;
      }
      target.innerHTML = '<div class="px-3 py-2 text-muted">Loading transfer alerts...</div>';
    }

    renderError(target, message) {
      if (!target) {
        return;
      }
      target.innerHTML = `<div class="px-3 py-2 text-danger">${message}</div>`;
    }

    renderAlerts(alerts, target, { compact }) {
      if (!target) {
        return;
      }

      if (!alerts.length) {
        if (compact) {
          target.innerHTML = '<div class="px-3 py-2 text-muted">No pending transfer alerts.</div>';
        } else {
          target.innerHTML = '<div class="p-3 text-muted">No transfer alerts available.</div>';
        }
        return;
      }

      const list = document.createElement(compact ? 'div' : 'ul');
      if (compact) {
        list.className = 'list-group list-group-flush small';
      } else {
        list.className = 'list-group list-group-flush';
      }

      alerts.forEach((alert) => {
        const item = document.createElement(compact ? 'div' : 'li');
        item.className = 'list-group-item';
        item.dataset.alertId = alert.id; // Add data attribute for easy removal
        if (!compact) {
          item.classList.add('py-3');
        }

        const header = document.createElement('div');
        header.className = 'd-flex align-items-start justify-content-between gap-2';

        const messageWrap = document.createElement('div');
        const title = document.createElement('div');
        title.className = 'fw-semibold';
        title.textContent = alert.message || 'Transfer notification';
        messageWrap.appendChild(title);

        const meta = document.createElement('div');
        meta.className = 'text-muted small';
        meta.textContent = isoToRelative(alert.created_at);
        messageWrap.appendChild(meta);

        const ctxDetails = this.renderContextDetails(alert.context || {});
        if (ctxDetails) {
          messageWrap.appendChild(ctxDetails);
        }

        header.appendChild(messageWrap);

        const actionContainer = this.renderActionButtons(alert);
        if (actionContainer) {
          header.appendChild(actionContainer);
        }

        item.appendChild(header);

        if (!alert.is_read) {
          item.classList.add('bg-light-subtle');
        }

        list.appendChild(item);
      });

      target.innerHTML = '';
      target.appendChild(list);
    }

    renderContextDetails(context) {
      if (!context || typeof context !== 'object') {
        return null;
      }
      const fragment = document.createElement('div');
      fragment.className = 'text-muted small mt-1';

      const parts = [];
      if (context.asset_id) {
        parts.push(`Asset #${context.asset_id}`);
      }
      if (context.asset_uuid) {
        parts.push(`UUID ${context.asset_uuid.slice(0, 8)}…`);
      }
      if (context.state) {
        const label = context.state.replace(/_/g, ' ');
        parts.push(`State: ${label}`);
      }
      if (context.initiator_comment) {
        parts.push(`Initiator note: ${context.initiator_comment}`);
      }
      if (context.receiver_comment) {
        parts.push(`Receiver note: ${context.receiver_comment}`);
      }
      if (context.admin_comment) {
        parts.push(`Admin note: ${context.admin_comment}`);
      }

      if (!parts.length) {
        return null;
      }

      fragment.textContent = parts.join(' • ');
      return fragment;
    }

    renderActionButtons(alert) {
      const context = alert.context || {};
      const state = (context.state || '').toLowerCase();
      const transferId = context.transfer_id;
      if (!transferId) {
        return null;
      }

      const actions = document.createElement('div');
      actions.className = 'btn-group btn-group-sm';

      const isReceiver = this.userId && Number(context.to_user_id) === this.userId;
      const canAdminReview = ['admin', 'manager'].includes(this.userRole);

      if (state === 'pending_receiver' && isReceiver) {
        const approveBtn = this.createActionButton('Approve', 'btn-success', () => {
          this.handleDecision('receiver', transferId, 'approved');
        });
        const rejectBtn = this.createActionButton('Reject', 'btn-danger', () => {
          this.handleDecision('receiver', transferId, 'rejected');
        });
        actions.appendChild(approveBtn);
        actions.appendChild(rejectBtn);
      } else if (state === 'awaiting_admin' && canAdminReview) {
        const approveBtn = this.createActionButton('Approve', 'btn-success', () => {
          this.handleDecision('admin', transferId, 'approved');
        });
        const rejectBtn = this.createActionButton('Reject', 'btn-danger', () => {
          this.handleDecision('admin', transferId, 'rejected');
        });
        actions.appendChild(approveBtn);
        actions.appendChild(rejectBtn);
      } else {
        return null;
      }

      return actions.children.length ? actions : null;
    }

    createActionButton(label, btnClass, handler) {
      const btn = document.createElement('button');
      btn.type = 'button';
      btn.className = `btn ${btnClass}`;
      btn.textContent = label;
      btn.dataset.originalText = label;
      btn.addEventListener('click', (e) => {
        // Disable button immediately to prevent double-clicks
        btn.disabled = true;
        btn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>Processing...';
        
        // Call handler and re-enable on error
        Promise.resolve(handler(e))
          .catch(() => {
            btn.disabled = false;
            btn.textContent = btn.dataset.originalText;
          });
      });
      return btn;
    }

    handleDecision(actor, transferId, decision) {
      const commentPrompt = decision === 'rejected' ? 'Optional comment for rejection:' : 'Optional comment:';
      let comment = '';
      try {
        comment = window.prompt(commentPrompt, '') || '';
      } catch (err) {
        comment = '';
      }

      // User cancelled the prompt
      if (comment === null) {
        return Promise.reject(new Error('Cancelled'));
      }

      const payload = {
        transfer_id: transferId,
        decision,
      };
      if (comment) {
        payload.comment = comment;
      }

      const endpoint = actor === 'receiver'
        ? '/assets/api/transfers/receiver-decision/'
        : '/assets/api/transfers/admin-review/';

      return fetch(endpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': getCSRFToken(),
          'Accept': 'application/json',
        },
        body: JSON.stringify(payload),
      })
        .then((res) => res.json().then((data) => ({ res, data })))
        .then(({ res, data }) => {
          if (!res.ok || !data.success) {
            // Extract error message from response
            let errorMsg = data.error || `HTTP ${res.status}`;
            
            // Handle array of errors (Django validation errors)
            if (Array.isArray(errorMsg)) {
              errorMsg = errorMsg.join(', ');
            }
            
            // User-friendly error messages
            if (errorMsg.includes('not awaiting receiver action')) {
              errorMsg = 'This transfer has already been processed. Please refresh the page.';
            } else if (errorMsg.includes('not awaiting admin review')) {
              errorMsg = 'This transfer has already been reviewed. Please refresh the page.';
            } else if (errorMsg.includes('Only the designated recipient')) {
              errorMsg = 'You are not authorized to approve this transfer.';
            }
            
            throw new Error(errorMsg);
          }
          
          // Immediately hide the alert items from UI
          this.hideTransferAlertItems(transferId);
          
          // Mark the alert(s) related to this transfer as read
          this.markTransferAlerts(transferId);
          
          // Refresh alerts to get updated data
          this.refreshAlerts();
          
          if (window.showToast) {
            const actionText = decision === 'approved' ? 'approved' : 'rejected';
            window.showToast(`Transfer ${actionText} successfully!`, 'success');
          }
          
          if (this.modalInstance) {
            this.loadModalAlerts();
          }
          
          return data;
        })
        .catch((err) => {
          console.error('Failed to submit transfer decision', err);
          
          // Don't show toast for cancelled prompts
          if (err.message !== 'Cancelled' && window.showToast) {
            window.showToast(err.message || 'Unable to process decision.', 'danger');
          }
          
          throw err; // Re-throw to allow button re-enabling
        });
    }

    hideTransferAlertItems(transferId) {
      // Immediately hide alert items from DOM for instant UI feedback
      if (!this.alerts || !this.alerts.length) {
        return;
      }
      
      const relatedAlertIds = this.alerts
        .filter(alert => {
          const context = alert.context || {};
          return context.transfer_id === transferId || 
                 context.asset_transfer_id === transferId ||
                 String(context.transfer_id) === String(transferId);
        })
        .map(alert => alert.id);
      
      // Remove items from both dropdown and modal
      relatedAlertIds.forEach(alertId => {
        // Remove from dropdown
        const dropdownItem = this.root?.querySelector(`[data-alert-id="${alertId}"]`);
        if (dropdownItem) {
          dropdownItem.style.transition = 'opacity 0.3s ease';
          dropdownItem.style.opacity = '0';
          setTimeout(() => dropdownItem.remove(), 300);
        }
        
        // Remove from modal
        const modalItem = this.modalBody?.querySelector(`[data-alert-id="${alertId}"]`);
        if (modalItem) {
          modalItem.style.transition = 'opacity 0.3s ease';
          modalItem.style.opacity = '0';
          setTimeout(() => modalItem.remove(), 300);
        }
      });
      
      // Update badge immediately
      const remainingCount = this.alerts.length - relatedAlertIds.length;
      this.updateBadge(Math.max(0, remainingCount));
    }

    markTransferAlerts(transferId) {
      // Find all alerts related to this transfer and mark them as read
      if (!this.alerts || !this.alerts.length) {
        return;
      }
      
      const relatedAlertIds = this.alerts
        .filter(alert => {
          const context = alert.context || {};
          return context.transfer_id === transferId || 
                 context.asset_transfer_id === transferId ||
                 String(context.transfer_id) === String(transferId);
        })
        .map(alert => alert.id);
      
      if (relatedAlertIds.length > 0) {
        this.markAlerts(relatedAlertIds, 'mark_read');
      }
    }

    markAlerts(ids, action) {
      if (!ids || !ids.length) {
        return;
      }
      fetch('/assets/api/transfers/alerts/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': getCSRFToken(),
          'Accept': 'application/json',
        },
        body: JSON.stringify({ alert_ids: ids, action }),
      })
        .then((res) => res.json().then((data) => ({ res, data })))
        .then(({ res, data }) => {
          if (!res.ok || !data.success) {
            throw new Error(data.error || `HTTP ${res.status}`);
          }
          this.refreshAlerts();
          if (this.modalInstance) {
            this.loadModalAlerts();
          }
        })
        .catch((err) => {
          console.error('Failed to mark alerts', err);
          if (window.showToast) {
            window.showToast('Unable to update alerts.', 'danger');
          }
        });
    }
  }

  document.addEventListener('DOMContentLoaded', () => {
    new TransferAlertCenter();
  });
})();
