// CNPERP ERP System - Standardized Navbar Component
// This file provides a consistent, clean navigation bar across all pages
// Includes offline-friendly styling

// Add offline-friendly CSS
function addOfflineStyles() {
	if (!document.getElementById('offline-navbar-styles')) {
		const style = document.createElement('style');
		style.id = 'offline-navbar-styles';
		style.textContent = `
			/* Offline-friendly navbar styles */
			.navbar {
				background-color: #0d6efd !important;
				padding: 0.5rem 1rem;
				box-shadow: 0 2px 4px rgba(0,0,0,0.1);
			}
			.navbar-brand {
				color: white !important;
				font-weight: bold;
				text-decoration: none;
				font-size: 1.25rem;
			}
			.navbar-nav .nav-link {
				color: rgba(255,255,255,0.8) !important;
				padding: 0.5rem 1rem;
				text-decoration: none;
				transition: color 0.2s;
			}
			.navbar-nav .nav-link:hover {
				color: white !important;
			}
			.navbar-nav .nav-link.active {
				color: white !important;
				font-weight: 600;
			}
			.navbar-toggler {
				border: 1px solid rgba(255,255,255,0.5);
				padding: 0.25rem 0.5rem;
			}
			.navbar-toggler-icon {
				background-image: url("data:image/svg+xml,%3csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 30 30'%3e%3cpath stroke='rgba%28255, 255, 255, 0.8%29' stroke-linecap='round' stroke-miterlimit='10' stroke-width='2' d='M4 7h22M4 15h22M4 23h22'/%3e%3c/svg%3e");
			}
			.dropdown-menu {
				background-color: white;
				border: 1px solid #dee2e6;
				border-radius: 0.375rem;
				box-shadow: 0 0.5rem 1rem rgba(0,0,0,0.15);
				padding: 0.5rem 0;
				margin: 0;
				list-style: none;
			}
			.dropdown-item {
				color: #212529;
				padding: 0.5rem 1rem;
				text-decoration: none;
				display: block;
			}
			.dropdown-item:hover {
				background-color: #f8f9fa;
				color: #212529;
			}
			.dropdown-divider {
				border-top: 1px solid #dee2e6;
				margin: 0.5rem 0;
			}
			/* Scrollable dropdown styles */
			.dropdown-menu.scrollable-dropdown {
				max-height: 500px;
				overflow-y: auto;
				width: 350px;
			}
			.dropdown-menu.scrollable-dropdown .dropdown-header {
				background-color: #f8f9fa;
				border-bottom: 1px solid #dee2e6;
				font-weight: 600;
				position: sticky;
				top: 0;
				z-index: 1020;
				padding: 0.5rem 1rem;
				margin: 0;
			}
			.dropdown-menu.scrollable-dropdown .dropdown-item {
				white-space: nowrap;
				padding: 0.5rem 1rem;
			}
			.dropdown-menu.scrollable-dropdown .dropdown-item i,
			.dropdown-menu.scrollable-dropdown .dropdown-item span {
				width: 16px;
				text-align: center;
			}
			/* Dark theme for scrollable dropdown */
			body[data-theme="dark"] .dropdown-menu.scrollable-dropdown {
				background-color: #343a40;
				border-color: #495057;
			}
			body[data-theme="dark"] .dropdown-menu.scrollable-dropdown .dropdown-header {
				background-color: #495057;
				border-bottom-color: #6c757d;
				color: #ffffff;
			}
			body[data-theme="dark"] .dropdown-menu.scrollable-dropdown .dropdown-item {
				color: #ffffff;
			}
			body[data-theme="dark"] .dropdown-menu.scrollable-dropdown .dropdown-item:hover {
				background-color: #495057;
				color: #ffffff;
			}
			/* Basic icon fallbacks */
			.bi {
				display: inline-block;
				width: 1em;
				height: 1em;
				vertical-align: -0.125em;
			}
			.bi-building::before { content: "🏢"; }
			.bi-speedometer2::before { content: "📊"; }
			.bi-calculator::before { content: "🧮"; }
			.bi-file-earmark-text::before { content: "📄"; }
			.bi-cash-stack::before { content: "💰"; }
			.bi-box-seam::before { content: "📦"; }
			.bi-clipboard-check::before { content: "📋"; }
			.bi-cart::before { content: "🛒"; }
			.bi-truck::before { content: "🚚"; }
			.bi-bank::before { content: "🏦"; }
			.bi-percent::before { content: "%"; }
			.bi-hdd-stack::before { content: "💾"; }
			.bi-gear::before { content: "⚙️"; }
			.bi-person-circle::before { content: "👤"; }
		`;
		document.head.appendChild(style);
	}
}

