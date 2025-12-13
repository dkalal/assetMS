// Global search enhancements: debounce, clear button, scope-aware behavior
(function() {
  function debounce(fn, delay) {
    let t; return function(...args) {
      clearTimeout(t); t = setTimeout(() => fn.apply(this, args), delay);
    };
  }

  document.addEventListener('DOMContentLoaded', function() {
    const form = document.querySelector('form[role="search"][aria-label="Asset search"]');
    const input = document.getElementById('global-asset-search');
    const clearBtn = document.querySelector('.search-clear');
    if (!form || !input) return;

    const onAssetsPage = window.location.pathname.startsWith('/assets/');

    function setClearVisibility() {
      if (!clearBtn) return;
      if (input.value && input.value.trim().length > 0) {
        clearBtn.classList.remove('d-none');
      } else {
        clearBtn.classList.add('d-none');
      }
    }

    // Debounced submit only on assets pages (scope-aware)
    const debouncedSubmit = debounce(function() {
      if (onAssetsPage) {
        // Reset page param if present
        const pageHidden = form.querySelector('input[name="page"]');
        if (pageHidden) pageHidden.remove();
        form.requestSubmit ? form.requestSubmit() : form.submit();
      }
    }, 300);

    input.addEventListener('input', function() {
      setClearVisibility();
      debouncedSubmit();
    });

    if (clearBtn) {
      clearBtn.addEventListener('click', function() {
        input.value = '';
        setClearVisibility();
        if (onAssetsPage) {
          // Ensure search param cleared and submit
          // Remove any existing search param hidden inputs created by server iteration
          // Not strictly necessary; submitting with empty value clears it.
          form.requestSubmit ? form.requestSubmit() : form.submit();
        }
      });
    }

    // Initialize clear button visibility on load
    setClearVisibility();
  });
})();
