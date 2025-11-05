/**
 * Dimensional Reports JavaScript
 * Handles interaction with the new dimensional reporting system
 */

// Global variables
let globalFilters = {
    startDate: null,
    endDate: null,
    costCenter: null,
    project: null,
    additionalDimensions: []
};

let currentReport = null;
let availableDimensions = {};

// Initialize the application
document.addEventListener('DOMContentLoaded', function () {
    initializeDateFilters();
    loadAvailableDimensions();
    showReport('dashboard-summary'); // Show dashboard by default
});

/**
 * Initialize date filters with current month
 */
function initializeDateFilters() {
    const today = new Date();
    const firstDay = new Date(today.getFullYear(), today.getMonth(), 1);
    const lastDay = new Date(today.getFullYear(), today.getMonth() + 1, 0);

    document.getElementById('startDate').value = firstDay.toISOString().split('T')[0];
    document.getElementById('endDate').value = lastDay.toISOString().split('T')[0];

    globalFilters.startDate = firstDay.toISOString().split('T')[0];
    globalFilters.endDate = lastDay.toISOString().split('T')[0];
}

/**
 * Load available dimensions for filtering
 */
async function loadAvailableDimensions() {
    try {
        const response = await fetch('/api/v1/reports/available-dimensions');
        if (response.ok) {
            availableDimensions = await response.json();
            populateDimensionFilters();
        }
    } catch (error) {
        console.error('Error loading dimensions:', error);
        showNotification('Error loading dimension filters', 'error');
    }
}

/**
 * Populate dimension filter dropdowns
 */
function populateDimensionFilters() {
    const costCenterSelect = document.getElementById('costCenterFilter');
    const projectSelect = document.getElementById('projectFilter');
    const additionalSelect = document.getElementById('additionalDimensionsFilter');

    // Clear existing options
    costCenterSelect.innerHTML = '<option value="">All Cost Centers</option>';
    projectSelect.innerHTML = '<option value="">All Projects</option>';
    additionalSelect.innerHTML = '';

    // Populate cost centers (FUNCTIONAL dimensions)
    if (availableDimensions.cost_centers) {
        availableDimensions.cost_centers.forEach(cc => {
            const option = document.createElement('option');
            option.value = cc.id;
            option.textContent = `${cc.code} - ${cc.name}`;
            costCenterSelect.appendChild(option);
        });
    }

    // Populate projects
    if (availableDimensions.projects) {
        availableDimensions.projects.forEach(project => {
            const option = document.createElement('option');
            option.value = project.id;
            option.textContent = `${project.code} - ${project.name}`;
            projectSelect.appendChild(option);
        });
    }

    // Populate additional dimensions
    if (availableDimensions.other_dimensions) {
        availableDimensions.other_dimensions.forEach(dim => {
            const option = document.createElement('option');
            option.value = dim.id;
            option.textContent = `${dim.type}: ${dim.code} - ${dim.name}`;
            additionalSelect.appendChild(option);
        });
    }
}

/**
 * Apply global filters to all reports
 */
function applyGlobalFilters() {
    globalFilters.startDate = document.getElementById('startDate').value;
    globalFilters.endDate = document.getElementById('endDate').value;
    globalFilters.costCenter = document.getElementById('costCenterFilter').value || null;
    globalFilters.project = document.getElementById('projectFilter').value || null;

    const additionalSelect = document.getElementById('additionalDimensionsFilter');
    globalFilters.additionalDimensions = Array.from(additionalSelect.selectedOptions).map(opt => opt.value);

    // Refresh current report with new filters
    if (currentReport) {
        showReport(currentReport);
    }

    showNotification('Filters applied successfully', 'success');
}

/**
 * Clear all filters
 */
function clearFilters() {
    initializeDateFilters();
    document.getElementById('costCenterFilter').value = '';
    document.getElementById('projectFilter').value = '';
    document.getElementById('additionalDimensionsFilter').selectedIndex = -1;

    globalFilters = {
        startDate: document.getElementById('startDate').value,
        endDate: document.getElementById('endDate').value,
        costCenter: null,
        project: null,
        additionalDimensions: []
    };

    // Refresh current report
    if (currentReport) {
        showReport(currentReport);
    }

    showNotification('Filters cleared', 'info');
}

/**
 * Show specified report section
 */
function showReport(reportType) {
    // Hide all report sections
    document.querySelectorAll('.report-section').forEach(section => {
        section.classList.remove('active');
    });

    // Show selected report section
    const reportSection = document.getElementById(`${reportType}-section`);
    if (reportSection) {
        reportSection.classList.add('active');
        currentReport = reportType;

        // Load report data
        loadReportData(reportType);
    }
}

