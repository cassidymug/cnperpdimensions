// Cash Reports JavaScript
const API_BASE = 'http://localhost:8010/api/v1';

let cashTrendChart = null;
let cashSourceChart = null;

// Initialize on page load
document.addEventListener('DOMContentLoaded', function () {
    console.log('Cash Reports page loaded');

    // Set default date range (last 30 days)
    const today = new Date();
    const thirtyDaysAgo = new Date(today);
    thirtyDaysAgo.setDate(today.getDate() - 30);

    document.getElementById('filterEndDate').value = today.toISOString().split('T')[0];
    document.getElementById('filterStartDate').value = thirtyDaysAgo.toISOString().split('T')[0];

    // Load branches
    loadBranches();

    // Initialize empty charts
    initializeCharts();
});

// Load branches
async function loadBranches() {
    try {
        const response = await fetch(`${API_BASE}/branches/`);
        if (!response.ok) throw new Error('Failed to load branches');

        const branches = await response.json();
        const branchSelect = document.getElementById('filterBranch');

        branchSelect.innerHTML = '<option value="">All Branches</option>';
        branches.forEach(branch => {
            branchSelect.add(new Option(branch.name, branch.id));
        });
    } catch (error) {
        console.error('Error loading branches:', error);
    }
}

// Load all reports
async function loadReports() {
    const spinner = document.getElementById('loadingSpinner');
    spinner.style.display = 'block';

    try {
        const startDate = document.getElementById('filterStartDate').value;
        const endDate = document.getElementById('filterEndDate').value;
        const branchId = document.getElementById('filterBranch').value;

        if (!startDate || !endDate) {
            showAlert('Please select both start and end dates', 'warning');
            return;
        }

        // Load data in parallel
        await Promise.all([
            loadStatistics(startDate, endDate, branchId),
            loadCashierPerformance(startDate, endDate, branchId),
            loadDailySummary(startDate, endDate, branchId),
            updateCharts(startDate, endDate, branchId)
        ]);

        showAlert('Report generated successfully!', 'success');

    } catch (error) {
        console.error('Error loading reports:', error);
        showAlert('Failed to load reports. Please try again.', 'danger');
    } finally {
        spinner.style.display = 'none';
    }
}

// Load statistics
async function loadStatistics(startDate, endDate, branchId) {
    try {
        const params = new URLSearchParams();
        params.append('start_date', startDate);
        params.append('end_date', endDate);
        if (branchId) params.append('branch_id', branchId);

        // Fetch cash submissions
        const submissionsResponse = await fetch(`${API_BASE}/sales/cash-submissions?${params}`);
        const submissions = await submissionsResponse.json();

        // Fetch float allocations
        const allocationsResponse = await fetch(`${API_BASE}/sales/float-allocations?${params}`);
        const allocations = await allocationsResponse.json();

        // Calculate totals
        const totalCashReceived = submissions.reduce((sum, s) => sum + parseFloat(s.amount), 0);
        const totalFloatAllocated = allocations.reduce((sum, a) => sum + parseFloat(a.amount || a.float_amount), 0);
        const outstandingFloats = allocations
            .filter(a => a.status === 'allocated')
            .reduce((sum, a) => sum + parseFloat(a.amount || a.float_amount), 0);

        // Calculate total variance
        const totalVariance = allocations.reduce((sum, a) => {
            if (a.returned_amount) {
                const variance = parseFloat(a.returned_amount) - parseFloat(a.amount || a.float_amount);
                return sum + variance;
            }
            return sum;
        }, 0);

        // Update UI
        document.getElementById('totalCashReceived').textContent = `P ${totalCashReceived.toFixed(2)}`;
        document.getElementById('totalFloatAllocated').textContent = `P ${totalFloatAllocated.toFixed(2)}`;
        document.getElementById('outstandingFloats').textContent = `P ${outstandingFloats.toFixed(2)}`;
        document.getElementById('totalVariance').textContent = `P ${totalVariance.toFixed(2)}`;

        // Color code variance
        const varianceEl = document.getElementById('totalVariance');
        if (totalVariance < 0) {
            varianceEl.parentElement.parentElement.parentElement.className = 'stat-card danger';
        } else if (totalVariance > 0) {
            varianceEl.parentElement.parentElement.parentElement.className = 'stat-card warning';
        } else {
            varianceEl.parentElement.parentElement.parentElement.className = 'stat-card success';
        }

    } catch (error) {
        console.error('Error loading statistics:', error);
        throw error;
    }
}

