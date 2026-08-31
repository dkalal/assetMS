(() => {
  'use strict';

  document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('approvalDecisionForm');
    const modalElement = document.getElementById('approvalConfirmModal');
    const confirmButton = document.getElementById('approvalConfirmButton');
    const message = document.getElementById('approvalConfirmMessage');
    if (!form || !modalElement || !confirmButton || !window.bootstrap) return;

    const modal = new bootstrap.Modal(modalElement);
    let pendingSubmitter = null;
    let confirmed = false;

    form.addEventListener('submit', (event) => {
      const submitter = event.submitter;
      const actionLabel = submitter?.dataset.confirmAction;
      if (!actionLabel || confirmed) {
        confirmed = false;
        return;
      }

      event.preventDefault();
      pendingSubmitter = submitter;
      message.textContent = actionLabel === 'Reject'
        ? 'Reject this request? Include a clear reason in the decision notes before continuing.'
        : 'Escalate this request to an administrator for further review?';
      confirmButton.className = actionLabel === 'Reject' ? 'btn btn-danger' : 'btn btn-warning';
      confirmButton.textContent = actionLabel;
      modal.show();
    });

    confirmButton.addEventListener('click', () => {
      if (!pendingSubmitter) return;
      confirmed = true;
      modal.hide();
      form.requestSubmit(pendingSubmitter);
    });

    modalElement.addEventListener('hidden.bs.modal', () => {
      pendingSubmitter = null;
    });
  });
})();