function createNavbar(currentPage = 'dashboard') {
	// Add offline styles
	addOfflineStyles();

	return `
	<nav class="navbar navbar-expand-lg">
		<div class="container-fluid">
			<a class="navbar-brand" href="/static/index.html">
				<span class="bi bi-building"></span> CNPERP ERP
			</a>

			<button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarContent">
				<span class="navbar-toggler-icon"></span>
			</button>

			<div class="collapse navbar-collapse" id="navbarContent">
				<ul class="navbar-nav me-auto">
					<li class="nav-item">
						<a class="nav-link ${currentPage === 'dashboard' ? 'active' : ''}" href="/static/index.html">
							<span class="bi bi-speedometer2"></span> Dashboard
						</a>
					</li>
					<li class="nav-item dropdown">
						<a class="nav-link dropdown-toggle ${currentPage === 'accounting' ? 'active' : ''}" href="#" role="button" data-bs-toggle="dropdown">
							<span class="bi bi-calculator"></span> Accounting
						</a>
						<ul class="dropdown-menu">
							<li><a class="dropdown-item" href="/static/chart-of-accounts.html">Chart of Accounts</a></li>
							<li><a class="dropdown-item" href="/static/accounting-codes.html">Accounting Codes</a></li>
							<li><a class="dropdown-item" href="/static/journal-entries.html">Journal Entries</a></li>
							<li><a class="dropdown-item" href="/static/ledgers.html">Ledgers</a></li>
							<li><hr class="dropdown-divider"></li>
							<li><a class="dropdown-item" href="/static/permission-matrix.html">Permission Matrix</a></li>
						</ul>
					</li>
					<li class="nav-item dropdown">
						<a class="nav-link dropdown-toggle ${currentPage === 'reports' ? 'active' : ''}" href="#" role="button" data-bs-toggle="dropdown">
							<span class="bi bi-file-earmark-text"></span> Reports
						</a>
						<ul class="dropdown-menu scrollable-dropdown">
							<!-- Financial Reports -->
							<li><h6 class="dropdown-header">Financial Reports</h6></li>
							<li><a class="dropdown-item" href="/static/reports.html">
								<span class="bi bi-chart-bar me-2"></span>Reports Center
							</a></li>
							<li><a class="dropdown-item" href="/static/financial-reports.html">
								<span class="bi bi-calculator me-2"></span>Financial Statements
							</a></li>
							<li><a class="dropdown-item" href="/static/reports.html#trial-balance">
								<span class="bi bi-list-task me-2"></span>Trial Balance
							</a></li>
							<li><a class="dropdown-item" href="/static/reports.html#balance-sheet">
								<span class="bi bi-pie-chart me-2"></span>Balance Sheet
							</a></li>
							<li><a class="dropdown-item" href="/static/reports.html#debtors-aging">
								<span class="bi bi-people me-2"></span>Debtors Aging
							</a></li>
							<li><a class="dropdown-item" href="/static/reports.html#creditors-aging">
								<span class="bi bi-building me-2"></span>Creditors Aging
							</a></li>

							<li><hr class="dropdown-divider"></li>

							<!-- Sales Reports -->
							<li><h6 class="dropdown-header">Sales Reports</h6></li>
							<li><a class="dropdown-item" href="/static/sales-reports.html">
								<span class="bi bi-cart me-2"></span>Sales Analytics
							</a></li>
							<li><a class="dropdown-item" href="/static/sales-reports.html#daily">
								<span class="bi bi-calendar-day me-2"></span>Daily Sales
							</a></li>
							<li><a class="dropdown-item" href="/static/sales-reports.html#monthly">
								<span class="bi bi-calendar-month me-2"></span>Monthly Sales
							</a></li>
							<li><a class="dropdown-item" href="/static/sales-reports.html#customers">
								<span class="bi bi-person-badge me-2"></span>Customer Analysis
							</a></li>
							<li><a class="dropdown-item" href="/static/customer-reports.html">
								<span class="bi bi-people-fill me-2"></span>Customer Reports
							</a></li>
							<li><a class="dropdown-item" href="/static/invoice-reports.html">
								<span class="bi bi-receipt me-2"></span>Invoice Reports
							</a></li>

							<li><hr class="dropdown-divider"></li>

							<!-- Inventory Reports -->
							<li><h6 class="dropdown-header">Inventory Reports</h6></li>
							<li><a class="dropdown-item" href="/static/inventory-reports.html">
								<span class="bi bi-box-seam me-2"></span>Inventory Analytics
							</a></li>
							<li><a class="dropdown-item" href="/static/inventory-reports.html#stock">
								<span class="bi bi-boxes me-2"></span>Stock Levels
							</a></li>
							<li><a class="dropdown-item" href="/static/inventory-reports.html#valuation">
								<span class="bi bi-currency-dollar me-2"></span>Stock Valuation
							</a></li>
							<li><a class="dropdown-item" href="/static/inventory-reports.html#movement">
								<span class="bi bi-arrow-left-right me-2"></span>Stock Movement
							</a></li>
							<li><a class="dropdown-item" href="/static/purchase-reports.html">
								<span class="bi bi-truck me-2"></span>Purchase Reports
							</a></li>
							<li><a class="dropdown-item" href="/static/supplier-reports.html">
								<span class="bi bi-building me-2"></span>Supplier Reports
							</a></li>

							<li><hr class="dropdown-divider"></li>

							<!-- Banking Reports -->
							<li><h6 class="dropdown-header">Banking Reports</h6></li>
							<li><a class="dropdown-item" href="/static/banking-reports.html#cashflow">
								<span class="bi bi-cash-stack me-2"></span>Cash Flow
							</a></li>
							<li><a class="dropdown-item" href="/static/banking-reports.html#reconciliation">
								<span class="bi bi-check2-square me-2"></span>Bank Reconciliation
							</a></li>
							<li><a class="dropdown-item" href="/static/bank-transaction-reports.html">
								<span class="bi bi-credit-card me-2"></span>Transaction Reports
							</a></li>
							<li><a class="dropdown-item" href="/static/bank-transfer-reports.html">
								<span class="bi bi-arrow-left-right me-2"></span>Transfer Reports
							</a></li>

							<li><hr class="dropdown-divider"></li>

							<!-- Tax Reports -->
							<li><h6 class="dropdown-header">Tax Reports</h6></li>
							<li><a class="dropdown-item" href="/static/vat-reconciliations.html">
								<span class="bi bi-receipt me-2"></span>VAT Returns
							</a></li>
							<li><a class="dropdown-item" href="/static/vat-reports.html">
								<span class="bi bi-percent me-2"></span>VAT Reports
							</a></li>
							<li><a class="dropdown-item" href="/static/tax-reports.html">
								<span class="bi bi-calculator me-2"></span>Tax Calculations
							</a></li>

							<li><hr class="dropdown-divider"></li>

							<!-- Budget Reports -->
							<li><h6 class="dropdown-header">Budget Reports</h6></li>
							<li><a class="dropdown-item" href="/static/budget-reports.html">
								<span class="bi bi-cash-stack me-2"></span>Budget Analysis
							</a></li>
							<li><a class="dropdown-item" href="/static/budget-reports.html#variance">
								<span class="bi bi-graph-up me-2"></span>Budget Variance
							</a></li>
							<li><a class="dropdown-item" href="/static/budget-reports.html#forecast">
								<span class="bi bi-calendar-range me-2"></span>Budget Forecast
							</a></li>

							<li><hr class="dropdown-divider"></li>

							<!-- Management Reports -->
							<li><h6 class="dropdown-header">Management Reports</h6></li>
							<li><a class="dropdown-item" href="/static/financial-reports.html#profit-loss">
								<span class="bi bi-graph-up me-2"></span>Profit & Loss
							</a></li>
							<li><a class="dropdown-item" href="/static/management-reports.html">
								<span class="bi bi-clipboard-data me-2"></span>Management Dashboard
							</a></li>
							<li><a class="dropdown-item" href="/static/kpi-reports.html">
								<span class="bi bi-speedometer2 me-2"></span>KPI Reports
							</a></li>
							<li><a class="dropdown-item" href="/static/performance-reports.html">
								<span class="bi bi-trophy me-2"></span>Performance Reports
							</a></li>
						</ul>
					</li>
					<li class="nav-item">
						<a class="nav-link ${currentPage === 'budgeting' ? 'active' : ''}" href="/static/budgeting.html">
							<span class="bi bi-cash-stack"></span> Budgeting
						</a>
					</li>
					<li class="nav-item dropdown">
						<a class="nav-link dropdown-toggle ${currentPage === 'inventory' ? 'active' : ''}" href="#" role="button" data-bs-toggle="dropdown">
							<span class="bi bi-box-seam"></span> Inventory
						</a>
						<ul class="dropdown-menu">
							<li><a class="dropdown-item" href="/static/products.html">Products</a></li>
							<li><a class="dropdown-item" href="/static/purchases.html">Purchases</a></li>
							<li><a class="dropdown-item" href="/static/purchase-orders.html">Purchase Orders</a></li>
							<li><a class="dropdown-item" href="/static/suppliers.html">Suppliers</a></li>
						</ul>
					</li>
					<li class="nav-item">
						<a class="nav-link ${currentPage === 'procurement' ? 'active' : ''}" href="/static/procurement.html">
							<span class="bi bi-clipboard-check"></span> Procurement
						</a>
					</li>
					<li class="nav-item dropdown">
						<a class="nav-link dropdown-toggle ${currentPage === 'sales' ? 'active' : ''}" href="#" role="button" data-bs-toggle="dropdown">
							<span class="bi bi-cart"></span> Sales
						</a>
						<ul class="dropdown-menu">
							<li><a class="dropdown-item" href="/static/pos.html">POS</a></li>
							<li><a class="dropdown-item" href="/static/sales.html">Sales</a></li>
							<li><a class="dropdown-item" href="/static/customers.html">Customers</a></li>
							<li><a class="dropdown-item" href="/static/invoices.html">Invoices</a></li>
							<li><a class="dropdown-item" href="/static/billing.html"><span class="bi bi-calendar-check me-2"></span>Billing & Recurring</a></li>
							<li><hr class="dropdown-divider"></li>
							<li><a class="dropdown-item" href="/static/sales-reports.html">Sales Reports</a></li>
							<li><a class="dropdown-item" href="/static/sales-analytics.html">Sales Analytics</a></li>
							<li><a class="dropdown-item" href="/static/customer-reports.html">Customer Reports</a></li>
							<li><a class="dropdown-item" href="/static/invoice-reports.html">Invoice Reports</a></li>
						</ul>
					</li>
					<li class="nav-item">
						<a class="nav-link ${currentPage === 'purchases' ? 'active' : ''}" href="/static/purchases.html">
							<span class="bi bi-truck"></span> Purchases
						</a>
					</li>
					<li class="nav-item">
						<a class="nav-link ${currentPage === 'banking' ? 'active' : ''}" href="/static/bank-accounts.html">
							<span class="bi bi-bank"></span> Banking
						</a>
					</li>
					<li class="nav-item">
						<a class="nav-link ${currentPage === 'tax' ? 'active' : ''}" href="/static/vat-reports.html">
							<span class="bi bi-percent"></span> Tax
						</a>
					</li>
					<li class="nav-item">
						<a class="nav-link ${currentPage === 'assets' ? 'active' : ''}" href="/static/asset-management.html">
							<span class="bi bi-hdd-stack"></span> Assets
						</a>
					</li>
					<li class="nav-item">
						<a class="nav-link ${currentPage === 'setup' ? 'active' : ''}" href="/static/settings.html">
							<span class="bi bi-gear"></span> Setup
						</a>
					</li>
				</ul>

				<ul class="navbar-nav">
					<li class="nav-item">
						<div class="nav-link d-flex align-items-center">
							<span class="bi bi-person-circle me-2"></span>
							<div class="d-flex flex-column">
								<small class="text-white-50" style="font-size: 0.75rem;">Logged in as</small>
								<span id="current-user-display" class="text-white fw-bold" style="font-size: 0.9rem;">Loading...</span>
								<small id="current-branch-display" class="text-white-50" style="font-size: 0.7rem;">Branch: Loading...</small>
							</div>
						</div>
					</li>
					<li class="nav-item dropdown">
						<a class="nav-link dropdown-toggle" href="#" role="button" data-bs-toggle="dropdown">
							<span class="bi bi-gear"></span>
						</a>
						<ul class="dropdown-menu dropdown-menu-end">
							<li><a class="dropdown-item" href="/static/admin-panel.html">Admin Panel</a></li>
							<li><a class="dropdown-item" href="/static/users.html">Users</a></li>
							<li><a class="dropdown-item" href="/static/settings.html">Settings</a></li>
							<li><a class="dropdown-item" href="/static/logs-viewer.html"><i class="bi bi-file-text me-2"></i>System Logs <span class="badge bg-success badge-sm ms-1">New</span></a></li>
							<li><a class="dropdown-item" href="/static/backup-management.html">Backup Management</a></li>
							<li><hr class="dropdown-divider"></li>
							<li><a class="dropdown-item" href="#" onclick="logout()">Logout</a></li>
						</ul>
					</li>
				</ul>
			</div>
		</div>
	</nav>
	`;
}

