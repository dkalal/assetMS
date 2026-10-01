(function () {
  'use strict';

  const breakpoint = window.matchMedia('(max-width: 991.98px)');
  const body = document.body;
  const sidebar = document.getElementById('app-sidebar');
  const toggle = document.getElementById('mobile-sidebar-toggle');
  const backdrop = document.getElementById('sidebar-backdrop');
  let returnFocus = null;

  if (!sidebar || !toggle || !backdrop) return;

  const focusableSelector = 'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex=\'-1\'])';

  function isOpen() {
    return body.classList.contains('sidebar-open');
  }

  function syncState() {
    const mobile = breakpoint.matches;
    toggle.classList.toggle('d-lg-none', !mobile);
    toggle.setAttribute('aria-expanded', String(mobile && isOpen()));
    sidebar.setAttribute('aria-hidden', String(mobile && !isOpen()));
    backdrop.setAttribute('tabindex', mobile && isOpen() ? '0' : '-1');
  }

  function openSidebar() {
    if (!breakpoint.matches) return;
    returnFocus = document.activeElement;
    body.classList.add('sidebar-open');
    syncState();
    const first = sidebar.querySelector(focusableSelector);
    if (first) first.focus();
  }

  function closeSidebar(restoreFocus) {
    body.classList.remove('sidebar-open');
    syncState();
    if (restoreFocus && returnFocus instanceof HTMLElement) returnFocus.focus();
  }

  toggle.addEventListener('click', function () {
    if (isOpen()) closeSidebar(true);
    else openSidebar();
  });
  backdrop.addEventListener('click', function () { closeSidebar(true); });
  sidebar.addEventListener('click', function (event) {
    if (breakpoint.matches && event.target.closest('a[href]')) closeSidebar(false);
  });

  document.addEventListener('keydown', function (event) {
    if (!breakpoint.matches || !isOpen()) return;
    if (event.key === 'Escape') {
      event.preventDefault();
      closeSidebar(true);
      return;
    }
    if (event.key !== 'Tab') return;
    const focusable = Array.from(sidebar.querySelectorAll(focusableSelector));
    if (!focusable.length) return;
    const first = focusable[0];
    const last = focusable[focusable.length - 1];
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  });

  breakpoint.addEventListener('change', function () {
    closeSidebar(false);
    syncState();
  });

  document.querySelectorAll('img[data-fallback]').forEach(function (image) {
    image.addEventListener('error', function () {
      if (image.dataset.fallback && image.src !== image.dataset.fallback) image.src = image.dataset.fallback;
    }, { once: true });
  });

  const branchSelect = document.getElementById('branch-select-topbar');
  if (branchSelect && branchSelect.form) {
    branchSelect.addEventListener('change', function () { branchSelect.form.requestSubmit(); });
  }

  syncState();
}());
