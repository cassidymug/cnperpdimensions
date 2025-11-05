// Deprecated: navbar-loader.js is now a no-op. The single source of truth is navbar.js.
// Keeping this file as a stub to avoid 404s on pages that still reference it.
(function () {
    function noop() { /* no operation */ }
    class NavbarLoaderStub {
        constructor() { this.isLoaded = true; }
        init() { console.warn('navbar-loader.js deprecated: navbar.js now auto-initializes the navbar.'); }
        loadNavbar() { noop(); }
        ensureNavbarScriptLoaded() { return Promise.resolve(true); }
        determineCurrentPage() { return 'dashboard'; }
        handleLoadError() { noop(); }
        createFallbackNavbar() { return ''; }
        initializeNavbarFunctionality() { noop(); }
        updateUserDisplay() { noop(); }
        applyRoleVisibility() { noop(); }
        setupThemeSwitcher() { noop(); }
        updateThemeIcon() { noop(); }
        highlightCurrentPage() { noop(); }
        setupDropdowns() { noop(); }
        setupClickHandlers() { noop(); }
        setupLogoutHandler() { noop(); }
        handleLogout() { noop(); }
        showLogoutConfirm() { return Promise.resolve(false); }
        performLogout() { noop(); }
        isNavbarLoaded() { return true; }
        getStatus() { return { loaded: true, source: 'stub' }; }
    }
    window.navbarLoader = new NavbarLoaderStub();
    // Ensure global logout points to auth.logout if available (compat on pages that only include navbar-loader)
    try {
        window.logout = function () {
            if (window.auth && typeof auth.logout === 'function') { auth.logout(); return; }
            try {
                localStorage.removeItem('token');
                localStorage.removeItem('user');
                localStorage.removeItem('token_exp');
            } catch (_) { }
            window.location.replace('/static/login.html');
        };
    } catch (_) { }
})();
// Enhanced Navbar Loader for CNPERP ERP
class NavbarLoader {
    constructor() {
        this.navbarContainer = null;
        this.isLoaded = false;
        this.retryCount = 0;
        this.maxRetries = 3;
        // Track whether we've already attempted a forced reload due to missing markers
        this.assetCheckReloaded = false;
    }

    // Initialize navbar loading
    init() {
        this.navbarContainer = document.getElementById('navbar-container');
        if (!this.navbarContainer) {
            // Some pages (like standalone POS/login) may intentionally omit the navbar.
            console.warn('ℹ️ Navbar container not found on this page; skipping navbar init.');
            return false;
        }

        // Ensure auth.js is available (lazy load if absent)
        // authBootstrap should already be loaded and provide basic functionality
        let authSource = window.auth || window.authBootstrap;
        if (!authSource) {
            if (!document.querySelector('script[src*="auth.js"],script[data-autoload-auth]')) {
                const s = document.createElement('script');
                s.src = '/static/js/auth.js?v=' + Date.now();
                s.async = true;
                s.dataset.autoloadAuth = '1';
                document.head.appendChild(s);
            }
            // Defer init until authReady event or fallback timeout
            if (this.retryCount < 40) { // ~2s
                this.retryCount++;
                setTimeout(() => this.init(), 50);
                return false;
            }
            console.warn('⚠️ Auth helper still not detected after extended retries; proceeding without it');
        }

        // Defer auth check until auth is fully initialized
        document.addEventListener('authReady', () => {
            console.log('🚀 authReady event received by navbar-loader.');
            const authSource = window.auth || window.authBootstrap;
            const path = window.location.pathname;
            const isLoginPage = path.endsWith('/login.html') || path.endsWith('/login');

            if (authSource && !authSource.isAuthenticated() && !isLoginPage) {
                console.log('🔒 Not authenticated after authReady - redirecting to login');
                const redirectUrl = `/static/login.html?next=${encodeURIComponent(path + window.location.search)}`;
                window.location.replace(redirectUrl);
            } else {
                console.log('✅ Authenticated or on login page after authReady.');
                this.loadNavbar();
            }
        }, { once: true });

        // Fallback if authReady never fires
        setTimeout(() => {
            if (!this.isLoaded) {
                console.warn('⚠️ authReady event never fired. Attempting to load navbar anyway.');
                this.loadNavbar();
            }
        }, 2000);

        console.log('🔍 Navbar container found, waiting for authReady event...');

        const updateFn = () => this.updateUserDisplay();
        setTimeout(updateFn, 300);
        document.addEventListener('authReady', () => setTimeout(updateFn, 50), { once: true });

        return true;
    }

