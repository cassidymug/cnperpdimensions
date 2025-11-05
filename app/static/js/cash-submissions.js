// Cash Submissions JavaScript
const API_BASE = 'http://localhost:8010/api/v1';

// Initialize on page load
document.addEventListener('DOMContentLoaded', function () {
    console.log('Cash Submissions page loaded');

    // Set today's date as default
    const today = new Date().toISOString().split('T')[0];
    document.getElementById('submissionDate').value = today;
    document.getElementById('filterStartDate').value = today;
    document.getElementById('filterEndDate').value = today;

    // Load initial data
    loadUsers();
    loadBranches();
    loadSubmissions();
    loadStatistics();

    // Setup denomination calculator
    setupDenominationCalculator();

    // Refresh data every 30 seconds
    setInterval(() => {
        loadSubmissions();
        loadStatistics();
    }, 30000);
});

// Load users for dropdowns
async function loadUsers() {
    try {
        const response = await fetch(`${API_BASE}/users/`);
        if (!response.ok) throw new Error('Failed to load users');

        const users = await response.json();

        // Populate salesperson dropdown
        const salespersonSelect = document.getElementById('salespersonId');
        const receivedBySelect = document.getElementById('receivedById');
        const filterSelect = document.getElementById('filterSalesperson');

        salespersonSelect.innerHTML = '<option value="">Select salesperson...</option>';
        receivedBySelect.innerHTML = '<option value="">Select manager/receiver...</option>';
        filterSelect.innerHTML = '<option value="">All Salespersons</option>';

        users.forEach(user => {
            const name = `${user.first_name || ''} ${user.last_name || ''}`.trim() || user.username;
            const option = new Option(name, user.id);

            salespersonSelect.add(option.cloneNode(true));
            receivedBySelect.add(option.cloneNode(true));
            filterSelect.add(option.cloneNode(true));
        });
    } catch (error) {
        console.error('Error loading users:', error);
        showAlert('Failed to load users. Please refresh the page.', 'danger');
    }
}

// Load branches
async function loadBranches() {
    try {
        const response = await fetch(`${API_BASE}/branches/`);
        if (!response.ok) throw new Error('Failed to load branches');

        const branches = await response.json();
        const branchSelect = document.getElementById('branchId');

        branchSelect.innerHTML = '<option value="">Select branch...</option>';
        branches.forEach(branch => {
            branchSelect.add(new Option(branch.name, branch.id));
        });

        // Auto-select first branch if only one exists
        if (branches.length === 1) {
            branchSelect.value = branches[0].id;
        }
    } catch (error) {
        console.error('Error loading branches:', error);
    }
}

// Load submissions with filters
async function loadSubmissions() {
    const spinner = document.getElementById('loadingSpinner');
    const tableBody = document.getElementById('submissionsTableBody');

    spinner.style.display = 'block';

    try {
        // Build query parameters
        const params = new URLSearchParams();

        const startDate = document.getElementById('filterStartDate').value;
        const endDate = document.getElementById('filterEndDate').value;
        const salespersonId = document.getElementById('filterSalesperson').value;
        const status = document.getElementById('filterStatus').value;

        if (startDate) params.append('start_date', startDate);
        if (endDate) params.append('end_date', endDate);
        if (salespersonId) params.append('salesperson_id', salespersonId);
        if (status) params.append('status_filter', status);

        const response = await fetch(`${API_BASE}/sales/cash-submissions?${params}`);
        if (!response.ok) throw new Error('Failed to load submissions');

        const submissions = await response.json();

        // Populate table
        if (submissions.length === 0) {
            tableBody.innerHTML = `
                <tr>
                    <td colspan="7" class="text-center text-muted py-4">
                        No submissions found for the selected filters.
                    </td>
                </tr>
            `;
        } else {
            tableBody.innerHTML = submissions.map(sub => `
                <tr>
                    <td>${formatDate(sub.submission_date)}</td>
                    <td>${sub.salesperson_name || 'Unknown'}</td>
                    <td class="amount-display">P ${parseFloat(sub.amount).toFixed(2)}</td>
                    <td>${sub.received_by_name || 'N/A'}</td>
                    <td>${getStatusBadge(sub.status)}</td>
                    <td>${sub.notes || '-'}</td>
                    <td>
                        <button class="btn btn-sm btn-info" onclick="viewDetails('${sub.id}')">
                            <i class="bi bi-eye"></i>
                        </button>
                        ${sub.status === 'pending' ? `
                            <button class="btn btn-sm btn-success" onclick="approveSubmission('${sub.id}')">
                                <i class="bi bi-check"></i>
                            </button>
                            <button class="btn btn-sm btn-danger" onclick="rejectSubmission('${sub.id}')">
                                <i class="bi bi-x"></i>
                            </button>
                        ` : ''}
                    </td>
                </tr>
            `).join('');
        }
    } catch (error) {
        console.error('Error loading submissions:', error);
        tableBody.innerHTML = `
            <tr>
                <td colspan="7" class="text-center text-danger py-4">
                    <i class="bi bi-exclamation-triangle"></i> Error loading submissions. Please try again.
                </td>
            </tr>
        `;
    } finally {
        spinner.style.display = 'none';
    }
}

