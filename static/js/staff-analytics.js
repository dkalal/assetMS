/**
 * Staff Analytics Dashboard
 * Handles charts, metrics, and data visualization for staff management
 */

// Debug mode - set to false in production to reduce console logs
const STAFF_DEBUG = false;

class StaffAnalytics {
    constructor() {
        this.charts = {};
        this.analyticsData = null;
        this.init();
    }

    init() {
        if (STAFF_DEBUG) console.log('🚀 Staff Analytics initialized');
        this.loadAnalytics();
        this.setupEventListeners();
    }

    setupEventListeners() {
        // Time range selector
        const timeRangeSelect = document.getElementById('timeRange');
        if (timeRangeSelect) {
            timeRangeSelect.addEventListener('change', () => {
                this.loadAnalytics(timeRangeSelect.value);
            });
        }

        // Export button
        const exportBtn = document.getElementById('exportBtn');
        if (exportBtn) {
            exportBtn.addEventListener('click', () => this.exportData());
        }

        // Refresh button
        const refreshBtn = document.getElementById('refreshAnalytics');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => this.loadAnalytics());
        }
    }

    async loadAnalytics(days = 30) {
        try {
            if (STAFF_DEBUG) console.log(`📊 Loading analytics for last ${days} days...`);
            
            // Show loading state
            this.showLoading();

            const response = await fetch(`/settings/api/staff-analytics/?days=${days}`, {
                method: 'GET',
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                }
            });

            if (!response.ok) {
                throw new Error('Failed to load analytics');
            }

            const data = await response.json();
            
            if (data.success) {
                this.analyticsData = data.analytics;
                this.renderCharts();
                this.updateMetrics();
                if (STAFF_DEBUG) console.log('✅ Analytics loaded successfully');
            }
        } catch (error) {
            console.error('❌ Error loading analytics:', error);
            this.showError('Failed to load analytics. Please try again.');
        } finally {
            this.hideLoading();
        }
    }

    renderCharts() {
        if (!this.analyticsData) return;

        // Destroy existing charts
        Object.values(this.charts).forEach(chart => chart?.destroy());
        this.charts = {};

        // Render each chart
        this.renderActivityChart();
        this.renderAssetDistributionChart();
        this.renderDailyTrendChart();
        this.renderRoleDistributionChart();
        this.renderTopPerformersChart();
    }

    renderActivityChart() {
        const canvas = document.getElementById('activityChart');
        if (!canvas || !this.analyticsData.activity_by_user.length) return;

        const data = this.analyticsData.activity_by_user.slice(0, 10);
        
        this.charts.activity = new Chart(canvas, {
            type: 'bar',
            data: {
                labels: data.map(d => d.user__username || 'Unknown'),
                datasets: [{
                    label: 'Activity Count',
                    data: data.map(d => d.count),
                    backgroundColor: 'rgba(23, 107, 135, 0.8)',
                    borderColor: 'rgba(23, 107, 135, 1)',
                    borderWidth: 2,
                    borderRadius: 8,
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    },
                    title: {
                        display: true,
                        text: 'Top 10 Most Active Staff',
                        font: {
                            size: 16,
                            weight: 'bold'
                        }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            precision: 0
                        }
                    }
                }
            }
        });
    }

    renderAssetDistributionChart() {
        const canvas = document.getElementById('assetChart');
        if (!canvas || !this.analyticsData.assets_by_user.length) return;

        const data = this.analyticsData.assets_by_user.slice(0, 8);
        
        this.charts.assets = new Chart(canvas, {
            type: 'doughnut',
            data: {
                labels: data.map(d => d.assigned_to__username || 'Unknown'),
                datasets: [{
                    label: 'Assets Assigned',
                    data: data.map(d => d.count),
                    backgroundColor: [
                        'rgba(23, 107, 135, 0.8)',
                        'rgba(100, 204, 197, 0.8)',
                        'rgba(16, 185, 129, 0.8)',
                        'rgba(245, 158, 11, 0.8)',
                        'rgba(239, 68, 68, 0.8)',
                        'rgba(99, 102, 241, 0.8)',
                        'rgba(236, 72, 153, 0.8)',
                        'rgba(168, 85, 247, 0.8)'
                    ],
                    borderWidth: 2,
                    borderColor: '#fff'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'right',
                        labels: {
                            boxWidth: 15,
                            padding: 10
                        }
                    },
                    title: {
                        display: true,
                        text: 'Asset Distribution by Staff',
                        font: {
                            size: 16,
                            weight: 'bold'
                        }
                    }
                }
            }
        });
    }

    renderDailyTrendChart() {
        const canvas = document.getElementById('trendChart');
        if (!canvas || !this.analyticsData.daily_activity.length) return;

        const data = this.analyticsData.daily_activity;
        
        this.charts.trend = new Chart(canvas, {
            type: 'line',
            data: {
                labels: data.map(d => new Date(d.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })),
                datasets: [{
                    label: 'Daily Activity',
                    data: data.map(d => d.count),
                    fill: true,
                    backgroundColor: 'rgba(23, 107, 135, 0.1)',
                    borderColor: 'rgba(23, 107, 135, 1)',
                    borderWidth: 3,
                    tension: 0.4,
                    pointRadius: 4,
                    pointHoverRadius: 6,
                    pointBackgroundColor: 'rgba(23, 107, 135, 1)',
                    pointBorderColor: '#fff',
                    pointBorderWidth: 2,
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    },
                    title: {
                        display: true,
                        text: 'Activity Trend Over Time',
                        font: {
                            size: 16,
                            weight: 'bold'
                        }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            precision: 0
                        }
                    }
                }
            }
        });
    }

    renderRoleDistributionChart() {
        const canvas = document.getElementById('roleChart');
        if (!canvas || !this.analyticsData.role_stats.length) return;

        const data = this.analyticsData.role_stats;
        
        this.charts.roles = new Chart(canvas, {
            type: 'bar',
            data: {
                labels: data.map(d => d.role.charAt(0).toUpperCase() + d.role.slice(1)),
                datasets: [
                    {
                        label: 'Total',
                        data: data.map(d => d.count),
                        backgroundColor: 'rgba(23, 107, 135, 0.8)',
                        borderColor: 'rgba(23, 107, 135, 1)',
                        borderWidth: 2,
                        borderRadius: 8,
                    },
                    {
                        label: 'Active',
                        data: data.map(d => d.active_count),
                        backgroundColor: 'rgba(16, 185, 129, 0.8)',
                        borderColor: 'rgba(16, 185, 129, 1)',
                        borderWidth: 2,
                        borderRadius: 8,
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: {
                        display: true,
                        text: 'Staff by Role',
                        font: {
                            size: 16,
                            weight: 'bold'
                        }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            precision: 0
                        }
                    }
                }
            }
        });
    }

    renderTopPerformersChart() {
        const canvas = document.getElementById('performersChart');
        if (!canvas || !this.analyticsData.top_performers.length) return;

        const data = this.analyticsData.top_performers;
        
        this.charts.performers = new Chart(canvas, {
            type: 'bar',
            data: {
                labels: data.map(d => `${d.user__first_name} ${d.user__last_name}`),
                datasets: [{
                    label: 'Activity Count',
                    data: data.map(d => d.activity_count),
                    backgroundColor: 'rgba(100, 204, 197, 0.8)',
                    borderColor: 'rgba(100, 204, 197, 1)',
                    borderWidth: 2,
                    borderRadius: 8,
                }]
            },
            options: {
                indexAxis: 'y',
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    },
                    title: {
                        display: true,
                        text: 'Top 5 Performers',
                        font: {
                            size: 16,
                            weight: 'bold'
                        }
                    }
                },
                scales: {
                    x: {
                        beginAtZero: true,
                        ticks: {
                            precision: 0
                        }
                    }
                }
            }
        });
    }

    updateMetrics() {
        if (!this.analyticsData) return;

        // Update allocation rate
        const allocationEl = document.getElementById('allocationRate');
        if (allocationEl) {
            allocationEl.textContent = `${this.analyticsData.allocation_rate}%`;
        }

        // Update inactive staff count
        const inactiveEl = document.getElementById('inactiveStaffCount');
        if (inactiveEl) {
            inactiveEl.textContent = this.analyticsData.inactive_staff_count;
        }

        // Update total staff
        const totalEl = document.getElementById('totalStaffMetric');
        if (totalEl) {
            totalEl.textContent = this.analyticsData.total_staff;
        }

        // Update active staff
        const activeEl = document.getElementById('activeStaffMetric');
        if (activeEl) {
            activeEl.textContent = this.analyticsData.active_staff;
        }

        if (STAFF_DEBUG) console.log('📈 Metrics updated');
    }

    async exportData() {
        try {
            if (STAFF_DEBUG) console.log('📥 Exporting staff data...');
            
            // Show loading on button
            const btn = document.getElementById('exportBtn');
            const originalText = btn.innerHTML;
            btn.innerHTML = '<i class="bi bi-hourglass-split me-2"></i>Exporting...';
            btn.disabled = true;

            window.location.href = '/settings/api/staff-export/?format=excel';

            // Reset button after delay
            setTimeout(() => {
                btn.innerHTML = originalText;
                btn.disabled = false;
            }, 2000);

            if (STAFF_DEBUG) console.log('✅ Export initiated');
        } catch (error) {
            console.error('❌ Export error:', error);
            this.showError('Failed to export data. Please try again.');
        }
    }

    showLoading() {
        const loader = document.getElementById('analyticsLoader');
        if (loader) {
            loader.classList.remove('d-none');
        }
    }

    hideLoading() {
        const loader = document.getElementById('analyticsLoader');
        if (loader) {
            loader.classList.add('d-none');
        }
    }

    showError(message) {
        // You can implement a toast or alert here
        console.error(message);
        alert(message);
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    // Only initialize if we're on the staff management page
    if (document.getElementById('staffAnalytics')) {
        window.staffAnalytics = new StaffAnalytics();
    }
});