    // Load the navbar with enhanced error handling
    async loadNavbar() {
        // Ensure this is only called once
        if (this.isLoaded) {
            console.log('Navbar already loaded or load in progress.');
            return;
        }
        this.isLoaded = true; // Mark as loading/loaded to prevent re-entry

        try {
            console.log('🔄 Loading navbar...');
            console.log('🔍 Navbar container:', this.navbarContainer);

            // Use the createNavbar function from navbar.js (load dynamically if missing)
            if (typeof createNavbar !== 'function') {
                console.warn('⚠️ createNavbar not found. Loading /static/js/navbar.js dynamically...');
                await this.ensureNavbarScriptLoaded(true);
            }

            if (typeof createNavbar === 'function') {
                const currentPage = this.determineCurrentPage();
                console.log('📄 Current page determined:', currentPage);
                let navbarHtml = createNavbar(currentPage);
                if (typeof navbarHtml !== 'string') {
                    console.error('❌ createNavbar did not return a string. Value:', navbarHtml);
                    this.createFallbackNavbar();
                    return;
                }
                console.log('📝 Navbar HTML generated, length:', navbarHtml.length);

                // Validate presence of a few key links to ensure navbar.js loaded correctly
                const requiredMarkers = [
                    '/static/accounting-codes.html',
                    '/static/financial-reports.html',
                    '/static/asset-management.html'
                ];
                const missing = requiredMarkers.filter(m => !navbarHtml.includes(m));
                if (missing.length && !this.assetCheckReloaded) {
                    console.warn('⚠️ Navbar markers missing (', missing.join(', '), '). Reloading navbar.js once...');
                    this.assetCheckReloaded = true;
                    await this.ensureNavbarScriptLoaded(true);
                    if (typeof createNavbar === 'function') {
                        navbarHtml = createNavbar(currentPage);
                        if (typeof navbarHtml !== 'string') {
                            console.error('❌ createNavbar after reload did not return a string:', navbarHtml);
                            this.createFallbackNavbar();
                            return;
                        }
                    }
                } else if (missing.length) {
                    console.warn('⚠️ Navbar markers still missing after reload:', missing);
                }

                this.navbarContainer.innerHTML = navbarHtml;
                console.log('✅ Navbar loaded successfully using createNavbar function');
                this.isLoaded = true;
                this.initializeNavbarFunctionality();
                this.applyRoleVisibility();
                document.dispatchEvent(new CustomEvent('navbarLoaded', { detail: { success: true } }));
            } else {
                throw new Error('createNavbar function not found after loading navbar.js');
            }

        } catch (error) {
            console.error('❌ Error loading navbar:', error);
            this.handleLoadError();
        }
    }

    // Ensure navbar.js is loaded
    ensureNavbarScriptLoaded(forceReload = false) {
        return new Promise((resolve, reject) => {
            const existing = document.getElementById('navbarScript');
            if (existing && !forceReload) {
                // Script already present; give it a tick to initialize
                setTimeout(() => resolve(), 100);
                return;
            }
            if (existing && forceReload) {
                existing.remove();
            }
            const script = document.createElement('script');
            script.id = 'navbarScript';
            // cache-bust to avoid stale cached script
            script.src = '/static/js/navbar.js?v=' + Date.now();
            script.onload = () => resolve();
            script.onerror = () => reject(new Error('Failed to load /static/js/navbar.js'));
            document.head.appendChild(script);
        });
    }

    // Determine current page for navbar highlighting
    determineCurrentPage() {
        const currentPath = window.location.pathname;

        if (currentPath.includes('products')) return 'products';
        else if (currentPath.includes('customers')) return 'customers';
        else if (currentPath.includes('sales')) return 'sales';
        else if (currentPath.includes('purchases')) return 'purchases';
        else if (currentPath.includes('suppliers')) return 'suppliers';
        else if (currentPath.includes('bank-accounts')) return 'banking';
        else if (currentPath.includes('bank-transactions')) return 'banking';
        else if (currentPath.includes('bank-transfers')) return 'banking';
        else if (currentPath.includes('bank-reconciliations')) return 'banking';
        else if (currentPath.includes('journal-entries')) return 'accounting';
        else if (currentPath.includes('ledgers')) return 'accounting';
        else if (currentPath.includes('users')) return 'setup';
        else if (currentPath.includes('branches')) return 'setup';
        else if (currentPath.includes('settings')) return 'setup';
        else if (currentPath.includes('pos')) return 'sales';
        else if (currentPath.includes('invoices')) return 'sales';
        else if (currentPath.includes('vat-reconciliations')) return 'tax';
        else if (currentPath.includes('vat-reports')) return 'tax';
        else if (currentPath.includes('purchase-orders')) return 'purchases';
        else if (currentPath.includes('accounting-codes')) return 'accounting';
        else if (currentPath.includes('reports')) return 'accounting';
        else if (currentPath.includes('financial-reports')) return 'reports';
        else if (currentPath.includes('asset-management')) return 'assets';
        else return 'dashboard';
    }