/**
 * Load report data based on type
 */
async function loadReportData(reportType) {
    showLoading(true);

    try {
        let endpoint = `/api/v1/reports/${reportType}`;
        let params = new URLSearchParams();

        // Add global filters to params
        if (globalFilters.startDate) params.append('start_date', globalFilters.startDate);
        if (globalFilters.endDate) params.append('end_date', globalFilters.endDate);
        if (globalFilters.costCenter) params.append('cost_center_id', globalFilters.costCenter);
        if (globalFilters.project) params.append('project_id', globalFilters.project);
        if (globalFilters.additionalDimensions.length > 0) {
            globalFilters.additionalDimensions.forEach(dim => params.append('dimension_ids', dim));
        }

        if (params.toString()) {
            endpoint += '?' + params.toString();
        }

        const response = await fetch(endpoint);
        if (response.ok) {
            const data = await response.json();

            // Render report based on type
            switch (reportType) {
                case 'profit-loss':
                    renderProfitLoss(data);
                    break;
                case 'balance-sheet':
                    renderBalanceSheet(data);
                    break;
                case 'general-ledger':
                    renderGeneralLedger(data);
                    break;
                case 'debtors-analysis':
                    renderDebtorsAnalysis(data);
                    break;
                case 'creditors-analysis':
                    renderCreditorsAnalysis(data);
                    break;
                case 'sales-analysis':
                    renderSalesAnalysis(data);
                    break;
                case 'purchases-analysis':
                    renderPurchasesAnalysis(data);
                    break;
                case 'comparative-analysis':
                    renderComparativeAnalysis(data);
                    break;
                case 'dashboard-summary':
                    renderDashboardSummary(data);
                    break;
                default:
                    console.error('Unknown report type:', reportType);
            }
        } else {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
    } catch (error) {
        console.error('Error loading report data:', error);
        showNotification(`Error loading ${reportType} report: ${error.message}`, 'error');
    } finally {
        showLoading(false);
    }
}

/**
 * Render Profit & Loss report
 */
function renderProfitLoss(data) {
    // Update summary metrics
    const summary = data.summary || {};
    document.getElementById('pl-revenue').textContent = formatCurrency(summary.total_revenue || 0);
    document.getElementById('pl-expenses').textContent = formatCurrency(summary.total_expenses || 0);
    document.getElementById('pl-gross-profit').textContent = formatCurrency(summary.gross_profit || 0);
    document.getElementById('pl-net-profit').textContent = formatCurrency(summary.net_profit || 0);

    // Update table
    const tbody = document.querySelector('#pl-table tbody');
    tbody.innerHTML = '';

    if (data.details && data.details.length > 0) {
        data.details.forEach(item => {
            const row = tbody.insertRow();
            row.innerHTML = `
                <td>${item.account_name || '-'}</td>
                <td>${item.cost_center || '-'}</td>
                <td>${item.project || '-'}</td>
                <td class="text-end">${formatCurrency(item.amount || 0)}</td>
                <td class="text-end">${formatPercentage(item.percentage_of_revenue || 0)}</td>
            `;
        });
    } else {
        tbody.innerHTML = '<tr><td colspan="5" class="text-center text-muted">No data available</td></tr>';
    }
}

/**
 * Render Balance Sheet report
 */
function renderBalanceSheet(data) {
    // Update summary metrics
    const summary = data.summary || {};
    document.getElementById('bs-assets').textContent = formatCurrency(summary.total_assets || 0);
    document.getElementById('bs-liabilities').textContent = formatCurrency(summary.total_liabilities || 0);
    document.getElementById('bs-equity').textContent = formatCurrency(summary.total_equity || 0);

    // Update table
    const tbody = document.querySelector('#bs-table tbody');
    tbody.innerHTML = '';

    if (data.details && data.details.length > 0) {
        data.details.forEach(item => {
            const row = tbody.insertRow();
            const dimensionsHtml = renderDimensionBadges(item.dimensions || []);
            row.innerHTML = `
                <td>${item.category || '-'}</td>
                <td>${item.account_name || '-'}</td>
                <td>${dimensionsHtml}</td>
                <td class="text-end">${formatCurrency(item.amount || 0)}</td>
                <td class="text-end">${formatPercentage(item.percentage_of_total || 0)}</td>
            `;
        });
    } else {
        tbody.innerHTML = '<tr><td colspan="5" class="text-center text-muted">No data available</td></tr>';
    }
}

/**
 * Render General Ledger report
 */
function renderGeneralLedger(data) {
    const tbody = document.querySelector('#gl-table tbody');
    tbody.innerHTML = '';

    if (data.entries && data.entries.length > 0) {
        let runningBalance = 0;
        data.entries.forEach(entry => {
            runningBalance += (entry.debit || 0) - (entry.credit || 0);
            const row = tbody.insertRow();
            row.innerHTML = `
                <td>${formatDate(entry.date)}</td>
                <td>${entry.account_name || '-'}</td>
                <td>${entry.description || '-'}</td>
                <td>${entry.cost_center || '-'}</td>
                <td>${entry.project || '-'}</td>
                <td class="text-end">${entry.debit ? formatCurrency(entry.debit) : '-'}</td>
                <td class="text-end">${entry.credit ? formatCurrency(entry.credit) : '-'}</td>
                <td class="text-end">${formatCurrency(runningBalance)}</td>
            `;
        });
    } else {
        tbody.innerHTML = '<tr><td colspan="8" class="text-center text-muted">No entries found</td></tr>';
    }
}

/**
 * Render Debtors Analysis report
 */
function renderDebtorsAnalysis(data) {
    // Update summary metrics
    const summary = data.summary || {};
    document.getElementById('debtors-total').textContent = formatCurrency(summary.total_outstanding || 0);
    document.getElementById('debtors-current').textContent = formatCurrency(summary.current || 0);
    document.getElementById('debtors-overdue').textContent = formatCurrency(summary.overdue_31_90 || 0);
    document.getElementById('debtors-long-overdue').textContent = formatCurrency(summary.overdue_90_plus || 0);

    // Update table
    const tbody = document.querySelector('#debtors-table tbody');
    tbody.innerHTML = '';

    if (data.details && data.details.length > 0) {
        data.details.forEach(item => {
            const row = tbody.insertRow();
            row.innerHTML = `
                <td>${item.customer_name || '-'}</td>
                <td>${item.cost_center || '-'}</td>
                <td>${item.project || '-'}</td>
                <td class="text-end">${formatCurrency(item.current || 0)}</td>
                <td class="text-end">${formatCurrency(item.days_31_60 || 0)}</td>
                <td class="text-end">${formatCurrency(item.days_61_90 || 0)}</td>
                <td class="text-end">${formatCurrency(item.days_90_plus || 0)}</td>
                <td class="text-end"><strong>${formatCurrency(item.total || 0)}</strong></td>
            `;
        });
    } else {
        tbody.innerHTML = '<tr><td colspan="8" class="text-center text-muted">No outstanding debtors</td></tr>';
    }
}

/**
 * Render Creditors Analysis report
 */
function renderCreditorsAnalysis(data) {
    const tbody = document.querySelector('#creditors-table tbody');
    tbody.innerHTML = '';

    if (data.details && data.details.length > 0) {
        data.details.forEach(item => {
            const row = tbody.insertRow();
            row.innerHTML = `
                <td>${item.supplier_name || '-'}</td>
                <td>${item.cost_center || '-'}</td>
                <td>${item.project || '-'}</td>
                <td class="text-end">${formatCurrency(item.current || 0)}</td>
                <td class="text-end">${formatCurrency(item.days_31_60 || 0)}</td>
                <td class="text-end">${formatCurrency(item.days_61_90 || 0)}</td>
                <td class="text-end">${formatCurrency(item.days_90_plus || 0)}</td>
                <td class="text-end"><strong>${formatCurrency(item.total || 0)}</strong></td>
            `;
        });
    } else {
        tbody.innerHTML = '<tr><td colspan="8" class="text-center text-muted">No outstanding creditors</td></tr>';
    }
}

/**
 * Render Sales Analysis report
 */
function renderSalesAnalysis(data) {
    const tbody = document.querySelector('#sales-table tbody');
    tbody.innerHTML = '';

    if (data.details && data.details.length > 0) {
        data.details.forEach(item => {
            const row = tbody.insertRow();
            row.innerHTML = `
                <td>${item.period || '-'}</td>
                <td>${item.product_service || '-'}</td>
                <td>${item.cost_center || '-'}</td>
                <td>${item.project || '-'}</td>
                <td class="text-end">${item.quantity || 0}</td>
                <td class="text-end">${formatCurrency(item.revenue || 0)}</td>
                <td class="text-end">${formatPercentage(item.growth_percentage || 0)}</td>
            `;
        });
    } else {
        tbody.innerHTML = '<tr><td colspan="7" class="text-center text-muted">No sales data available</td></tr>';
    }
}

/**
 * Render Purchases Analysis report
 */
function renderPurchasesAnalysis(data) {
    // Similar to sales analysis but for purchases
    // Implementation would be similar to renderSalesAnalysis
    console.log('Purchases Analysis data:', data);
}

/**
 * Render Comparative Analysis report
 */
function renderComparativeAnalysis(data) {
    // Implementation for comparative period analysis
    console.log('Comparative Analysis data:', data);
}

/**
 * Render Dashboard Summary
 */
function renderDashboardSummary(data) {
    const summaryContent = document.getElementById('dashboard-summary-content');

    if (data.summary) {
        const summary = data.summary;
        summaryContent.innerHTML = `
            <div class="row">
                <div class="col-md-3">
                    <div class="card bg-primary text-white">
                        <div class="card-body text-center">
                            <h5>Total Revenue</h5>
                            <h3>${formatCurrency(summary.total_revenue || 0)}</h3>
                        </div>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="card bg-success text-white">
                        <div class="card-body text-center">
                            <h5>Total Profit</h5>
                            <h3>${formatCurrency(summary.total_profit || 0)}</h3>
                        </div>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="card bg-info text-white">
                        <div class="card-body text-center">
                            <h5>Active Cost Centers</h5>
                            <h3>${summary.active_cost_centers || 0}</h3>
                        </div>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="card bg-warning text-white">
                        <div class="card-body text-center">
                            <h5>Active Projects</h5>
                            <h3>${summary.active_projects || 0}</h3>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }
}

/**
 * Export report to Excel or PDF
 */
async function exportReport(reportType, format) {
    showLoading(true);

    try {
        let endpoint = `/api/v1/reports/${reportType}/export`;
        let params = new URLSearchParams();

        params.append('format', format);
        if (globalFilters.startDate) params.append('start_date', globalFilters.startDate);
        if (globalFilters.endDate) params.append('end_date', globalFilters.endDate);
        if (globalFilters.costCenter) params.append('cost_center_id', globalFilters.costCenter);
        if (globalFilters.project) params.append('project_id', globalFilters.project);

        endpoint += '?' + params.toString();

        const response = await fetch(endpoint);
        if (response.ok) {
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `${reportType}-${new Date().toISOString().split('T')[0]}.${format}`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            window.URL.revokeObjectURL(url);

            showNotification(`${reportType} exported successfully`, 'success');
        } else {
            throw new Error(`Export failed: ${response.statusText}`);
        }
    } catch (error) {
        console.error('Export error:', error);
        showNotification(`Export failed: ${error.message}`, 'error');
    } finally {
        showLoading(false);
    }
}

/**
 * Utility Functions
 */

function showLoading(show) {
    const spinner = document.getElementById('loadingSpinner');
    spinner.style.display = show ? 'block' : 'none';
}

function formatCurrency(amount) {
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD',
        minimumFractionDigits: 2
    }).format(amount);
}

function formatPercentage(value) {
    return new Intl.NumberFormat('en-US', {
        style: 'percent',
        minimumFractionDigits: 1,
        maximumFractionDigits: 2
    }).format(value / 100);
}

function formatDate(dateString) {
    if (!dateString) return '-';
    return new Date(dateString).toLocaleDateString('en-US');
}

function renderDimensionBadges(dimensions) {
    if (!dimensions || dimensions.length === 0) return '-';

    return dimensions.map(dim =>
        `<span class="dimension-badge">${dim.type}: ${dim.name}</span>`
    ).join('');
}

function showNotification(message, type = 'info') {
    // Create and show notification toast
    const toastContainer = document.getElementById('toast-container') || createToastContainer();

    const toast = document.createElement('div');
    toast.className = `toast align-items-center text-white bg-${type === 'error' ? 'danger' : type} border-0`;
    toast.setAttribute('role', 'alert');
    toast.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">${message}</div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
        </div>
    `;

    toastContainer.appendChild(toast);

    const bsToast = new bootstrap.Toast(toast);
    bsToast.show();

    // Remove toast element after it's hidden
    toast.addEventListener('hidden.bs.toast', () => {
        toast.remove();
    });
}

function createToastContainer() {
    const container = document.createElement('div');
    container.id = 'toast-container';
    container.className = 'toast-container position-fixed top-0 end-0 p-3';
    container.style.zIndex = '9999';
    document.body.appendChild(container);
    return container;
}
