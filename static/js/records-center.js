(function () {
  'use strict';
  document.querySelectorAll('[data-refresh]').forEach((button) => {
    button.addEventListener('click', () => window.location.reload());
  });
  document.querySelectorAll('[data-print]').forEach((button) => {
    button.addEventListener('click', () => window.print());
  });
})();