    // Handle navbar load errors with retry logic
    handleLoadError() {
        if (this.retryCount < this.maxRetries) {
            this.retryCount++;
            console.log(`🔄 Retrying navbar load (${this.retryCount}/${this.maxRetries})`);
            setTimeout(() => this.loadNavbar(), 1000 * this.retryCount);
        } else {
            console.warn('⚠️ Max retries reached, using fallback navbar');
            this.createFallbackNavbar();
        }
    }    // Create a fallback navbar if loading fails
    createFallbackNavbar() {
        const fallbackHtml = `
            <nav class="navbar navbar-expand-lg modern-navbar">
                <div class="container-fluid">
                    <a class="navbar-brand modern-brand fw-bold" href="/static/index.html">
                        <i class="bi bi-building me-2"></i>CNPERP ERP
                    </a>

                    <button class="navbar-toggler modern-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#fallbackNavbar">
                        <span class="navbar-toggler-icon"></span>
                    </button>

                    <div class="collapse navbar-collapse" id="fallbackNavbar">
                        <ul class="navbar-nav me-auto">
                            <li class="nav-item">
                                <a class="nav-link modern-nav-link" href="/static/index.html">
                                    <i class="bi bi-speedometer2 me-1"></i>Dashboard
                                </a>
                            </li>
                                                         <li class="nav-item dropdown">
                                 <a class="nav-link dropdown-toggle modern-nav-link" href="#" role="button" data-bs-toggle="dropdown">
                                     <i class="bi bi-calculator me-1"></i>Accounting
                                 </a>
                                 <ul class="dropdown-menu modern-dropdown">
                                     <li><a class="dropdown-item modern-dropdown-item" href="/static/chart-of-accounts.html">Chart of Accounts</a></li>
                                     <li><a class="dropdown-item modern-dropdown-item" href="/static/accounting-codes.html">Accounting Codes</a></li>
                                     <li><a class="dropdown-item modern-dropdown-item" href="/static/journal-entries.html">Journal Entries</a></li>
                                     <li><a class="dropdown-item modern-dropdown-item" href="/static/ledgers.html">Ledgers</a></li>
                                 </ul>
                             </li>
                             <li class="nav-item dropdown">
                                 <a class="nav-link dropdown-toggle modern-nav-link" href="#" role="button" data-bs-toggle="dropdown">
                                     <i class="bi bi-file-earmark-text me-1"></i>Reports
                                 </a>
                                 <ul class="dropdown-menu modern-dropdown scrollable-dropdown">
                                     <!-- Financial Reports -->
                                     <li><h6 class="dropdown-header">Financial Reports</h6></li>
                                     <li><a class="dropdown-item modern-dropdown-item" href="/static/reports.html">
                                         <i class="bi bi-chart-bar me-2"></i>Reports Center
                                     </a></li>
                                     <li><a class="dropdown-item modern-dropdown-item" href="/static/financial-reports.html">
                                         <i class="bi bi-calculator me-2"></i>Financial Statements
                                     </a></li>
                                     <li><a class="dropdown-item modern-dropdown-item" href="/static/generic-report-export.html">
                                         <i class="bi bi-filetype-pdf me-2"></i>Generic Export
                                     </a></li>
                                     <li><a class="dropdown-item modern-dropdown-item" href="/static/reports.html#trial-balance">
                                         <i class="bi bi-list-task me-2"></i>Trial Balance
                                     </a></li>
                                     <li><a class="dropdown-item modern-dropdown-item" href="/static/reports.html#balance-sheet">
                                         <i class="bi bi-pie-chart me-2"></i>Balance Sheet
                                     </a></li>
                                     <li><a class="dropdown-item modern-dropdown-item" href="/static/reports.html#debtors-aging">
                                         <i class="bi bi-people me-2"></i>Debtors Aging
                                     </a></li>
                                     <li><a class="dropdown-item modern-dropdown-item" href="/static/reports.html#creditors-aging">
                                         <i class="bi bi-building me-2"></i>Creditors Aging
                                     </a></li>

                                     <li><hr class="dropdown-divider"></li>

                                     <!-- Sales Reports -->
                                     <li><h6 class="dropdown-header">Sales Reports</h6></li>
                                     <li><a class="dropdown-item modern-dropdown-item" href="/static/sales-reports.html">
                                         <i class="bi bi-cart me-2"></i>Sales Analytics
                                     </a></li>
                                     <li><a class="dropdown-item modern-dropdown-item" href="/static/sales-reports.html#daily">
                                         <i class="bi bi-calendar-day me-2"></i>Daily Sales
                                     </a></li>
                                     <li><a class="dropdown-item modern-dropdown-item" href="/static/sales-reports.html#monthly">
                                         <i class="bi bi-calendar-month me-2"></i>Monthly Sales
                                     </a></li>
                                     <li><a class="dropdown-item modern-dropdown-item" href="/static/sales-reports.html#customers">
                                         <i class="bi bi-person-badge me-2"></i>Customer Analysis
                                     </a></li>
                                     <li><a class="dropdown-item modern-dropdown-item" href="/static/customer-reports.html">
                                         <i class="bi bi-people-fill me-2"></i>Customer Reports
                                     </a></li>
                                     <li><a class="dropdown-item modern-dropdown-item" href="/static/invoice-reports.html">
                                         <i class="bi bi-receipt me-2"></i>Invoice Reports
                                     </a></li>

                                     <li><hr class="dropdown-divider"></li>

                                     <!-- Inventory Reports -->
                                     <li><h6 class="dropdown-header">Inventory Reports</h6></li>
                                     <li><a class="dropdown-item modern-dropdown-item" href="/static/inventory-reports.html">
                                         <i class="bi bi-box-seam me-2"></i>Inventory Analytics
                                     </a></li>
                                     <li><a class="dropdown-item modern-dropdown-item" href="/static/inventory-reports.html#stock">
                                         <i class="bi bi-boxes me-2"></i>Stock Levels
                                     </a></li>
                                     <li><a class="dropdown-item modern-dropdown-item" href="/static/inventory-reports.html#valuation">
                                         <i class="bi bi-currency-dollar me-2"></i>Stock Valuation
                                     </a></li>
                                     <li><a class="dropdown-item modern-dropdown-item" href="/static/inventory-reports.html#movement">
                                         <i class="bi bi-arrow-left-right me-2"></i>Stock Movement
                                     </a></li>
                                     <li><a class="dropdown-item modern-dropdown-item" href="/static/purchase-reports.html">
                                         <i class="bi bi-truck me-2"></i>Purchase Reports
                                     </a></li>
                                     <li><a class="dropdown-item modern-dropdown-item" href="/static/supplier-reports.html">
                                         <i class="bi bi-building me-2"></i>Supplier Reports
                                     </a></li>

                                     <li><hr class="dropdown-divider"></li>

                                     <!-- Banking Reports -->
                                     <li><h6 class="dropdown-header">Banking Reports</h6></li>
                                     <li><a class="dropdown-item modern-dropdown-item" href="/static/banking-reports.html#cashflow">
                                         <i class="bi bi-cash-stack me-2"></i>Cash Flow
                                     </a></li>
                                     <li><a class="dropdown-item modern-dropdown-item" href="/static/banking-reports.html#reconciliation">
                                         <i class="bi bi-check2-square me-2"></i>Bank Reconciliation
                                     </a></li>
                                     <li><a class="dropdown-item modern-dropdown-item" href="/static/bank-transaction-reports.html">
                                         <i class="bi bi-credit-card me-2"></i>Transaction Reports
                                     </a></li>
                                     <li><a class="dropdown-item modern-dropdown-item" href="/static/bank-transfer-reports.html">
                                         <i class="bi bi-arrow-left-right me-2"></i>Transfer Reports
                                     </a></li>

                                     <li><hr class="dropdown-divider"></li>

                                     <!-- Tax Reports -->
                                     <li><h6 class="dropdown-header">Tax Reports</h6></li>
                                     <li><a class="dropdown-item modern-dropdown-item" href="/static/vat-reconciliations.html">
                                         <i class="bi bi-receipt me-2"></i>VAT Returns
                                     </a></li>
                                     <li><a class="dropdown-item modern-dropdown-item" href="/static/vat-reports.html">
                                         <i class="bi bi-percent me-2"></i>VAT Reports
                                     </a></li>
                                     <li><a class="dropdown-item modern-dropdown-item" href="/static/tax-reports.html">
                                         <i class="bi bi-calculator me-2"></i>Tax Calculations
                                     </a></li>

                                     <li><hr class="dropdown-divider"></li>

                                     <!-- Budget Reports -->
                                     <li><h6 class="dropdown-header">Budget Reports</h6></li>
                                     <li><a class="dropdown-item modern-dropdown-item" href="/static/budget-reports.html">
                                         <i class="bi bi-cash-stack me-2"></i>Budget Analysis
                                     </a></li>
                                     <li><a class="dropdown-item modern-dropdown-item" href="/static/budget-reports.html#variance">
                                         <i class="bi bi-graph-up me-2"></i>Budget Variance
                                     </a></li>
                                     <li><a class="dropdown-item modern-dropdown-item" href="/static/budget-reports.html#forecast">
                                         <i class="bi bi-calendar-range me-2"></i>Budget Forecast
                                     </a></li>

                                     <li><hr class="dropdown-divider"></li>

                                     <!-- Management Reports -->
                                     <li><h6 class="dropdown-header">Management Reports</h6></li>
                                     <li><a class="dropdown-item modern-dropdown-item" href="/static/financial-reports.html#profit-loss">
                                         <i class="bi bi-graph-up me-2"></i>Profit & Loss
                                     </a></li>
                                     <li><a class="dropdown-item modern-dropdown-item" href="/static/kpi-reports.html">
                                         <i class="bi bi-speedometer2 me-2"></i>KPI Reports
                                     </a></li>
                                 </ul>
                             </li>
                            <li class="nav-item dropdown">
                                <a class="nav-link dropdown-toggle modern-nav-link" href="#" role="button" data-bs-toggle="dropdown">
                                    <i class="bi bi-box-seam me-1"></i>Inventory
                                </a>
                                <ul class="dropdown-menu modern-dropdown">
                                    <li><a class="dropdown-item modern-dropdown-item" href="/static/products.html">Products</a></li>
                                    <li><a class="dropdown-item modern-dropdown-item" href="/static/purchases.html">Purchases</a></li>
                                    <li><a class="dropdown-item modern-dropdown-item" href="/static/purchase-orders.html">Purchase Orders</a></li>
                                </ul>
                            </li>
                            <li class="nav-item dropdown">
                                <a class="nav-link dropdown-toggle modern-nav-link" href="#" role="button" data-bs-toggle="dropdown">
                                    <i class="bi bi-hdd-stack me-1"></i>Assets
                                </a>
                                <ul class="dropdown-menu modern-dropdown">
                                    <li><a class="dropdown-item modern-dropdown-item" href="/static/asset-management.html">Asset Register</a></li>
                                    <li><a class="dropdown-item modern-dropdown-item" href="/static/asset-management.html#depreciation">Depreciation</a></li>
                                    <li><a class="dropdown-item modern-dropdown-item" href="/static/asset-management.html#maintenance">Maintenance</a></li>
                                </ul>
                            </li>
                            <li class="nav-item dropdown">
                                <a class="nav-link dropdown-toggle modern-nav-link" href="#" role="button" data-bs-toggle="dropdown">
                                    <i class="bi bi-cart me-1"></i>Sales
                                </a>
                                <ul class="dropdown-menu modern-dropdown">
                                    <li><a class="dropdown-item modern-dropdown-item" href="/static/pos.html">POS</a></li>
                                    <li><a class="dropdown-item modern-dropdown-item" href="/static/sales.html">Sales</a></li>
                                    <li><a class="dropdown-item modern-dropdown-item" href="/static/customers.html">Customers</a></li>
                                    <li><a class="dropdown-item modern-dropdown-item" href="/static/invoices.html">Invoices</a></li>
                                    <li><hr class="dropdown-divider"></li>
                                    <li><a class="dropdown-item modern-dropdown-item" href="/static/sales-reports.html">Sales Reports</a></li>
                                    <li><a class="dropdown-item modern-dropdown-item" href="/static/sales-analytics.html">Sales Analytics</a></li>
                                    <li><a class="dropdown-item modern-dropdown-item" href="/static/customer-reports.html">Customer Reports</a></li>
                                    <li><a class="dropdown-item modern-dropdown-item" href="/static/invoice-reports.html">Invoice Reports</a></li>
                                </ul>
                            </li>
                            <li class="nav-item dropdown">
                                <a class="nav-link dropdown-toggle modern-nav-link" href="#" role="button" data-bs-toggle="dropdown">
                                    <i class="bi bi-truck me-1"></i>Purchases
                                </a>
                                <ul class="dropdown-menu modern-dropdown">
                                    <li><a class="dropdown-item modern-dropdown-item" href="/static/suppliers.html">Suppliers</a></li>
                                    <li><a class="dropdown-item modern-dropdown-item" href="/static/purchases.html">Purchases</a></li>
                                    <li><a class="dropdown-item modern-dropdown-item" href="/static/purchase-orders.html">Orders</a></li>
                                </ul>
                            </li>
                            <li class="nav-item dropdown">
                                <a class="nav-link dropdown-toggle modern-nav-link" href="#" role="button" data-bs-toggle="dropdown">
                                    <i class="bi bi-bank me-1"></i>Banking
                                </a>
                                <ul class="dropdown-menu modern-dropdown">
                                    <li><a class="dropdown-item modern-dropdown-item" href="/static/bank-accounts.html">Bank Accounts</a></li>
                                    <li><a class="dropdown-item modern-dropdown-item" href="/static/bank-transactions.html">Transactions</a></li>
                                    <li><a class="dropdown-item modern-dropdown-item" href="/static/bank-transfers.html">Transfers</a></li>
                                    <li><a class="dropdown-item modern-dropdown-item" href="/static/bank-reconciliations.html">Reconciliations</a></li>
                                </ul>
                            </li>
                            <li class="nav-item dropdown">
                                <a class="nav-link dropdown-toggle modern-nav-link" href="#" role="button" data-bs-toggle="dropdown">
                                    <i class="bi bi-percent me-1"></i>Tax
                                </a>
                                <ul class="dropdown-menu modern-dropdown">
                                    <li><a class="dropdown-item modern-dropdown-item" href="/static/vat-reconciliations.html">VAT Reconciliations</a></li>
                                    <li><a class="dropdown-item modern-dropdown-item" href="/static/vat-reports.html">VAT Reports</a></li>
                                    <li><hr class="dropdown-divider"></li>
                                    <li><a class="dropdown-item modern-dropdown-item" href="/static/financial-reports.html">Tax Reports</a></li>
                                    <li><a class="dropdown-item modern-dropdown-item" href="/static/settings.html#vat-settings">VAT Settings</a></li>
                                </ul>
                            </li>
                            <li class="nav-item dropdown">
                                <a class="nav-link dropdown-toggle modern-nav-link" href="#" role="button" data-bs-toggle="dropdown">
                                    <i class="bi bi-gear me-1"></i>Setup
                                </a>
                                <ul class="dropdown-menu modern-dropdown">
                                    <li><a class="dropdown-item modern-dropdown-item" href="/static/branches.html">Branches</a></li>
                                    <li><a class="dropdown-item modern-dropdown-item" href="/static/users.html">Users</a></li>
                                    <li><a class="dropdown-item modern-dropdown-item" href="/static/settings.html">Settings</a></li>
                                </ul>
                            </li>
                        </ul>

                        <ul class="navbar-nav">
                            <li class="nav-item">
                                <button class="btn btn-outline-light btn-sm" id="themeToggle" title="Toggle Theme">
                                    <i class="bi bi-moon-fill"></i>
                                </button>
                            </li>
                            <li class="nav-item dropdown">
                                <a class="nav-link dropdown-toggle modern-nav-link" href="#" role="button" data-bs-toggle="dropdown">
                                    <i class="bi bi-person-circle me-1"></i>Admin
                                </a>
                                <ul class="dropdown-menu dropdown-menu-end modern-dropdown">
                                    <li><a class="dropdown-item modern-dropdown-item" href="/static/admin-panel.html">Admin Panel</a></li>
                                    <li><a class="dropdown-item modern-dropdown-item" href="/static/users.html">Users</a></li>
                                    <li><a class="dropdown-item modern-dropdown-item" href="/static/settings.html">Settings</a></li>
                                    <li><a class="dropdown-item modern-dropdown-item" href="/static/backup-management.html">Backup Management</a></li>
                                    <li><hr class="dropdown-divider"></li>
                                    <li><a class="dropdown-item modern-dropdown-item" href="#" onclick="logout()">Logout</a></li>
                                </ul>
                            </li>
                        </ul>
                    </div>
                </div>
            </nav>
            <div style="height: 70px;"></div>
        `;

        this.navbarContainer.innerHTML = fallbackHtml;
        this.initializeNavbarFunctionality();

        // Dispatch event for fallback navbar
        document.dispatchEvent(new CustomEvent('navbarLoaded', { detail: { success: false, fallback: true } }));
    }