// Function to update user display in navbar
function updateUserDisplay() {
	const userDisplay = document.getElementById('current-user-display');
	const branchDisplay = document.getElementById('current-branch-display');

	if (userDisplay && branchDisplay) {
		if (window.auth && auth.isAuthenticated()) {
			const user = auth.getUser();
			if (user) {
				// Display username
				const username = user.username || 'Unknown User';
				userDisplay.textContent = username;

				// Display branch information
				const branchCode = user.branch_code || 'No Branch';
				branchDisplay.textContent = `Branch: ${branchCode}`;
			} else {
				userDisplay.textContent = 'Not logged in';
				branchDisplay.textContent = 'Branch: N/A';
			}
		} else {
			userDisplay.textContent = 'Not logged in';
			branchDisplay.textContent = 'Branch: N/A';
		}
	}
}

// Function to initialize navbar on any page
function initializeNavbar(currentPage = 'dashboard') {
	const navbarContainer = document.getElementById('navbar-container');
	if (navbarContainer) {
		navbarContainer.innerHTML = createNavbar(currentPage);
		// Update user display after navbar is created
		setTimeout(updateUserDisplay, 100);
	}
}

// Function to handle logout
function logout() {
	// Delegate to enhanced global logout (with custom confirm) if available
	if (typeof window.navbarLoader !== 'undefined' && window.navbarLoader.handleLogout) {
		window.navbarLoader.handleLogout();
		return;
	}
	if (typeof window.logout === 'function' && window.logout !== logout) {
		// Another logout implementation exists
		window.logout();
		return;
	}
	// Fallback: simple immediate redirect clearing basic tokens
	try {
		localStorage.removeItem('user_token');
		localStorage.removeItem('user_data');
	} catch (e) { console.warn('Logout fallback error', e); }
	window.location.replace('/static/login.html');
}

