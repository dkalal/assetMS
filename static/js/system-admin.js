(() => {
  'use strict';
  const root = document.querySelector('[data-system-admin]');
  if (!root) return;
  root.querySelectorAll('[data-confirm]').forEach((control) => {
    control.addEventListener('click', (event) => {
      if (!window.confirm(control.dataset.confirm)) event.preventDefault();
    });
  });
})();