    // Initialize all navbar functionality
    initializeNavbarFunctionality() {
        // Wait a bit for DOM to be ready
        setTimeout(() => {
            this.setupThemeSwitcher();
            this.highlightCurrentPage();
            this.setupDropdowns();
            this.setupClickHandlers();
            this.setupLogoutHandler();
            this.updateUserDisplay(); // Add user display update
            // Install global auth fetch wrapper if not present
            if (!document.querySelector('script[src*="auth-fetch.js"]')) {
                const s = document.createElement('script');
                s.src = '/static/js/auth-fetch.js?v=' + Date.now();
                document.head.appendChild(s);
            }
            // Inject ui-guard.js globally if not present
            if (!document.querySelector('script[src*="ui-guard.js"]')) {
                const s = document.createElement('script');
                s.src = '/static/js/ui-guard.js?v=' + Date.now();
                document.head.appendChild(s);
            }
        }, 100);
    }

    // Update user display in navbar
    updateUserDisplay() {
        const userDisplay = document.getElementById('current-user-display');
        const branchDisplay = document.getElementById('current-branch-display');
        const badgeContainerId = 'dev-timeout-badge';
        const host = (window.location && window.location.hostname) || '';
        const authSourceFull = window.auth; // full auth (with debugInfo)
        let devSuspended = false;
        try {
            if (authSourceFull && typeof authSourceFull.debugInfo === 'function') {
                const info = authSourceFull.debugInfo();
                devSuspended = !!info.devNoTimeout;
            } else if (['localhost', '127.0.0.1', '0.0.0.0'].includes(host)) {
                // Fallback heuristic
                devSuspended = true;
            }
        } catch (_) { }

        if (userDisplay && branchDisplay) {
            // Use authBootstrap as fallback when full auth is not available
            const authSource = window.auth || window.authBootstrap;

            if (authSource && authSource.isAuthenticated()) {
                const user = authSource.getUser();
                console.debug('[navbar-loader] Authenticated state. Using:', authSource === window.auth ? 'auth' : 'authBootstrap', 'User object:', user);
                if (user) {
                    // Display username
                    const username = user.username || 'Unknown User';
                    userDisplay.textContent = username;

                    // Display branch information
                    const branchCode = user.branch_code || 'No Branch';
                    branchDisplay.textContent = `Branch: ${branchCode}`;
                } else {
                    console.warn('[navbar-loader] isAuthenticated true but no user payload found in storage');
                    userDisplay.textContent = 'Not logged in';
                    branchDisplay.textContent = 'Branch: N/A';
                }
            } else {
                console.debug('[navbar-loader] Not authenticated (no auth service available or token invalid)');
                userDisplay.textContent = 'Not logged in';
                branchDisplay.textContent = 'Branch: N/A';
            }
        }

        // Inject / update DEV timeout badge
        try {
            let existing = document.getElementById(badgeContainerId);
            if (devSuspended) {
                if (!existing) {
                    existing = document.createElement('span');
                    existing.id = badgeContainerId;
                    existing.className = 'badge rounded-pill bg-danger ms-2';
                    existing.style.fontSize = '0.65rem';
                    existing.style.letterSpacing = '0.5px';
                    existing.title = 'Session timeouts suspended for development';
                    // Prefer placing next to username if available
                    if (userDisplay && userDisplay.parentElement) {
                        userDisplay.parentElement.appendChild(existing);
                    } else if (this.navbarContainer) {
                        this.navbarContainer.appendChild(existing);
                    }
                }
                existing.innerHTML = '<i class="bi bi-lightning-fill me-1"></i>DEV NO TIMEOUT';
            } else if (existing) {
                existing.remove();
            }
        } catch (e) { console.warn('[navbar-loader] Badge inject failed', e); }
    }