// Load statistics
async function loadStatistics() {
    try {
        const today = new Date().toISOString().split('T')[0];
        const response = await fetch(`${API_BASE}/sales/cash-submissions?start_date=${today}&end_date=${today}`);

        if (!response.ok) throw new Error('Failed to load statistics');

        const submissions = await response.json();

        const totalCount = submissions.length;
        const totalAmount = submissions.reduce((sum, sub) => sum + parseFloat(sub.amount), 0);
        const pendingCount = submissions.filter(sub => sub.status === 'pending').length;
        const postedCount = submissions.filter(sub => sub.status === 'posted').length;

        document.getElementById('totalSubmissionsToday').textContent = totalCount;
        document.getElementById('totalAmountToday').textContent = `P ${totalAmount.toFixed(2)}`;
        document.getElementById('pendingCount').textContent = pendingCount;
        document.getElementById('postedCount').textContent = postedCount;
    } catch (error) {
        console.error('Error loading statistics:', error);
    }
}

// Submit cash
async function submitCash() {
    const form = document.getElementById('submitCashForm');

    if (!form.checkValidity()) {
        form.reportValidity();
        return;
    }

    const data = {
        salesperson_id: document.getElementById('salespersonId').value,
        received_by_id: document.getElementById('receivedById').value,
        amount: parseFloat(document.getElementById('amount').value),
        submission_date: document.getElementById('submissionDate').value,
        branch_id: document.getElementById('branchId').value || null,
        notes: document.getElementById('notes').value || null
    };

    try {
        const response = await fetch(`${API_BASE}/sales/cash-submissions`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to submit cash');
        }

        const result = await response.json();

        showAlert('Cash submission created successfully!', 'success');

        // Close modal and reset form
        const modal = bootstrap.Modal.getInstance(document.getElementById('submitCashModal'));
        modal.hide();
        form.reset();

        // Set default date again
        const today = new Date().toISOString().split('T')[0];
        document.getElementById('submissionDate').value = today;

        // Reload data
        loadSubmissions();
        loadStatistics();

    } catch (error) {
        console.error('Error submitting cash:', error);
        showAlert(error.message, 'danger');
    }
}

// Setup denomination calculator
function setupDenominationCalculator() {
    const denominations = document.querySelectorAll('.denomination');
    const coinsInput = document.getElementById('coins');

    denominations.forEach(input => {
        input.addEventListener('input', calculateTotal);
    });

    coinsInput.addEventListener('input', calculateTotal);
}

// Calculate total from denominations
function calculateTotal() {
    let total = 0;

    // Calculate notes
    document.querySelectorAll('.denomination').forEach(input => {
        const count = parseInt(input.value) || 0;
        const value = parseInt(input.dataset.value);
        total += count * value;
    });

    // Add coins
    const coins = parseFloat(document.getElementById('coins').value) || 0;
    total += coins;

    document.getElementById('calculatedTotal').textContent = `P ${total.toFixed(2)}`;
}

