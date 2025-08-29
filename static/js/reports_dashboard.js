// Reports Dashboard Page JS (moved from inline script in reports_dashboard.html for CSP compliance)

document.addEventListener('DOMContentLoaded', function() {
  // Custom modal open/close logic for report generation
  const openGenerateReportModalBtn = document.getElementById('openGenerateReportModal');
  const generateReportModalCustom = document.getElementById('generateReportModalCustom');
  const closeGenerateReportModalBtn = document.getElementById('closeGenerateReportModal');
  const cancelGenerateReportModalBtn = document.getElementById('cancelGenerateReportModal');
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
}); 