    // Hide/show menu items based on role permissions
    // Hide / show nav items based on role matrix
    applyRoleVisibility() {
        try {
            // Use authBootstrap as fallback when full auth is not available
            const authSource = window.auth || window.authBootstrap;
            if (!authSource || !authSource.isAuthenticated()) return;
            const user = authSource.getUser();
            if (!user) return;
            const role = (user.role || '').toLowerCase();
            const showAll = role === 'super_admin' || role === 'admin';

            // Map of feature keywords to roles allowed
            // Simplified role matrix per spec:
            // - Universal (super_admin, admin, accountant) see everything (handled by showAll)
            // - Manager: inventory (products), customers, POS, sales, reports (sales reports)
            // - POS users (cashier, pos_user): POS, sales, inventory (read), customers
            const accessMatrix = {
                accounting: ['accountant'],
                purchases: ['accountant'],
                suppliers: ['accountant'],
                banking: ['accountant'],
                products: ['accountant', 'manager', 'cashier', 'pos_user'],
                inventory: ['accountant', 'manager', 'cashier', 'pos_user'],
                pos: ['accountant', 'manager', 'cashier', 'pos_user'],
                sales: ['accountant', 'manager', 'cashier', 'pos_user'],
                settings: ['accountant'],
                users: ['accountant'],
                reports: ['accountant', 'manager'],
                assets: ['accountant']
            };

            // Simple heuristic: query all nav links and decide
            const links = this.navbarContainer.querySelectorAll('a[href]');
            links.forEach(a => {
                if (showAll) return; // keep all visible
                const href = a.getAttribute('href') || '';
                const text = (a.textContent || '').toLowerCase();
                let feature = null;
                if (/accounting|journal|ledger|financial|trial|balance/.test(href + text)) feature = 'accounting';
                else if (/purchase-order|purchases/.test(href + text)) feature = 'purchases';
                else if (/supplier/.test(href + text)) feature = 'suppliers';
                else if (/bank-/.test(href + text) || /reconciliation/.test(href + text)) feature = 'banking';
                else if (/product/.test(href + text)) feature = 'products';
                else if (/inventory|stock|adjustment/.test(href + text)) feature = 'inventory';
                else if (/pos/.test(href + text)) feature = 'pos';
                else if (/sale/.test(href + text)) feature = 'sales';
                else if (/setting|user|branch/.test(href + text)) feature = 'settings';
                else if (/report/.test(href + text)) feature = 'reports';
                else if (/asset/.test(href + text)) feature = 'assets';

                if (feature) {
                    const allowed = accessMatrix[feature];
                    if (allowed && !allowed.includes(role)) {
                        a.closest('li')?.classList.add('d-none');
                    }
                }
            });

            // Tag body for CSS-based conditional UI (optional)
            document.body.setAttribute('data-role', role);
        } catch (e) { console.warn('Role visibility error', e); }
    }

