// Float Allocations JavaScript
const API_BASE = 'http://localhost:8010/api/v1';

// Initialize on page load
document.addEventListener('DOMContentLoaded', function () {
    console.log('Float Allocations page loaded');

    // Set today's date as default
    const today = new Date().toISOString().split('T')[0];
    document.getElementById('allocationDate').value = today;
    document.getElementById('returnDate').value = today;
    document.getElementById('filterStartDate').value = today;
    document.getElementById('filterEndDate').value = today;

    // Load initial data
    loadUsers();
    loadBranches();
    loadAllocations();
    loadStatistics();

    // Setup variance calculator
    setupVarianceCalculator();

    // Refresh data every 30 seconds
    setInterval(() => {
        loadAllocations();
        loadStatistics();
    }, 30000);
});

// Load users for dropdowns
async function loadUsers() {
    try {
        const response = await fetch(`${API_BASE}/users/`);
        if (!response.ok) throw new Error('Failed to load users');

        const users = await response.json();

        const cashierSelect = document.getElementById('cashierId');
        const allocatedBySelect = document.getElementById('allocatedById');
        const filterSelect = document.getElementById('filterCashier');

        cashierSelect.innerHTML = '<option value="">Select cashier...</option>';
        allocatedBySelect.innerHTML = '<option value="">Select manager...</option>';
        filterSelect.innerHTML = '<option value="">All Cashiers</option>';

        users.forEach(user => {
            const name = `${user.first_name || ''} ${user.last_name || ''}`.trim() || user.username;
            const option = new Option(name, user.id);

            cashierSelect.add(option.cloneNode(true));
            allocatedBySelect.add(option.cloneNode(true));
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

        if (branches.length === 1) {
            branchSelect.value = branches[0].id;
        }
    } catch (error) {
        console.error('Error loading branches:', error);
    }
}

// Load allocations with filters
async function loadAllocations() {
    const spinner = document.getElementById('loadingSpinner');
    const tableBody = document.getElementById('allocationsTableBody');

    spinner.style.display = 'block';

    try {
        const params = new URLSearchParams();

        const startDate = document.getElementById('filterStartDate').value;
        const endDate = document.getElementById('filterEndDate').value;
        const cashierId = document.getElementById('filterCashier').value;
        const status = document.getElementById('filterStatus').value;

        if (startDate) params.append('start_date', startDate);
        if (endDate) params.append('end_date', endDate);
        if (cashierId) params.append('cashier_id', cashierId);
        if (status) params.append('status_filter', status);

        const response = await fetch(`${API_BASE}/sales/float-allocations?${params}`);
        if (!response.ok) throw new Error('Failed to load allocations');

        const allocations = await response.json();

        if (allocations.length === 0) {
            tableBody.innerHTML = `
                <tr>
                    <td colspan="9" class="text-center text-muted py-4">
                        No float allocations found for the selected filters.
                    </td>
                </tr>
            `;
        } else {
            tableBody.innerHTML = allocations.map(alloc => {
                const variance = alloc.returned_amount ?
                    parseFloat(alloc.returned_amount) - parseFloat(alloc.amount) : 0;
                const varianceClass = variance < 0 ? 'variance-negative' :
                    variance > 0 ? 'variance-positive' : '';

                return `
                    <tr>
                        <td>${formatDate(alloc.allocation_date)}</td>
                        <td>${alloc.cashier_name || 'Unknown'}</td>
                        <td class="amount-display">P ${parseFloat(alloc.amount).toFixed(2)}</td>
                        <td>${alloc.allocated_by_name || 'N/A'}</td>
                        <td>${alloc.return_date ? formatDate(alloc.return_date) : '-'}</td>
                        <td class="amount-display">${alloc.returned_amount ? 'P ' + parseFloat(alloc.returned_amount).toFixed(2) : '-'}</td>
                        <td class="${varianceClass}">${variance !== 0 ? 'P ' + variance.toFixed(2) : '-'}</td>
                        <td>${getStatusBadge(alloc.status)}</td>
                        <td>
                            <button class="btn btn-sm btn-info" onclick="viewDetails('${alloc.id}')">
                                <i class="bi bi-eye"></i>
                            </button>
                            ${alloc.status === 'allocated' ? `
                                <button class="btn btn-sm btn-primary" onclick="showReturnModal('${alloc.id}', ${alloc.amount})">
                                    <i class="bi bi-arrow-return-left"></i>
                                </button>
                            ` : ''}
                        </td>
                    </tr>
                `;
            }).join('');
        }
    } catch (error) {
        console.error('Error loading allocations:', error);
        tableBody.innerHTML = `
            <tr>
                <td colspan="9" class="text-center text-danger py-4">
                    <i class="bi bi-exclamation-triangle"></i> Error loading allocations. Please try again.
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
        const response = await fetch(`${API_BASE}/sales/float-allocations?start_date=${today}&end_date=${today}`);

        if (!response.ok) throw new Error('Failed to load statistics');

        const allocations = await response.json();

        const totalCount = allocations.length;
        const totalAmount = allocations.reduce((sum, alloc) => sum + parseFloat(alloc.amount), 0);
        const activeCount = allocations.filter(alloc => alloc.status === 'allocated').length;
        const returnedCount = allocations.filter(alloc => alloc.status === 'returned').length;

        document.getElementById('totalAllocationsToday').textContent = totalCount;
        document.getElementById('totalAllocatedToday').textContent = `P ${totalAmount.toFixed(2)}`;
        document.getElementById('activeFloats').textContent = activeCount;
        document.getElementById('returnedToday').textContent = returnedCount;
    } catch (error) {
        console.error('Error loading statistics:', error);
    }
}

// Allocate float
async function allocateFloat() {
    const form = document.getElementById('allocateFloatForm');

    if (!form.checkValidity()) {
        form.reportValidity();
        return;
    }

    const data = {
        cashier_id: document.getElementById('cashierId').value,
        allocated_by_id: document.getElementById('allocatedById').value,
        amount: parseFloat(document.getElementById('floatAmount').value),
        allocation_date: document.getElementById('allocationDate').value,
        expected_return_date: document.getElementById('expectedReturnDate').value || null,
        branch_id: document.getElementById('branchId').value || null,
        purpose: document.getElementById('purpose').value || null
    };

    try {
        const response = await fetch(`${API_BASE}/sales/float-allocations`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to allocate float');
        }

        const result = await response.json();

        showAlert('Float allocated successfully!', 'success');

        // Close modal and reset form
        const modal = bootstrap.Modal.getInstance(document.getElementById('allocateFloatModal'));
        modal.hide();
        form.reset();

        // Set default date again
        const today = new Date().toISOString().split('T')[0];
        document.getElementById('allocationDate').value = today;

        // Reload data
        loadAllocations();
        loadStatistics();

    } catch (error) {
        console.error('Error allocating float:', error);
        showAlert(error.message, 'danger');
    }
}

// Show return modal
function showReturnModal(allocationId, amount) {
    document.getElementById('returnAllocationId').value = allocationId;
    document.getElementById('originalAmount').textContent = `P ${parseFloat(amount).toFixed(2)}`;
    document.getElementById('returnedAmount').value = '';
    document.getElementById('varianceDisplay').textContent = 'P 0.00';

    const modal = new bootstrap.Modal(document.getElementById('returnFloatModal'));
    modal.show();
}

// Setup variance calculator
function setupVarianceCalculator() {
    const returnedAmountInput = document.getElementById('returnedAmount');

    returnedAmountInput.addEventListener('input', function () {
        const originalText = document.getElementById('originalAmount').textContent;
        const original = parseFloat(originalText.replace('P ', ''));
        const returned = parseFloat(this.value) || 0;
        const variance = returned - original;

        const varianceDisplay = document.getElementById('varianceDisplay');
        varianceDisplay.textContent = `P ${variance.toFixed(2)}`;

        if (variance < 0) {
            varianceDisplay.className = 'form-control-plaintext variance-negative';
        } else if (variance > 0) {
            varianceDisplay.className = 'form-control-plaintext variance-positive';
        } else {
            varianceDisplay.className = 'form-control-plaintext';
        }
    });
}

// Submit return
async function submitReturn() {
    const allocationId = document.getElementById('returnAllocationId').value;
    const returnedAmount = parseFloat(document.getElementById('returnedAmount').value);
    const returnDate = document.getElementById('returnDate').value;
    const notes = document.getElementById('returnNotes').value;

    if (!returnedAmount || !returnDate) {
        showAlert('Please fill in all required fields', 'warning');
        return;
    }

    const data = {
        returned_amount: returnedAmount,
        return_date: returnDate,
        notes: notes || null
    };

    try {
        const response = await fetch(`${API_BASE}/sales/float-allocations/${allocationId}/return`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to return float');
        }

        showAlert('Float returned successfully!', 'success');

        const modal = bootstrap.Modal.getInstance(document.getElementById('returnFloatModal'));
        modal.hide();

        loadAllocations();
        loadStatistics();

    } catch (error) {
        console.error('Error returning float:', error);
        showAlert(error.message, 'danger');
    }
}

// View allocation details
async function viewDetails(id) {
    try {
        const response = await fetch(`${API_BASE}/sales/float-allocations/${id}`);
        if (!response.ok) throw new Error('Failed to load allocation details');

        const allocation = await response.json();

        const variance = allocation.returned_amount ?
            parseFloat(allocation.returned_amount) - parseFloat(allocation.amount) : 0;

        const detailsHtml = `
            <div class="row g-3">
                <div class="col-md-6">
                    <strong>Allocation ID:</strong><br>
                    <code>${allocation.id}</code>
                </div>
                <div class="col-md-6">
                    <strong>Status:</strong><br>
                    ${getStatusBadge(allocation.status)}
                </div>
                <div class="col-md-6">
                    <strong>Cashier:</strong><br>
                    ${allocation.cashier_name || 'Unknown'}
                </div>
                <div class="col-md-6">
                    <strong>Allocated By:</strong><br>
                    ${allocation.allocated_by_name || 'N/A'}
                </div>
                <div class="col-md-6">
                    <strong>Float Amount:</strong><br>
                    <span class="amount-display fs-4">P ${parseFloat(allocation.amount).toFixed(2)}</span>
                </div>
                <div class="col-md-6">
                    <strong>Allocation Date:</strong><br>
                    ${formatDate(allocation.allocation_date)}
                </div>
                <div class="col-md-6">
                    <strong>Expected Return:</strong><br>
                    ${allocation.expected_return_date ? formatDate(allocation.expected_return_date) : 'N/A'}
                </div>
                <div class="col-md-6">
                    <strong>Actual Return Date:</strong><br>
                    ${allocation.return_date ? formatDate(allocation.return_date) : 'Not returned'}
                </div>
                ${allocation.returned_amount ? `
                <div class="col-md-6">
                    <strong>Returned Amount:</strong><br>
                    <span class="amount-display fs-4">P ${parseFloat(allocation.returned_amount).toFixed(2)}</span>
                </div>
                <div class="col-md-6">
                    <strong>Variance:</strong><br>
                    <span class="fs-4 ${variance < 0 ? 'variance-negative' : variance > 0 ? 'variance-positive' : ''}">
                        P ${variance.toFixed(2)}
                    </span>
                </div>
                ` : ''}
                <div class="col-md-12">
                    <strong>Purpose:</strong><br>
                    ${allocation.purpose || 'N/A'}
                </div>
                <div class="col-md-12">
                    <strong>Branch:</strong><br>
                    ${allocation.branch_id || 'N/A'}
                </div>
                <div class="col-md-12">
                    <strong>Notes:</strong><br>
                    ${allocation.notes || 'No notes'}
                </div>
                <div class="col-md-6">
                    <strong>Created:</strong><br>
                    ${formatDateTime(allocation.created_at)}
                </div>
                <div class="col-md-6">
                    <strong>Updated:</strong><br>
                    ${formatDateTime(allocation.updated_at)}
                </div>
            </div>
        `;

        document.getElementById('allocationDetails').innerHTML = detailsHtml;

        const modal = new bootstrap.Modal(document.getElementById('viewDetailsModal'));
        modal.show();

    } catch (error) {
        console.error('Error loading details:', error);
        showAlert('Failed to load allocation details', 'danger');
    }
}

// Apply filters
function applyFilters() {
    loadAllocations();
}

// Clear filters
function clearFilters() {
    const today = new Date().toISOString().split('T')[0];
    document.getElementById('filterStartDate').value = today;
    document.getElementById('filterEndDate').value = today;
    document.getElementById('filterCashier').value = '';
    document.getElementById('filterStatus').value = '';
    loadAllocations();
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
        'allocated': '<span class="status-badge status-allocated">Allocated</span>',
        'returned': '<span class="status-badge status-returned">Returned</span>',
        'variance': '<span class="status-badge status-variance">Variance</span>'
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

    setTimeout(() => {
        const alert = document.querySelector('.alert');
        if (alert) {
            alert.remove();
        }
    }, 5000);
}
