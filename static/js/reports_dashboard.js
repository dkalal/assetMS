// Reports Dashboard Page JS (moved from inline script in reports_dashboard.html for CSP compliance)

document.addEventListener('DOMContentLoaded', function() {
  // Custom modal open/close logic for report generation
  const openGenerateReportModalBtn = document.getElementById('openGenerateReportModal');
  const generateReportModalCustom = document.getElementById('generateReportModalCustom');
  const closeGenerateReportModalBtn = document.getElementById('closeGenerateReportModal');
  const cancelGenerateReportModalBtn = document.getElementById('cancelGenerateReportModal');
  const applyFiltersBtn = document.getElementById('applyFiltersBtn');
  const filterBranch = document.getElementById('filterBranch');
  const filterStatus = document.getElementById('filterStatus');
  const filterDateFrom = document.getElementById('filterDateFrom');
  const filterDateTo = document.getElementById('filterDateTo');
  const modalBranchId = document.getElementById('modalBranchId');
  const modalStatus = document.getElementById('modalStatus');
  const modalDateFrom = document.getElementById('modalDateFrom');
  const modalDateTo = document.getElementById('modalDateTo');
  const generateReportForm = document.querySelector('#generateReportModalCustom form');

  if (openGenerateReportModalBtn && generateReportModalCustom && closeGenerateReportModalBtn && cancelGenerateReportModalBtn) {
    openGenerateReportModalBtn.addEventListener('click', () => {
      generateReportModalCustom.classList.add('active');
      generateReportModalCustom.focus();
    });
    closeGenerateReportModalBtn.addEventListener('click', () => {
      generateReportModalCustom.classList.remove('active');
    });
    cancelGenerateReportModalBtn.addEventListener('click', () => {
      generateReportModalCustom.classList.remove('active');
    });
    generateReportModalCustom.addEventListener('click', (e) => {
      if (e.target === generateReportModalCustom) {
        generateReportModalCustom.classList.remove('active');
      }
    });
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && generateReportModalCustom.classList.contains('active')) {
        generateReportModalCustom.classList.remove('active');
      }
    });
  }

  if (generateReportForm) {
    generateReportForm.addEventListener('submit', () => {
      if (modalBranchId && filterBranch) {
        modalBranchId.value = filterBranch.value || '';
      }
      if (modalStatus && filterStatus) {
        modalStatus.value = filterStatus.value || '';
      }
      if (modalDateFrom && filterDateFrom) {
        modalDateFrom.value = filterDateFrom.value || '';
      }
      if (modalDateTo && filterDateTo) {
        modalDateTo.value = filterDateTo.value || '';
      }
    });
  }

  if (applyFiltersBtn && generateReportForm) {
    applyFiltersBtn.addEventListener('click', () => {
      modalBranchId.value = filterBranch.value || '';
      modalStatus.value = filterStatus.value || '';
      modalDateFrom.value = filterDateFrom.value || '';
      modalDateTo.value = filterDateTo.value || '';
      generateReportModalCustom.classList.add('active');
      generateReportModalCustom.focus();
    });
  }
});