    // Setup theme switcher
    setupThemeSwitcher() {
        const themeToggle = document.getElementById('themeToggle');
        if (themeToggle) {
            const icon = themeToggle.querySelector('i');

            // Check for saved theme preference
            const currentTheme = localStorage.getItem('theme') || 'light';
            document.body.setAttribute('data-theme', currentTheme);
            this.updateThemeIcon(currentTheme);

            themeToggle.addEventListener('click', () => {
                const currentTheme = document.body.getAttribute('data-theme');
                const newTheme = currentTheme === 'dark' ? 'light' : 'dark';

                document.body.setAttribute('data-theme', newTheme);
                localStorage.setItem('theme', newTheme);
                this.updateThemeIcon(newTheme);
            });
        }
    }

    // Update theme icon
    updateThemeIcon(theme) {
        const themeToggle = document.getElementById('themeToggle');
        if (themeToggle) {
            const icon = themeToggle.querySelector('i');
            if (theme === 'dark') {
                icon.className = 'bi bi-sun-fill';
                themeToggle.title = 'Switch to Light Mode';
            } else {
                icon.className = 'bi bi-moon-fill';
                themeToggle.title = 'Switch to Dark Mode';
            }
        }
    }

    // Highlight current page in navigation
    highlightCurrentPage() {
        const currentPath = window.location.pathname;
        const navLinks = document.querySelectorAll('.navbar-nav .nav-link');

        navLinks.forEach(link => {
            const href = link.getAttribute('href');
            if (href && href === currentPath) {
                link.classList.add('active');
            }
        });
    }