// Load cashier performance
async function loadCashierPerformance(startDate, endDate, branchId) {
    try {
        const params = new URLSearchParams();
        params.append('start_date', startDate);
        params.append('end_date', endDate);
        if (branchId) params.append('branch_id', branchId);

        // Fetch data
        const [submissionsResponse, allocationsResponse] = await Promise.all([
            fetch(`${API_BASE}/sales/cash-submissions?${params}`),
            fetch(`${API_BASE}/sales/float-allocations?${params}`)
        ]);

        const submissions = await submissionsResponse.json();
        const allocations = await allocationsResponse.json();

        // Group by cashier/salesperson
        const performanceMap = new Map();

        // Process submissions
        submissions.forEach(sub => {
            const key = sub.salesperson_id;
            const name = sub.salesperson_name || 'Unknown';

            if (!performanceMap.has(key)) {
                performanceMap.set(key, {
                    name: name,
                    submissions: 0,
                    totalAmount: 0,
                    floatsAllocated: 0,
                    floatAmount: 0,
                    floatsReturned: 0,
                    variance: 0
                });
            }

            const perf = performanceMap.get(key);
            perf.submissions++;
            perf.totalAmount += parseFloat(sub.amount);
        });

        // Process allocations
        allocations.forEach(alloc => {
            const key = alloc.cashier_id;
            const name = alloc.cashier_name || 'Unknown';

            if (!performanceMap.has(key)) {
                performanceMap.set(key, {
                    name: name,
                    submissions: 0,
                    totalAmount: 0,
                    floatsAllocated: 0,
                    floatAmount: 0,
                    floatsReturned: 0,
                    variance: 0
                });
            }

            const perf = performanceMap.get(key);
            perf.floatsAllocated++;
            perf.floatAmount += parseFloat(alloc.amount || alloc.float_amount);

            if (alloc.status === 'returned' || alloc.returned_amount) {
                perf.floatsReturned++;
                const variance = parseFloat(alloc.returned_amount || 0) - parseFloat(alloc.amount || alloc.float_amount);
                perf.variance += variance;
            }
        });

        // Build table
        const tbody = document.getElementById('cashierPerformanceTable');

        if (performanceMap.size === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="8" class="text-center text-muted py-4">
                        No data found for the selected period
                    </td>
                </tr>
            `;
        } else {
            tbody.innerHTML = Array.from(performanceMap.values())
                .map(perf => {
                    const varianceClass = perf.variance < 0 ? 'variance-negative' :
                        perf.variance > 0 ? 'variance-positive' : '';
                    const status = perf.floatsAllocated > perf.floatsReturned ?
                        '<span class="badge bg-warning">Outstanding</span>' :
                        '<span class="badge bg-success">Clear</span>';

                    return `
                        <tr>
                            <td><strong>${perf.name}</strong></td>
                            <td>${perf.submissions}</td>
                            <td class="amount-display">P ${perf.totalAmount.toFixed(2)}</td>
                            <td>${perf.floatsAllocated}</td>
                            <td class="amount-display">P ${perf.floatAmount.toFixed(2)}</td>
                            <td>${perf.floatsReturned}</td>
                            <td class="${varianceClass}">P ${perf.variance.toFixed(2)}</td>
                            <td>${status}</td>
                        </tr>
                    `;
                })
                .join('');
        }

    } catch (error) {
        console.error('Error loading cashier performance:', error);
        throw error;
    }
}

// Load daily summary
async function loadDailySummary(startDate, endDate, branchId) {
    try {
        const params = new URLSearchParams();
        params.append('start_date', startDate);
        params.append('end_date', endDate);
        if (branchId) params.append('branch_id', branchId);

        // Fetch data
        const [submissionsResponse, allocationsResponse] = await Promise.all([
            fetch(`${API_BASE}/sales/cash-submissions?${params}`),
            fetch(`${API_BASE}/sales/float-allocations?${params}`)
        ]);

        const submissions = await submissionsResponse.json();
        const allocations = await allocationsResponse.json();

        // Group by date
        const dailyMap = new Map();

        // Process submissions
        submissions.forEach(sub => {
            const date = sub.submission_date;

            if (!dailyMap.has(date)) {
                dailyMap.set(date, {
                    submissions: 0,
                    totalCash: 0,
                    allocations: 0,
                    totalFloat: 0,
                    returned: 0,
                    variance: 0
                });
            }

            const daily = dailyMap.get(date);
            daily.submissions++;
            daily.totalCash += parseFloat(sub.amount);
        });

        // Process allocations
        allocations.forEach(alloc => {
            const date = alloc.allocation_date;

            if (!dailyMap.has(date)) {
                dailyMap.set(date, {
                    submissions: 0,
                    totalCash: 0,
                    allocations: 0,
                    totalFloat: 0,
                    returned: 0,
                    variance: 0
                });
            }

            const daily = dailyMap.get(date);
            daily.allocations++;
            daily.totalFloat += parseFloat(alloc.amount || alloc.float_amount);

            if (alloc.status === 'returned' || alloc.returned_amount) {
                daily.returned++;
                const variance = parseFloat(alloc.returned_amount || 0) - parseFloat(alloc.amount || alloc.float_amount);
                daily.variance += variance;
            }
        });

        // Build table
        const tbody = document.getElementById('dailySummaryTable');

        if (dailyMap.size === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="7" class="text-center text-muted py-4">
                        No data found for the selected period
                    </td>
                </tr>
            `;
        } else {
            // Sort by date descending
            const sortedDates = Array.from(dailyMap.keys()).sort((a, b) => b.localeCompare(a));

            tbody.innerHTML = sortedDates
                .map(date => {
                    const daily = dailyMap.get(date);
                    const varianceClass = daily.variance < 0 ? 'variance-negative' :
                        daily.variance > 0 ? 'variance-positive' : '';

                    return `
                        <tr>
                            <td><strong>${formatDate(date)}</strong></td>
                            <td>${daily.submissions}</td>
                            <td class="amount-display">P ${daily.totalCash.toFixed(2)}</td>
                            <td>${daily.allocations}</td>
                            <td class="amount-display">P ${daily.totalFloat.toFixed(2)}</td>
                            <td>${daily.returned}</td>
                            <td class="${varianceClass}">P ${daily.variance.toFixed(2)}</td>
                        </tr>
                    `;
                })
                .join('');
        }

    } catch (error) {
        console.error('Error loading daily summary:', error);
        throw error;
    }
}

