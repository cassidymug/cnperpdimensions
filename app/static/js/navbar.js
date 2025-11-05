// Standard CNPERP Bootstrap Navbar System - Clean & Crisp
console.log('🔵 navbar.js loaded - version 20250121-v2');

// Global logout handler - explicitly attach to window object
window.handleLogoutClick = function () {
	console.log('🔴 Logout button clicked');
	// Redirect to logout page
	window.location.href = '/static/logout.html';
};

function createNavbar(currentPage = 'dashboard') {
	// Check user role from localStorage
	const user = JSON.parse(localStorage.getItem('user') || '{}');
	const role = (user.role || '').toLowerCase();

	// POS users should NOT see the navbar - return empty string
	if (role === 'pos_user' || role === 'cashier') {
		console.log('🔒 POS user detected - navbar hidden');
		return '';
	}

	const navbarHtml = `
	<style>
		/* Clean Bootstrap Navbar Styling */
		.cnperp-navbar {
			background-color: #0d6efd !important;
			box-shadow: 0 2px 4px rgba(0,0,0,0.1);
		}
		.cnperp-navbar .navbar-brand {
			font-weight: 600;
			font-size: 1.25rem;
			color: white !important;
		}
		.cnperp-navbar .nav-link {
			color: rgba(255, 255, 255, 0.95) !important;
			font-weight: 500;
			padding: 0.5rem 1rem !important;
		}
		.cnperp-navbar .nav-link:hover {
			color: white !important;
			background-color: rgba(255, 255, 255, 0.1);
			border-radius: 4px;
		}
		.cnperp-navbar .dropdown-menu {
			border: none;
			box-shadow: 0 0.25rem 0.5rem rgba(0, 0, 0, 0.15);
			border-radius: 0.375rem;
		}
		.cnperp-navbar .dropdown-item {
			padding: 0.5rem 1rem;
		}
		.cnperp-navbar .dropdown-item:hover {
			background-color: #f8f9fa;
			color: #0d6efd;
		}
		.cnperp-navbar .dropdown-item i {
			width: 20px;
			margin-right: 0.5rem;
		}
	</style>

	<nav class="navbar navbar-expand-lg navbar-dark cnperp-navbar">
		<div class="container-fluid">
			<a class="navbar-brand" href="/static/index.html">
				<i class="bi bi-building me-2"></i>CNPERP
			</a>

			<button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarMain">
				<span class="navbar-toggler-icon"></span>
			</button>

			<div class="collapse navbar-collapse" id="navbarMain">
				<ul class="navbar-nav me-auto">
					<li class="nav-item">
						<a class="nav-link" href="/static/index.html">
							<i class="bi bi-speedometer2 me-1"></i>Dashboard
						</a>
					</li>

					<li class="nav-item dropdown">
						<a class="nav-link dropdown-toggle" href="#" data-bs-toggle="dropdown">
							<i class="bi bi-cart-check me-1"></i>POS
						</a>
						<ul class="dropdown-menu">
							<li><a class="dropdown-item" href="/static/pos.html"><i class="bi bi-cart-plus"></i>Point of Sale</a></li>
							<li><a class="dropdown-item" href="/static/pos-reconciliation.html"><i class="bi bi-cash-stack"></i>POS Reconciliation</a></li>
						</ul>
					</li>

					<li class="nav-item dropdown">
						<a class="nav-link dropdown-toggle" href="#" data-bs-toggle="dropdown">
							<i class="bi bi-cart me-1"></i>Sales
						</a>
						<ul class="dropdown-menu">
							<li><a class="dropdown-item" href="/static/sales.html"><i class="bi bi-cash-coin"></i>Sales</a></li>
							<li><a class="dropdown-item" href="/static/customers.html"><i class="bi bi-people"></i>Customers</a></li>
							<li><a class="dropdown-item" href="/static/invoices.html"><i class="bi bi-receipt"></i>Invoices</a></li>
							<li><a class="dropdown-item" href="/static/quotations.html"><i class="bi bi-file-text"></i>Quotations</a></li>
							<li><a class="dropdown-item" href="/static/credit-notes.html"><i class="bi bi-file-minus"></i>Credit Notes</a></li>
							<li><hr class="dropdown-divider"></li>
							<li><a class="dropdown-item" href="/static/billing.html"><i class="bi bi-calendar-check"></i>Billing & Recurring</a></li>
							<li><a class="dropdown-item" href="/static/branch-sales.html"><i class="bi bi-graph-up-arrow"></i>Branch Sales</a></li>
							<li><a class="dropdown-item" href="/static/sales-reports.html"><i class="bi bi-graph-up"></i>Sales Reports</a></li>
						</ul>
					</li>

					<li class="nav-item dropdown">
						<a class="nav-link dropdown-toggle" href="#" data-bs-toggle="dropdown">
							<i class="bi bi-box me-1"></i>Inventory
						</a>
						<ul class="dropdown-menu">
							<li><a class="dropdown-item" href="/static/products.html"><i class="bi bi-box-seam"></i>Products</a></li>
							<li><a class="dropdown-item" href="/static/recipes.html"><i class="bi bi-journal-text"></i>Recipes/BOM</a></li>
							<li><a class="dropdown-item" href="/static/inventory-allocation.html"><i class="bi bi-distribution-vertical"></i>Inventory Allocation</a></li>
							<li><a class="dropdown-item" href="/static/uom-management.html"><i class="bi bi-rulers"></i>Units of Measure</a></li>
							<li><hr class="dropdown-divider"></li>
							<li><a class="dropdown-item" href="/static/cogs.html"><i class="bi bi-calculator"></i>COGS Management</a></li>
							<li><a class="dropdown-item" href="/static/inventory-reports.html"><i class="bi bi-graph-up"></i>Inventory Reports</a></li>
							<li><a class="dropdown-item" href="/static/cogs-reports.html"><i class="bi bi-file-bar-graph"></i>COGS Reports</a></li>
						</ul>
					</li>

					<li class="nav-item dropdown">
						<a class="nav-link dropdown-toggle" href="#" data-bs-toggle="dropdown">
							<i class="bi bi-truck me-1"></i>Purchases
						</a>
						<ul class="dropdown-menu">
							<li><a class="dropdown-item" href="/static/purchases.html"><i class="bi bi-truck"></i>Purchases</a></li>
							<li><hr class="dropdown-divider"></li>
							<li><a class="dropdown-item" href="/static/purchase-orders.html"><i class="bi bi-cart-check"></i>Purchase Orders</a></li>
							<li><a class="dropdown-item" href="/static/suppliers.html"><i class="bi bi-building"></i>Suppliers</a></li>
							<li><a class="dropdown-item" href="/static/receipts.html"><i class="bi bi-inbox"></i>Receipts</a></li>
							<li><a class="dropdown-item" href="/static/purchase-payments.html"><i class="bi bi-credit-card"></i>Payments</a></li>
							<li><hr class="dropdown-divider"></li>
							<li><a class="dropdown-item" href="/static/procurement.html"><i class="bi bi-clipboard-check"></i>Procurement</a></li>
							<li><a class="dropdown-item" href="/static/landed-costs.html"><i class="bi bi-ship"></i>Landed Costs</a></li>
							<li><a class="dropdown-item" href="/static/purchase-reports.html"><i class="bi bi-graph-up"></i>Purchase Reports</a></li>
						</ul>
					</li>

					<li class="nav-item dropdown">
						<a class="nav-link dropdown-toggle" href="#" data-bs-toggle="dropdown">
							<i class="bi bi-building me-1"></i>Assets
						</a>
						<ul class="dropdown-menu">
							<li><a class="dropdown-item" href="/static/asset-management.html"><i class="bi bi-buildings"></i>Asset Management</a></li>
							<li><a class="dropdown-item" href="/static/asset.html"><i class="bi bi-building-check"></i>Fixed Assets</a></li>
						</ul>
					</li>

					<li class="nav-item dropdown">
						<a class="nav-link dropdown-toggle" href="#" data-bs-toggle="dropdown">
							<i class="bi bi-bank me-1"></i>Banking
						</a>
						<ul class="dropdown-menu">
							<li><a class="dropdown-item" href="/static/bank-accounts.html"><i class="bi bi-bank"></i>Bank Accounts</a></li>
							<li><a class="dropdown-item" href="/static/bank-transactions.html"><i class="bi bi-receipt-cutoff"></i>Transactions</a></li>
							<li><a class="dropdown-item" href="/static/bank-transfers.html"><i class="bi bi-arrow-left-right"></i>Transfers</a></li>
							<li><a class="dropdown-item" href="/static/bank-reconciliations.html"><i class="bi bi-check2-square"></i>Reconciliations</a></li>
							<li><hr class="dropdown-divider"></li>
							<li><a class="dropdown-item" href="/static/cash-submissions.html"><i class="bi bi-cash-stack"></i>Cash Submissions</a></li>
							<li><a class="dropdown-item" href="/static/float-allocations.html"><i class="bi bi-wallet2"></i>Float Allocations</a></li>
							<li><a class="dropdown-item" href="/static/banking-reports.html"><i class="bi bi-graph-up"></i>Banking Reports</a></li>
							<li><a class="dropdown-item" href="/static/cash-reports.html"><i class="bi bi-file-earmark-text"></i>Cash Reports</a></li>
						</ul>
					</li>

					<li class="nav-item dropdown">
						<a class="nav-link dropdown-toggle" href="#" data-bs-toggle="dropdown">
							<i class="bi bi-calculator me-1"></i>Accounting
						</a>
						<ul class="dropdown-menu">
							<li><a class="dropdown-item" href="/static/accounting-codes.html"><i class="bi bi-diagram-3"></i>Chart of Accounts</a></li>
							<li><a class="dropdown-item" href="/static/journal-entries.html"><i class="bi bi-journal-text"></i>Journal Entries</a></li>
							<li><a class="dropdown-item" href="/static/ledgers.html"><i class="bi bi-book"></i>General Ledger</a></li>
							<li><a class="dropdown-item" href="/static/accounting-dimensions.html"><i class="bi bi-grid-3x3"></i>Accounting Dimensions</a></li>
							<li><hr class="dropdown-divider"></li>
							<li><a class="dropdown-item" href="/static/vat-reports.html"><i class="bi bi-percent"></i>VAT Reports</a></li>
							<li><a class="dropdown-item" href="/static/vat-reconciliations.html"><i class="bi bi-check2-circle"></i>VAT Reconciliations</a></li>
							<li><hr class="dropdown-divider"></li>
							<li><a class="dropdown-item" href="/static/budgeting.html"><i class="bi bi-graph-up-arrow"></i>Budgeting</a></li>
							<li><a class="dropdown-item" href="/static/financial-reports.html"><i class="bi bi-file-earmark-bar-graph"></i>Financial Reports</a></li>
						</ul>
					</li>

					<li class="nav-item dropdown">
						<a class="nav-link dropdown-toggle" href="#" data-bs-toggle="dropdown">
							<i class="bi bi-tools me-1"></i>Manufacturing
						</a>
						<ul class="dropdown-menu">
							<li><a class="dropdown-item" href="/static/manufacturing.html"><i class="bi bi-gear"></i>Production Orders</a></li>
							<li><a class="dropdown-item" href="/static/job-cards.html"><i class="bi bi-card-checklist"></i>Job Cards</a></li>
							<li><a class="dropdown-item" href="/static/recipes.html"><i class="bi bi-journal-text"></i>Recipes/BOM</a></li>
						</ul>
					</li>

					<li class="nav-item dropdown">
						<a class="nav-link dropdown-toggle" href="#" data-bs-toggle="dropdown">
							<i class="bi bi-graph-up me-1"></i>Reports
						</a>
						<ul class="dropdown-menu">
							<li><a class="dropdown-item" href="/static/reports.html"><i class="bi bi-file-earmark-bar-graph"></i>All Reports</a></li>
							<li><a class="dropdown-item" href="/static/financial-reports.html"><i class="bi bi-cash-coin"></i>Financial Reports</a></li>
							<li><a class="dropdown-item" href="/static/management-reports.html"><i class="bi bi-briefcase"></i>Management Reports</a></li>
							<li><hr class="dropdown-divider"></li>
							<li><a class="dropdown-item" href="/static/sales-reports.html"><i class="bi bi-cart"></i>Sales Reports</a></li>
							<li><a class="dropdown-item" href="/static/purchase-reports.html"><i class="bi bi-truck"></i>Purchase Reports</a></li>
							<li><a class="dropdown-item" href="/static/inventory-reports.html"><i class="bi bi-box"></i>Inventory Reports</a></li>
							<li><a class="dropdown-item" href="/static/customer-reports.html"><i class="bi bi-people"></i>Customer Reports</a></li>
							<li><a class="dropdown-item" href="/static/invoice-reports.html"><i class="bi bi-receipt"></i>Invoice Reports</a></li>
							<li><hr class="dropdown-divider"></li>
							<li><a class="dropdown-item" href="/static/business-intelligence.html"><i class="bi bi-bar-chart"></i>Business Intelligence</a></li>
						</ul>
					</li>

					<li class="nav-item dropdown">
						<a class="nav-link dropdown-toggle" href="#" data-bs-toggle="dropdown">
							<i class="bi bi-gear-fill me-1"></i>Settings
						</a>
						<ul class="dropdown-menu">
							<li><a class="dropdown-item" href="/static/settings.html"><i class="bi bi-sliders"></i>System Settings</a></li>
							<li><a class="dropdown-item" href="/static/admin-panel.html"><i class="bi bi-shield-lock"></i>Admin Panel</a></li>
							<li><a class="dropdown-item" href="/static/logs-viewer.html"><i class="bi bi-file-text"></i>System Logs <span class="badge bg-success badge-sm ms-1">New</span></a></li>
							<li><hr class="dropdown-divider"></li>
							<li><a class="dropdown-item" href="/static/users.html"><i class="bi bi-person"></i>Users</a></li>
							<li><a class="dropdown-item" href="/static/branches.html"><i class="bi bi-building"></i>Branches</a></li>
							<li><a class="dropdown-item" href="/static/user-permissions.html"><i class="bi bi-key"></i>User Permissions</a></li>
							<li><a class="dropdown-item" href="/static/role-management.html"><i class="bi bi-person-badge"></i>Role Management</a></li>
							<li><a class="dropdown-item" href="/static/permission-matrix.html"><i class="bi bi-grid"></i>Permission Matrix</a></li>
							<li><hr class="dropdown-divider"></li>
							<li><a class="dropdown-item" href="/static/invoice-customization.html"><i class="bi bi-brush"></i>Invoice Customization</a></li>
							<li><a class="dropdown-item" href="/static/invoice-designer.html"><i class="bi bi-palette"></i>Invoice Designer</a></li>
							<li><a class="dropdown-item" href="/static/invoice-printer-settings.html"><i class="bi bi-printer"></i>Print Settings</a></li>
							<li><hr class="dropdown-divider"></li>
							<li><a class="dropdown-item" href="/static/backup-management.html"><i class="bi bi-cloud-upload"></i>Backup Management</a></li>
							<li><a class="dropdown-item" href="/static/excel-templates.html"><i class="bi bi-file-excel"></i>Excel Templates</a></li>
							<li><hr class="dropdown-divider"></li>
							<li><a class="dropdown-item" href="/static/help-center.html"><i class="bi bi-question-circle"></i>Help Center</a></li>
						</ul>
					</li>
				</ul>

				<ul class="navbar-nav ms-auto">
					<li class="nav-item dropdown">
						<a class="nav-link dropdown-toggle" href="#" data-bs-toggle="dropdown">
							<i class="bi bi-person-circle me-1"></i>User
						</a>
						<ul class="dropdown-menu dropdown-menu-end">
							<li><a class="dropdown-item" href="#"><i class="bi bi-person"></i>Profile</a></li>
							<li><a class="dropdown-item" href="#"><i class="bi bi-gear"></i>Settings</a></li>
							<li><hr class="dropdown-divider"></li>
							<li><a class="dropdown-item" href="#" onclick="handleLogoutClick(); return false;"><i class="bi bi-box-arrow-right"></i>Logout</a></li>
						</ul>
					</li>
				</ul>
			</div>
		</div>
	</nav>
	`;

	return navbarHtml;
}

// Load navbar on page load
document.addEventListener('DOMContentLoaded', function () {
	// Try both navbar-container (new standard) and navbar-placeholder (legacy)
	const navbarContainer = document.getElementById('navbar-container') || document.getElementById('navbar-placeholder');
	if (navbarContainer) {
		navbarContainer.innerHTML = createNavbar();
		console.log('✅ Clean Bootstrap navbar loaded successfully');

		// Add logout handler after navbar is loaded
		setTimeout(() => {
			const logoutLinks = document.querySelectorAll('a[href="/static/logout.html"]');
			logoutLinks.forEach(link => {
				link.addEventListener('click', function (e) {
					e.preventDefault();
					console.log('🔴 Logout clicked - redirecting...');
					window.location.href = '/static/logout.html';
				});
			});
		}, 100);
	} else {
		console.error('❌ No navbar container found! Looking for #navbar-container or #navbar-placeholder');
	}
});