    // Setup Bootstrap dropdowns
    setupDropdowns() {
        if (typeof bootstrap !== 'undefined') {
            const dropdownElementList = document.querySelectorAll('.dropdown-toggle');
            dropdownElementList.forEach(dropdownToggleEl => {
                new bootstrap.Dropdown(dropdownToggleEl);
            });
        }
    }

    // Setup click handlers for navigation links
    setupClickHandlers() {
        const allNavLinks = document.querySelectorAll('.navbar-nav a');
        allNavLinks.forEach(link => {
            link.addEventListener('click', (e) => {
                // Don't prevent default for dropdown toggles
                if (link.classList.contains('dropdown-toggle')) {
                    return;
                }

                // For logout, handle specially
                if (link.getAttribute('onclick') === 'logout()') {
                    e.preventDefault();
                    this.handleLogout();
                    return;
                }

                // For other links, ensure they work properly
                const href = link.getAttribute('href');
                if (href && href !== '#' && !href.startsWith('javascript:')) {
                    // Add loading indicator if modernUI is available
                    if (window.modernUI) {
                        window.modernUI.showNotification('Navigating...', 'info');
                    }
                }
            });
        });
    }

    // Setup logout handler
    setupLogoutHandler() {
        // Override the global logout function
        window.logout = () => this.handleLogout();
    }