// Check if Bootstrap is available
function isBootstrapAvailable() {
	return typeof bootstrap !== 'undefined' && bootstrap.Modal;
}

// Add basic Bootstrap functionality if not available
function addBootstrapFallback() {
	if (!isBootstrapAvailable()) {
		console.log('⚠️ Bootstrap not available, adding fallback functionality');

		// Add basic dropdown functionality
		document.addEventListener('click', function (e) {
			if (e.target.classList.contains('dropdown-toggle')) {
				e.preventDefault();
				const dropdown = e.target.closest('.dropdown');
				const menu = dropdown.querySelector('.dropdown-menu');

				// Close other dropdowns
				document.querySelectorAll('.dropdown-menu').forEach(m => {
					if (m !== menu) m.style.display = 'none';
				});

				// Toggle current dropdown
				menu.style.display = menu.style.display === 'block' ? 'none' : 'block';
			} else if (!e.target.closest('.dropdown')) {
				// Close all dropdowns when clicking outside
				document.querySelectorAll('.dropdown-menu').forEach(m => {
					m.style.display = 'none';
				});
			}
		});

		// Add basic collapse functionality
		document.addEventListener('click', function (e) {
			if (e.target.classList.contains('navbar-toggler')) {
				e.preventDefault();
				const target = e.target.getAttribute('data-bs-target');
				const element = document.querySelector(target);
				if (element) {
					element.classList.toggle('show');
				}
			}
		});
	}
}