// Initialize charts
function initializeCharts() {
    const trendCtx = document.getElementById('cashTrendChart').getContext('2d');
    const sourceCtx = document.getElementById('cashSourceChart').getContext('2d');

    cashTrendChart = new Chart(trendCtx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [
                {
                    label: 'Cash Received',
                    data: [],
                    borderColor: '#667eea',
                    backgroundColor: 'rgba(102, 126, 234, 0.1)',
                    tension: 0.4
                },
                {
                    label: 'Float Allocated',
                    data: [],
                    borderColor: '#38ef7d',
                    backgroundColor: 'rgba(56, 239, 125, 0.1)',
                    tension: 0.4
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'top'
                }
            },
            scales: {
                y: {
                    beginAtZero: true
                }
            }
        }
    });

    cashSourceChart = new Chart(sourceCtx, {
        type: 'doughnut',
        data: {
            labels: ['Cash Submissions', 'Float Returns', 'Outstanding Floats'],
            datasets: [{
                data: [0, 0, 0],
                backgroundColor: [
                    '#667eea',
                    '#38ef7d',
                    '#f5576c'
                ]
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom'
                }
            }
        }
    });
}

// Update charts with data
async function updateCharts(startDate, endDate, branchId) {
    try {
        const params = new URLSearchParams();
        params.append('start_date', startDate);
        params.append('end_date', endDate);
        if (branchId) params.append('branch_id', branchId);

        // Fetch data
        const [submissionsResponse, allocationsResponse] = await Promise.all([
            fetch(`${API_BASE}/sales/cash-submissions?${params}`),
            fetch(`${API_BASE}/sales/float-allocations?${params}`)
        ]);

        const submissions = await submissionsResponse.json();
        const allocations = await allocationsResponse.json();

        // Process data for trend chart
        const dailyData = new Map();

        submissions.forEach(sub => {
            const date = sub.submission_date;
            if (!dailyData.has(date)) {
                dailyData.set(date, { cash: 0, float: 0 });
            }
            dailyData.get(date).cash += parseFloat(sub.amount);
        });

        allocations.forEach(alloc => {
            const date = alloc.allocation_date;
            if (!dailyData.has(date)) {
                dailyData.set(date, { cash: 0, float: 0 });
            }
            dailyData.get(date).float += parseFloat(alloc.amount || alloc.float_amount);
        });

        // Sort dates and update trend chart
        const sortedDates = Array.from(dailyData.keys()).sort();
        const cashData = sortedDates.map(date => dailyData.get(date).cash);
        const floatData = sortedDates.map(date => dailyData.get(date).float);

        cashTrendChart.data.labels = sortedDates.map(formatDate);
        cashTrendChart.data.datasets[0].data = cashData;
        cashTrendChart.data.datasets[1].data = floatData;
        cashTrendChart.update();

        // Update source chart
        const totalCash = submissions.reduce((sum, s) => sum + parseFloat(s.amount), 0);
        const totalReturned = allocations
            .filter(a => a.returned_amount)
            .reduce((sum, a) => sum + parseFloat(a.returned_amount), 0);
        const totalOutstanding = allocations
            .filter(a => a.status === 'allocated')
            .reduce((sum, a) => sum + parseFloat(a.amount || a.float_amount), 0);

        cashSourceChart.data.datasets[0].data = [totalCash, totalReturned, totalOutstanding];
        cashSourceChart.update();

    } catch (error) {
        console.error('Error updating charts:', error);
        throw error;
    }
}

// Export to Excel
function exportToExcel() {
    showAlert('Excel export feature coming soon!', 'info');
    // TODO: Implement Excel export using a library like xlsx
}

// Export to PDF
function exportToPDF() {
    showAlert('PDF export feature coming soon!', 'info');
    // TODO: Implement PDF export using a library like jsPDF
}

// Utility functions
function formatDate(dateString) {
    if (!dateString) return 'N/A';
    const date = new Date(dateString);
    return date.toLocaleDateString('en-GB');
}

function showAlert(message, type = 'info') {
    const alertHtml = `
        <div class="alert alert-${type} alert-dismissible fade show position-fixed top-0 start-50 translate-middle-x mt-3"
             style="z-index: 9999; min-width: 300px;" role="alert">
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
    `;

    document.body.insertAdjacentHTML('beforeend', alertHtml);

    setTimeout(() => {
        const alert = document.querySelector('.alert');
        if (alert) {
            alert.remove();
        }
    }, 5000);
}
