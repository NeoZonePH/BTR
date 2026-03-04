/**
 * TARGET — Chart.js Dashboards
 * Renders analytics charts for incidents.
 */

// Chart.js global defaults
Chart.defaults.color = '#94a3b8';
Chart.defaults.borderColor = 'rgba(255,255,255,0.06)';
Chart.defaults.font.family = "'Inter', sans-serif";

const chartColors = {
    accent: '#00d4ff',
    danger: '#ff1744',
    warning: '#ffab00',
    success: '#00e676',
    purple: '#9b59b6',
    teal: '#1abc9c',
    orange: '#e67e22',
    blue: '#3498db',
    brown: '#795548',
    grey: '#95a5a6',
};

const typeColors = [
    chartColors.danger,
    chartColors.purple,
    chartColors.blue,
    chartColors.teal,
    chartColors.orange,
    chartColors.brown,
    chartColors.grey,
];

// Track chart instances for destroy/recreate
let chartInstances = {};

function destroyChart(id) {
    if (chartInstances[id]) {
        chartInstances[id].destroy();
        delete chartInstances[id];
    }
}

/**
 * Load dashboard mini-charts (used on command dashboards).
 */
function loadDashboardCharts(url) {
    fetch(url + '?range=month', {
        headers: { 'X-Requested-With': 'XMLHttpRequest' },
    })
        .then((r) => r.json())
        .then((data) => {
            // Type doughnut
            const typeCtx = document.getElementById('typeChart');
            if (typeCtx) {
                destroyChart('typeChart');
                chartInstances['typeChart'] = new Chart(typeCtx, {
                    type: 'doughnut',
                    data: {
                        labels: data.type.labels,
                        datasets: [{
                            data: data.type.data,
                            backgroundColor: typeColors,
                            borderWidth: 0,
                        }],
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {
                            legend: { position: 'bottom', labels: { boxWidth: 12, font: { size: 11 } } },
                        },
                    },
                });
            }

            // Status doughnut
            const statusCtx = document.getElementById('statusChart');
            if (statusCtx) {
                destroyChart('statusChart');
                chartInstances['statusChart'] = new Chart(statusCtx, {
                    type: 'doughnut',
                    data: {
                        labels: data.status.labels,
                        datasets: [{
                            data: data.status.data,
                            backgroundColor: [chartColors.warning, chartColors.accent, chartColors.success],
                            borderWidth: 0,
                        }],
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {
                            legend: { position: 'bottom', labels: { boxWidth: 12, font: { size: 11 } } },
                        },
                    },
                });
            }
        })
        .catch((err) => console.error('Chart data error:', err));
}

/**
 * Render full analytics charts (used on analytics page).
 */
function renderAnalyticsCharts(data) {
    // Daily trend line chart
    const dailyCtx = document.getElementById('dailyChart');
    if (dailyCtx) {
        destroyChart('dailyChart');
        chartInstances['dailyChart'] = new Chart(dailyCtx, {
            type: 'line',
            data: {
                labels: data.daily.labels,
                datasets: [{
                    label: 'Incidents',
                    data: data.daily.data,
                    borderColor: chartColors.accent,
                    backgroundColor: 'rgba(0,212,255,0.1)',
                    fill: true,
                    tension: 0.4,
                    pointRadius: 4,
                    pointBackgroundColor: chartColors.accent,
                    pointBorderWidth: 0,
                }],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: { beginAtZero: true, ticks: { stepSize: 1 } },
                    x: { grid: { display: false } },
                },
                plugins: {
                    legend: { display: false },
                },
            },
        });
    }

    // Type bar chart
    const typeCtx = document.getElementById('typeChart');
    if (typeCtx) {
        destroyChart('typeChart');
        chartInstances['typeChart'] = new Chart(typeCtx, {
            type: 'bar',
            data: {
                labels: data.type.labels,
                datasets: [{
                    data: data.type.data,
                    backgroundColor: typeColors,
                    borderRadius: 6,
                    borderSkipped: false,
                }],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                indexAxis: 'y',
                scales: {
                    x: { beginAtZero: true, ticks: { stepSize: 1 } },
                    y: { grid: { display: false } },
                },
                plugins: {
                    legend: { display: false },
                },
            },
        });
    }

    // Region bar chart
    const regionCtx = document.getElementById('regionChart');
    if (regionCtx) {
        destroyChart('regionChart');
        chartInstances['regionChart'] = new Chart(regionCtx, {
            type: 'bar',
            data: {
                labels: data.region.labels.map((l) => l.length > 20 ? l.slice(0, 20) + '…' : l),
                datasets: [{
                    data: data.region.data,
                    backgroundColor: chartColors.accent,
                    borderRadius: 6,
                    borderSkipped: false,
                }],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: { beginAtZero: true, ticks: { stepSize: 1 } },
                    x: { grid: { display: false } },
                },
                plugins: {
                    legend: { display: false },
                },
            },
        });
    }

    // Status doughnut
    const statusCtx = document.getElementById('statusChart');
    if (statusCtx) {
        destroyChart('statusChart');
        chartInstances['statusChart'] = new Chart(statusCtx, {
            type: 'doughnut',
            data: {
                labels: data.status.labels,
                datasets: [{
                    data: data.status.data,
                    backgroundColor: [chartColors.warning, chartColors.accent, chartColors.success],
                    borderWidth: 0,
                }],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { position: 'bottom', labels: { boxWidth: 12, font: { size: 11 } } },
                },
            },
        });
    }
}