// Auto-initialize navbar if navbar-container exists
document.addEventListener('DOMContentLoaded', function () {
	// Add Bootstrap fallback
	addBootstrapFallback();

	const navbarContainer = document.getElementById('navbar-container');
	if (navbarContainer) {
		// Determine current page from URL
		const currentPath = window.location.pathname;
		let currentPage = 'dashboard';

		if (currentPath.includes('products')) currentPage = 'inventory';
		else if (currentPath.includes('customers')) currentPage = 'sales';
		else if (currentPath.includes('sales')) currentPage = 'sales';
		else if (currentPath.includes('purchases')) currentPage = 'purchases';
		else if (currentPath.includes('suppliers')) currentPage = 'purchases';
		else if (currentPath.includes('bank-accounts')) currentPage = 'banking';
		else if (currentPath.includes('bank-transactions')) currentPage = 'banking';
		else if (currentPath.includes('bank-transfers')) currentPage = 'banking';
		else if (currentPath.includes('bank-reconciliations')) currentPage = 'banking';
		else if (currentPath.includes('journal-entries')) currentPage = 'accounting';
		else if (currentPath.includes('ledgers')) currentPage = 'accounting';
		else if (currentPath.includes('chart-of-accounts')) currentPage = 'accounting';
		else if (currentPath.includes('users')) currentPage = 'setup';
		else if (currentPath.includes('branches')) currentPage = 'setup';
		else if (currentPath.includes('settings')) currentPage = 'setup';
		else if (currentPath.includes('pos')) currentPage = 'sales';
		else if (currentPath.includes('invoices')) currentPage = 'sales';
		else if (currentPath.includes('vat-reconciliations')) currentPage = 'tax';
		else if (currentPath.includes('vat-reports')) currentPage = 'tax';
		else if (currentPath.includes('purchase-orders')) currentPage = 'purchases';
		else if (currentPath.includes('accounting-codes')) currentPage = 'accounting';
		else if (currentPath.includes('reports')) currentPage = 'reports';
		else if (currentPath.includes('financial-reports')) currentPage = 'reports';
		else if (currentPath.includes('asset-management')) currentPage = 'assets';
		else if (currentPath.includes('budgeting')) currentPage = 'budgeting';
		else if (currentPath.includes('procurement')) currentPage = 'procurement';

		initializeNavbar(currentPage);
	}
});
