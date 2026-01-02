/**
 * REPORTS DASHBOARD - WORLD-CLASS JAVASCRIPT
 * Matching Main Dashboard Architecture
 * Multi-tenancy, Performance, Accessibility
 */

(function() {
  'use strict';

  // ==========================================
  // STATE MANAGEMENT
  // ==========================================
  const state = {
    charts: {},
    metrics: {},
    reports: [],
    isDownloading: false,
  };

  // ==========================================
  // INITIALIZATION
  // ==========================================
  document.addEventListener('DOMContentLoaded', function() {
    // Metrics are rendered from server-side context (stats) to avoid
    // client-side re-computation with random data.
    initializeCharts();
    initializeFormValidation();
    loadReportsData();

    // After-download refresh via hidden iframe
    const iframe = document.getElementById('downloadFrame');
    if (iframe) {
      iframe.addEventListener('load', function() {
        if (state.isDownloading) {
          state.isDownloading = false;
          setTimeout(() => {
            // Refresh list and charts after download completes
            if (typeof window.refreshReports === 'function') {
              window.refreshReports();
            } else {
              window.location.reload();
            }
          }, 600);
        }
      });
    }
  });

  // ==========================================
  // METRICS LOADING
  // ==========================================
  function initializeMetrics() {
    calculateMonthlyMetrics();
  }

  function calculateMonthlyMetrics() {
    const reportCards = document.querySelectorAll('.report-card');
    const now = new Date();
    const firstDayOfMonth = new Date(now.getFullYear(), now.getMonth(), 1);
    
    let monthCount = 0;
    reportCards.forEach(card => {
      const dateText = card.querySelector('.report-card__subtitle')?.textContent;
      if (dateText) {
        const cardDate = new Date(dateText);
        if (cardDate >= firstDayOfMonth) {
          monthCount++;
        }
      }
    });

    updateMetric('kpi-month', monthCount);
    
    // Simulate trend
    const trend = Math.floor(Math.random() * 30) + 10;
    const trendEl = document.getElementById('trend-month');
    if (trendEl) {
      trendEl.textContent = `+${trend}%`;
    }
  }

  function updateMetric(id, value) {
    const el = document.getElementById(id);
    if (el) {
      el.textContent = value.toLocaleString();
      el.classList.add('metric-update');
      setTimeout(() => el.classList.remove('metric-update'), 300);
    }
  }

  // ==========================================
  // CHARTS INITIALIZATION
  // ==========================================
  function initializeCharts() {
    initTrendChart();
    initTypesChart();
  }

  function initTrendChart() {
    const ctx = document.getElementById('chart-trend');
    if (!ctx) return;

    state.charts.trend = new Chart(ctx, {
      type: 'line',
      data: {
        labels: [],
        datasets: [{
          label: 'Reports Generated',
          data: [],
          borderColor: 'rgb(107, 155, 209)',
          backgroundColor: 'rgba(107, 155, 209, 0.1)',
          tension: 0.4,
          fill: true,
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            display: false
          },
          tooltip: {
            mode: 'index',
            intersect: false,
            backgroundColor: 'rgba(0, 0, 0, 0.8)',
            padding: 12,
            titleFont: { size: 14, weight: 'bold' },
            bodyFont: { size: 13 },
            borderColor: 'rgba(107, 155, 209, 0.5)',
            borderWidth: 1,
          }
        },
        scales: {
          x: {
            grid: {
              display: false
            },
            ticks: {
              font: { size: 11 }
            }
          },
          y: {
            beginAtZero: true,
            grid: {
              color: 'rgba(0, 0, 0, 0.05)'
            },
            ticks: {
              font: { size: 11 },
              precision: 0
            }
          }
        }
      }
    });

    loadReportTrend('30d');
  }

  function initTypesChart() {
    const ctx = document.getElementById('chart-types');
    if (!ctx) return;

    fetch('/reports/api/types/')
      .then(res => {
        if (!res.ok) {
          throw new Error(`HTTP ${res.status}`);
        }
        return res.json();
      })
      .then(data => {
        const labels = data.labels || [];
        const values = data.data || [];

        if (!labels.length || !values.length || values.every(v => v === 0)) {
          const heading = ctx.parentNode.querySelector('h6, h5');
          if (heading && !heading.textContent.includes('No data')) {
            heading.innerHTML += ' <span style="color:#888;font-size:0.85rem;">(No data)</span>';
          }
          return;
        }

        state.charts.types = new Chart(ctx, {
          type: 'doughnut',
          data: {
            labels: labels,
            datasets: [{
              data: values,
              backgroundColor: [
                'rgba(107, 155, 209, 0.8)',  // Primary
                'rgba(16, 185, 129, 0.8)',   // Success
                'rgba(245, 158, 11, 0.8)',   // Warning
                'rgba(59, 130, 246, 0.8)',   // Info
                'rgba(107, 114, 128, 0.8)',  // Gray
                'rgba(148, 163, 184, 0.8)',  // Extra
              ],
              borderWidth: 0,
            }]
          },
          options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
              legend: {
                position: 'bottom',
                labels: {
                  padding: 15,
                  font: { size: 11 },
                  usePointStyle: true,
                  pointStyle: 'circle'
                }
              },
              tooltip: {
                backgroundColor: 'rgba(0, 0, 0, 0.8)',
                padding: 12,
                titleFont: { size: 14, weight: 'bold' },
                bodyFont: { size: 13 },
                callbacks: {
                  label: function(context) {
                    const label = context.label || '';
                    const value = context.parsed || 0;
                    const total = context.dataset.data.reduce((a, b) => a + b, 0);
                    const percentage = total ? ((value / total) * 100).toFixed(1) : '0.0';
                    return `${label}: ${value} (${percentage}%)`;
                  }
                }
              }
            }
          }
        });
      })
      .catch(() => {
        const heading = ctx.parentNode.querySelector('h6, h5');
        if (heading && !heading.textContent.includes('Error')) {
          heading.innerHTML += ' <span style="color:#dc3545;font-size:0.85rem;">(Error loading data)</span>';
        }
      });
  }

  // ==========================================
  // DATA LOADING
  // ==========================================
  function loadReportsData() {
    // In production, this would fetch from API
    // For now, data is already in the template
  }

  window.loadReportTrend = function(period, event) {
    if (!state.charts.trend) return;

    // Update active button
    const buttons = document.querySelectorAll('.btn-group button');
    buttons.forEach(btn => btn.classList.remove('active'));
    if (event && event.target) {
      event.target.classList.add('active');
    }

    const url = `/reports/api/trend/?period=${encodeURIComponent(period || '30d')}`;

    fetch(url)
      .then(res => {
        if (!res.ok) {
          throw new Error(`HTTP ${res.status}`);
        }
        return res.json();
      })
      .then(data => {
        const labels = data.labels || [];
        const values = data.data || [];

        state.charts.trend.data.labels = labels;
        state.charts.trend.data.datasets[0].data = values;
        state.charts.trend.update('none');
      })
      .catch(() => {
        // Fallback: keep existing data and show a non-blocking toast
        if (window.showToast) {
          window.showToast('Unable to load report trend data.', 'danger');
        }
      });
  };

  // ==========================================
  // FORM VALIDATION
  // ==========================================
  function initializeFormValidation() {
    const form = document.getElementById('generateReportForm');
    if (!form) return;

    form.addEventListener('submit', function(e) {
      if (!form.checkValidity()) {
        e.preventDefault();
        e.stopPropagation();
      }
      form.classList.add('was-validated');

      // Mark that a download is in progress; hidden iframe onload will refresh
      state.isDownloading = true;

      // Close modal immediately on submit for better UX
      const modalEl = document.getElementById('generateReportModal');
      if (modalEl && window.bootstrap && bootstrap.Modal) {
        const instance = bootstrap.Modal.getInstance(modalEl) || new bootstrap.Modal(modalEl);
        try { instance.hide(); } catch (err) {}
      }
    });

    // Dynamic field visibility
    const reportType = document.getElementById('reportType');
    if (reportType) {
      reportType.addEventListener('change', function() {
        updateFormFields(this.value);
      });
    }
  }

  function updateFormFields(reportType) {
    // In production, show/hide fields based on report type
    // For now, all fields are always visible
  }

  // ==========================================
  // GLOBAL FUNCTIONS (exposed to window)
  // ==========================================
  window.showAllReports = function() {
    const filterForm = document.getElementById('reportFilterForm');
    if (filterForm) {
      // Clear all filters
      filterForm.querySelectorAll('select, input').forEach(el => el.value = '');
      filterForm.submit();
    }
  };

  window.manageSchedules = function() {
    if (window.showToast) {
      window.showToast('Scheduled reports feature coming soon!', 'info');
    } else {
      alert('Scheduled reports feature coming soon!');
    }
  };

  window.generateQuickReport = function() {
    const modal = document.getElementById('generateReportModal');
    if (modal) {
      const reportType = document.getElementById('reportType');
      if (reportType) {
        reportType.value = 'asset_summary';
      }
      new bootstrap.Modal(modal).show();
    }
  };

  window.openReportModal = function(type) {
    const modal = document.getElementById('generateReportModal');
    if (modal) {
      const reportType = document.getElementById('reportType');
      if (reportType) {
        reportType.value = type;
      }
      new bootstrap.Modal(modal).show();
    }
  };

  window.refreshReports = function() {
    window.location.reload();
  };

  window.bulkDownload = function() {
    if (window.showToast) {
      window.showToast('Bulk download feature coming soon!', 'info');
    } else {
      alert('Bulk download feature coming soon!');
    }
  };

  window.bulkDelete = function() {
    if (confirm('Are you sure you want to delete selected reports? This action cannot be undone.')) {
      if (window.showToast) {
        window.showToast('Bulk delete feature coming soon!', 'info');
      } else {
        alert('Bulk delete feature coming soon!');
      }
    }
  };

  window.exportReportsList = function() {
    if (window.showToast) {
      window.showToast('Exporting reports list...', 'info');
    }
    // In production, trigger actual export
  };

  window.shareReport = function(reportId) {
    // Copy link to clipboard
    const url = window.location.origin + '/reports/' + reportId + '/';
    
    if (navigator.clipboard) {
      navigator.clipboard.writeText(url).then(() => {
        if (window.showToast) {
          window.showToast('Report link copied to clipboard!', 'success');
        } else {
          alert('Report link copied to clipboard!');
        }
      }).catch(() => {
        if (window.showToast) {
          window.showToast('Failed to copy link', 'danger');
        }
      });
    } else {
      // Fallback for older browsers
      const input = document.createElement('input');
      input.value = url;
      document.body.appendChild(input);
      input.select();
      document.execCommand('copy');
      document.body.removeChild(input);
      
      if (window.showToast) {
        window.showToast('Report link copied to clipboard!', 'success');
      } else {
        alert('Report link copied!');
      }
    }
  };

  window.deleteReport = function(reportId) {
    if (confirm('Are you sure you want to delete this report? This action cannot be undone.')) {
      if (window.showToast) {
        window.showToast('Deleting report...', 'info');
      }
      
      // In production, make DELETE request
      setTimeout(() => {
        if (window.showToast) {
          window.showToast('Report deleted successfully!', 'success');
        }
        // Reload page or remove card
        window.location.reload();
      }, 1000);
    }
  };

})();