// Fill amount from breakdown
function fillAmountFromBreakdown() {
    const totalText = document.getElementById('calculatedTotal').textContent;
    const amount = parseFloat(totalText.replace('P ', ''));
    document.getElementById('amount').value = amount.toFixed(2);
}

// View submission details
async function viewDetails(id) {
    try {
        const response = await fetch(`${API_BASE}/sales/cash-submissions/${id}`);
        if (!response.ok) throw new Error('Failed to load submission details');

        const submission = await response.json();

        const detailsHtml = `
            <div class="row g-3">
                <div class="col-md-6">
                    <strong>Submission ID:</strong><br>
                    <code>${submission.id}</code>
                </div>
                <div class="col-md-6">
                    <strong>Status:</strong><br>
                    ${getStatusBadge(submission.status)}
                </div>
                <div class="col-md-6">
                    <strong>Salesperson:</strong><br>
                    ${submission.salesperson_name || 'Unknown'}
                </div>
                <div class="col-md-6">
                    <strong>Received By:</strong><br>
                    ${submission.received_by_name || 'N/A'}
                </div>
                <div class="col-md-6">
                    <strong>Amount:</strong><br>
                    <span class="amount-display fs-4">P ${parseFloat(submission.amount).toFixed(2)}</span>
                </div>
                <div class="col-md-6">
                    <strong>Submission Date:</strong><br>
                    ${formatDate(submission.submission_date)}
                </div>
                <div class="col-md-12">
                    <strong>Branch:</strong><br>
                    ${submission.branch_id || 'N/A'}
                </div>
                <div class="col-md-12">
                    <strong>Journal Entry ID:</strong><br>
                    ${submission.journal_entry_id ? `<code>${submission.journal_entry_id}</code>` : 'N/A'}
                </div>
                <div class="col-md-12">
                    <strong>Notes:</strong><br>
                    ${submission.notes || 'No notes'}
                </div>
                <div class="col-md-6">
                    <strong>Created:</strong><br>
                    ${formatDateTime(submission.created_at)}
                </div>
                <div class="col-md-6">
                    <strong>Updated:</strong><br>
                    ${formatDateTime(submission.updated_at)}
                </div>
            </div>
        `;

        document.getElementById('submissionDetails').innerHTML = detailsHtml;

        const modal = new bootstrap.Modal(document.getElementById('viewDetailsModal'));
        modal.show();

    } catch (error) {
        console.error('Error loading details:', error);
        showAlert('Failed to load submission details', 'danger');
    }
}

// Apply filters
function applyFilters() {
    loadSubmissions();
}

// Clear filters
function clearFilters() {
    const today = new Date().toISOString().split('T')[0];
    document.getElementById('filterStartDate').value = today;
    document.getElementById('filterEndDate').value = today;
    document.getElementById('filterSalesperson').value = '';
    document.getElementById('filterStatus').value = '';
    loadSubmissions();
}

// Export to Excel
function exportToExcel() {
    showAlert('Excel export feature coming soon!', 'info');
}

// Utility functions
function formatDate(dateString) {
    if (!dateString) return 'N/A';
    const date = new Date(dateString);
    return date.toLocaleDateString('en-GB');
}

function formatDateTime(dateString) {
    if (!dateString) return 'N/A';
    const date = new Date(dateString);
    return date.toLocaleString('en-GB');
}

function getStatusBadge(status) {
    const badges = {
        'pending': '<span class="status-badge status-pending">Pending</span>',
        'posted': '<span class="status-badge status-posted">Posted</span>',
        'rejected': '<span class="status-badge status-rejected">Rejected</span>'
    };
    return badges[status] || status;
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

    // Auto-dismiss after 5 seconds
    setTimeout(() => {
        const alert = document.querySelector('.alert');
        if (alert) {
            alert.remove();
        }
    }, 5000);
}