    // Handle logout
    handleLogout() {
        // Show a simple custom confirmation box instead of browser confirm
        this.showLogoutConfirm();
    }

    // Display a simple centered square confirm box for logout
    showLogoutConfirm() {
        // If one already exists, don't create another
        if (document.getElementById('custom-logout-confirm')) return;

        // Inject minimal styles once
        if (!document.getElementById('custom-logout-confirm-style')) {
            const style = document.createElement('style');
            style.id = 'custom-logout-confirm-style';
            style.textContent = `
            #custom-logout-overlay {position:fixed;inset:0;background:rgba(0,0,0,0.35);display:flex;align-items:center;justify-content:center;z-index:2000;}
            #custom-logout-confirm {background:#fff;border:1px solid #ccc;border-radius:4px;box-shadow:0 4px 16px rgba(0,0,0,0.15);width:300px;max-width:90%;padding:18px;font-family:system-ui,-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;animation:fadeIn .12s ease-out;}
            #custom-logout-confirm h5 {margin:0 0 8px;font-size:16px;font-weight:600;text-align:center;}
            #custom-logout-confirm p {margin:0 0 16px;font-size:13px;text-align:center;color:#444;}
            #custom-logout-confirm .btn-row {display:flex;gap:8px;}
            #custom-logout-confirm button {flex:1;border:1px solid #888;background:#f5f5f5;border-radius:4px;padding:8px 10px;font-size:13px;cursor:pointer;transition:background .15s,border-color .15s;}
            #custom-logout-confirm button.confirm {background:#c62828;color:#fff;border-color:#c62828;}
            #custom-logout-confirm button.confirm:hover {background:#b71c1c;}
            #custom-logout-confirm button.cancel:hover {background:#e0e0e0;}
            @keyframes fadeIn {from {opacity:0;transform:scale(.96);} to {opacity:1;transform:scale(1);} }
            `;
            document.head.appendChild(style);
        }

        const overlay = document.createElement('div');
        overlay.id = 'custom-logout-overlay';
        overlay.innerHTML = `
          <div id="custom-logout-confirm" role="dialog" aria-modal="true" aria-labelledby="logoutConfirmTitle">
            <h5 id="logoutConfirmTitle">Confirm Logout</h5>
            <p>Are you sure you want to log out?</p>
            <div class="btn-row">
              <button type="button" class="cancel" id="logoutCancelBtn">Cancel</button>
              <button type="button" class="confirm" id="logoutConfirmBtn">Logout</button>
            </div>
          </div>`;
        document.body.appendChild(overlay);

        const remove = () => { if (overlay.parentNode) overlay.parentNode.removeChild(overlay); };
        document.getElementById('logoutCancelBtn').addEventListener('click', remove);
        document.getElementById('logoutConfirmBtn').addEventListener('click', () => {
            remove();
            this.performLogout();
        });
        // Close on ESC
        const escHandler = (e) => { if (e.key === 'Escape') { remove(); document.removeEventListener('keydown', escHandler); } };
        document.addEventListener('keydown', escHandler);
    }

    // Actual logout logic separated from confirmation UI
    performLogout() {
        try {
            localStorage.removeItem('theme');
            sessionStorage.clear();
            if (window.auth) {
                // Call without a reason so no top message appears on login
                auth.logout();
                return; // auth.logout handles redirect
            }
            // Fallback if auth missing
            localStorage.removeItem('token');
            localStorage.removeItem('user');
            localStorage.removeItem('token_exp');
            window.location.replace('/static/login.html');
        } catch (e) {
            console.warn('Logout error', e);
            window.location.replace('/static/login.html');
        }
    }

    // Check if navbar is loaded
    isNavbarLoaded() {
        return this.isLoaded;
    }

    // Get navbar status
    getStatus() {
        return {
            loaded: this.isLoaded,
            retryCount: this.retryCount,
            containerExists: !!this.navbarContainer
        };
    }
}

// Auto-initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function () {
    window.navbarLoader = new NavbarLoader();
    window.navbarLoader.init();
});

// Export for manual initialization
if (typeof module !== 'undefined' && module.exports) {
    module.exports = NavbarLoader;
}
