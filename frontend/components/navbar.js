// CNPERP ERP Navigation Bar Component
class CNPERPNavbar {
    constructor(options = {}) {
        this.options = {
            brandName: 'CNPERP ERP',
            brandIcon: 'bi-building',
            primaryColor: '#0d6efd',
            accentColor: '#198754',
            showSearch: true,
            showNotifications: true,
            showQuickActions: true,
            showUserMenu: true,
            ...options
        };

        this.currentUser = null;
        this.notifications = [];
        this.init();
    }

    init() {
        this.createNavbar();
        this.bindEvents();
        this.updateDateTime();
        this.loadUserData();
        this.loadNotifications();
    }

    createNavbar() {
        const navbarHTML = `
            <nav class="navbar navbar-expand-lg navbar-dark bg-primary" id="cnperpNavbar">
                <div class="container-fluid">
                    <!-- Brand -->
                    <a class="navbar-brand" href="index.html">
                        <i class="bi ${this.options.brandIcon} me-2"></i>
                        ${this.options.brandName}
                    </a>

                    <!-- Mobile Toggle -->
                    <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarMain">
                        <span class="navbar-toggler-icon"></span>
                    </button>

                    <!-- Navigation Items -->
                    <div class="collapse navbar-collapse" id="navbarMain">
                        <!-- Left Side - Main Navigation -->
                        <ul class="navbar-nav me-auto">
                            ${this.createMainNavigation()}
                        </ul>

                        <!-- Center - Search -->
                        ${this.options.showSearch ? this.createSearchBox() : ''}

                        <!-- Right Side - User Menu & Quick Actions -->
                        <ul class="navbar-nav">
                            ${this.options.showQuickActions ? this.createQuickActions() : ''}
                            ${this.options.showNotifications ? this.createNotifications() : ''}
                            ${this.options.showUserMenu ? this.createUserMenu() : ''}
                        </ul>
                    </div>
                </div>
            </nav>

            <!-- Secondary Navigation Bar -->
            <nav class="navbar navbar-expand-lg navbar-light bg-light border-bottom">
                <div class="container-fluid">
                    <span class="navbar-text">
                        <i class="bi bi-geo-alt me-1"></i>
                        Branch: <span id="currentBranch">Main Office</span>
                    </span>

                    <ul class="navbar-nav ms-auto">
                        <li class="nav-item">
                            <span class="navbar-text me-3">
                                <i class="bi bi-clock me-1"></i>
                                <span id="currentTime">Loading...</span>
                            </span>
                        </li>
                        <li class="nav-item">
                            <span class="navbar-text">
                                <i class="bi bi-calendar me-1"></i>
                                <span id="currentDate">Loading...</span>
                            </span>
                        </li>
                    </ul>
                </div>
            </nav>
        `;

        // Insert navbar at the beginning of the body
        document.body.insertAdjacentHTML('afterbegin', navbarHTML);
    }

    createMainNavigation() {
        return `
            <!-- Dashboard -->
            <li class="nav-item">
                <a class="nav-link" href="index.html">
                    <i class="bi bi-speedometer2 me-1"></i>
                    Dashboard
                </a>
            </li>

            <!-- Sales Dropdown -->
            <li class="nav-item dropdown">
                <a class="nav-link dropdown-toggle" href="#" role="button" data-bs-toggle="dropdown">
                    <i class="bi bi-cart me-1"></i>
                    Sales
                </a>
                <ul class="dropdown-menu">
                    <li><h6 class="dropdown-header">Sales Management</h6></li>
                    <li><a class="dropdown-item" href="sales.html">
                        <i class="bi bi-cart-plus"></i>
                        Point of Sale
                    </a></li>
                    <li><a class="dropdown-item" href="sales-history.html">
                        <i class="bi bi-clock-history"></i>
                        Sales History
                    </a></li>
                    <li><a class="dropdown-item" href="customers.html">
                        <i class="bi bi-people"></i>
                        Customers
                    </a></li>
                    <li><a class="dropdown-item" href="invoices.html">
                        <i class="bi bi-receipt"></i>
                        Invoices
                    </a></li>
                    <li><a class="dropdown-item" href="quotations.html">
                        <i class="bi bi-file-text"></i>
                        Quotations
                    </a></li>
                    <li><a class="dropdown-item" href="payments.html">
                        <i class="bi bi-credit-card"></i>
                        Payments
                    </a></li>
                    <li><a class="dropdown-item" href="receipts.html">
                        <i class="bi bi-receipt-cutoff"></i>
                        Receipts
                    </a></li>
                    <li><hr class="dropdown-divider"></li>
                    <li><a class="dropdown-item" href="sales-reports.html">
                        <i class="bi bi-graph-up"></i>
                        Sales Reports
                    </a></li>
                    <li><a class="dropdown-item" href="customer-analytics.html">
                        <i class="bi bi-bar-chart"></i>
                        Customer Analytics
                    </a></li>
                </ul>
            </li>

            <!-- Inventory Dropdown -->
            <li class="nav-item dropdown">
                <a class="nav-link dropdown-toggle" href="#" role="button" data-bs-toggle="dropdown">
                    <i class="bi bi-box me-1"></i>
                    Inventory
                </a>
                <ul class="dropdown-menu">
                    <li><h6 class="dropdown-header">Inventory Management</h6></li>
                    <li><a class="dropdown-item" href="products.html">
                        <i class="bi bi-box-seam"></i>
                        Products
                    </a></li>
                    <li><a class="dropdown-item" href="stock-levels.html">
                        <i class="bi bi-archive"></i>
                        Stock Levels
                    </a></li>
                    <li><a class="dropdown-item" href="inventory-transactions.html">
                        <i class="bi bi-arrow-left-right"></i>
                        Transactions
                    </a></li>
                    <li><a class="dropdown-item" href="adjustments.html">
                        <i class="bi bi-tools"></i>
                        Adjustments
                    </a></li>
                    <li><a class="dropdown-item" href="serial-numbers.html">
                        <i class="bi bi-upc-scan"></i>
                        Serial Numbers
                    </a></li>
                    <li><hr class="dropdown-divider"></li>
                    <li><a class="dropdown-item" href="inventory-reports.html">
                        <i class="bi bi-file-earmark-text"></i>
                        Inventory Reports
                    </a></li>
                    <li><a class="dropdown-item" href="low-stock-alerts.html">
                        <i class="bi bi-exclamation-triangle"></i>
                        Low Stock Alerts
                    </a></li>
                </ul>
            </li>

            <!-- Purchases Dropdown -->
            <li class="nav-item dropdown">
                <a class="nav-link dropdown-toggle" href="#" role="button" data-bs-toggle="dropdown">
                    <i class="bi bi-truck me-1"></i>
                    Purchases
                </a>
                <ul class="dropdown-menu">
                    <li><h6 class="dropdown-header">Purchase Management</h6></li>
                    <li><a class="dropdown-item" href="purchases.html">
                        <i class="bi bi-cart-check"></i>
                        Purchase Orders
                    </a></li>
                    <li><a class="dropdown-item" href="suppliers.html">
                        <i class="bi bi-building"></i>
                        Suppliers
                    </a></li>
                    <li><a class="dropdown-item" href="receipts.html">
                        <i class="bi bi-box-arrow-in-down"></i>
                        Goods Receipts
                    </a></li>
                    <li><a class="dropdown-item" href="purchase-history.html">
                        <i class="bi bi-clock-history"></i>
                        Purchase History
                    </a></li>
                    <li><hr class="dropdown-divider"></li>
                    <li><a class="dropdown-item" href="purchase-reports.html">
                        <i class="bi bi-graph-up"></i>
                        Purchase Reports
                    </a></li>
                    <li><a class="dropdown-item" href="supplier-analytics.html">
                        <i class="bi bi-bar-chart"></i>
                        Supplier Analytics
                    </a></li>
                </ul>
            </li>

            <!-- Accounting Dropdown -->
            <li class="nav-item dropdown">
                <a class="nav-link dropdown-toggle" href="#" role="button" data-bs-toggle="dropdown">
                    <i class="bi bi-calculator me-1"></i>
                    Accounting
                </a>
                <ul class="dropdown-menu">
                    <li><h6 class="dropdown-header">Financial Management</h6></li>
                    <li><a class="dropdown-item" href="accounting-codes.html">
                        <i class="bi bi-diagram-3"></i>
                        Chart of Accounts
                    </a></li>
                    <li><a class="dropdown-item" href="journal-entries.html">
                        <i class="bi bi-journal-text"></i>
                        Journal Entries
                    </a></li>
                    <li><a class="dropdown-item" href="ledgers.html">
                        <i class="bi bi-book"></i>
                        Ledgers
                    </a></li>
                    <li><a class="dropdown-item" href="trial-balance.html">
                        <i class="bi bi-scale"></i>
                        Trial Balance
                    </a></li>
                    <li><hr class="dropdown-divider"></li>
                    <li><a class="dropdown-item" href="balance-sheet.html">
                        <i class="bi bi-file-earmark-spreadsheet"></i>
                        Balance Sheet
                    </a></li>
                    <li><a class="dropdown-item" href="income-statement.html">
                        <i class="bi bi-graph-up-arrow"></i>
                        Income Statement
                    </a></li>
                    <li><a class="dropdown-item" href="cash-flow.html">
                        <i class="bi bi-currency-dollar"></i>
                        Cash Flow
                    </a></li>
                    <li><hr class="dropdown-divider"></li>
                    <li><h6 class="dropdown-header">Cost Accounting</h6></li>
                    <li><a class="dropdown-item" href="cogs.html">
                        <i class="bi bi-tags"></i>
                        Cost of Goods Sold
                    </a></li>
                    <li><a class="dropdown-item" href="cogs-reports.html">
                        <i class="bi bi-graph-up"></i>
                        COGS Reports
                    </a></li>
                    <li><a class="dropdown-item" href="manufacturing.html">
                        <i class="bi bi-gear"></i>
                        Manufacturing Costs
                    </a></li>
                </ul>
            </li>

            <!-- Banking Dropdown -->
            <li class="nav-item dropdown">
                <a class="nav-link dropdown-toggle" href="#" role="button" data-bs-toggle="dropdown">
                    <i class="bi bi-bank me-1"></i>
                    Banking
                </a>
                <ul class="dropdown-menu">
                    <li><h6 class="dropdown-header">Banking Operations</h6></li>
                    <li><a class="dropdown-item" href="bank-accounts.html">
                        <i class="bi bi-credit-card"></i>
                        Bank Accounts
                    </a></li>
                    <li><a class="dropdown-item" href="bank-transactions.html">
                        <i class="bi bi-arrow-left-right"></i>
                        Transactions
                    </a></li>
                    <li><a class="dropdown-item" href="bank-transfers.html">
                        <i class="bi bi-arrow-repeat"></i>
                        Transfers
                    </a></li>
                    <li><a class="dropdown-item" href="bank-reconciliations.html">
                        <i class="bi bi-check2-all"></i>
                        Reconciliations
                    </a></li>
                    <li><hr class="dropdown-divider"></li>
                    <li><a class="dropdown-item" href="bank-reports.html">
                        <i class="bi bi-file-earmark-text"></i>
                        Bank Reports
                    </a></li>
                </ul>
            </li>

            <!-- VAT Dropdown -->
            <li class="nav-item dropdown">
                <a class="nav-link dropdown-toggle" href="#" role="button" data-bs-toggle="dropdown">
                    <i class="bi bi-receipt-cutoff me-1"></i>
                    VAT
                </a>
                <ul class="dropdown-menu">
                    <li><h6 class="dropdown-header">VAT Management</h6></li>
                    <li><a class="dropdown-item" href="vat-reconciliations.html">
                        <i class="bi bi-check2-square"></i>
                        VAT Reconciliations
                    </a></li>
                    <li><a class="dropdown-item" href="vat-payments.html">
                        <i class="bi bi-credit-card"></i>
                        VAT Payments
                    </a></li>
                    <li><a class="dropdown-item" href="vat-reports.html">
                        <i class="bi bi-file-earmark-text"></i>
                        VAT Reports
                    </a></li>
                    <li><a class="dropdown-item" href="vat-settings.html">
                        <i class="bi bi-gear"></i>
                        VAT Settings
                    </a></li>
                </ul>
            </li>

            <!-- Reports Dropdown -->
            <li class="nav-item dropdown">
                <a class="nav-link dropdown-toggle" href="#" role="button" data-bs-toggle="dropdown">
                    <i class="bi bi-graph-up me-1"></i>
                    Reports
                </a>
                <ul class="dropdown-menu">
                    <li><h6 class="dropdown-header">Business Reports</h6></li>
                    <li><a class="dropdown-item" href="sales-reports.html">
                        <i class="bi bi-cart"></i>
                        Sales Reports
                    </a></li>
                    <li><a class="dropdown-item" href="inventory-reports.html">
                        <i class="bi bi-box"></i>
                        Inventory Reports
                    </a></li>
                    <li><a class="dropdown-item" href="financial-reports.html">
                        <i class="bi bi-calculator"></i>
                        Financial Reports
                    </a></li>
                    <li><a class="dropdown-item" href="vat-reports.html">
                        <i class="bi bi-receipt"></i>
                        VAT Reports
                    </a></li>
                    <li><hr class="dropdown-divider"></li>
                    <li><a class="dropdown-item" href="custom-reports.html">
                        <i class="bi bi-file-earmark-plus"></i>
                        Custom Reports
                    </a></li>
                    <li><a class="dropdown-item" href="scheduled-reports.html">
                        <i class="bi bi-clock"></i>
                        Scheduled Reports
                    </a></li>
                </ul>
            </li>
        `;
    }

    createSearchBox() {
        return `
            <form class="d-flex me-3">
                <input class="form-control search-box" type="search" placeholder="Search..." aria-label="Search">
            </form>
        `;
    }

    createQuickActions() {
        return `
            <li class="nav-item dropdown quick-actions">
                <a class="nav-link dropdown-toggle" href="#" role="button" data-bs-toggle="dropdown">
                    <i class="bi bi-lightning me-1"></i>
                    Quick Actions
                </a>
                <ul class="dropdown-menu dropdown-menu-end">
                    <li><h6 class="dropdown-header">Quick Actions</h6></li>
                    <li><a class="dropdown-item" href="sales.html">
                        <i class="bi bi-cart-plus"></i>
                        New Sale
                    </a></li>
                    <li><a class="dropdown-item" href="purchases.html">
                        <i class="bi bi-cart-check"></i>
                        New Purchase
                    </a></li>
                    <li><a class="dropdown-item" href="journal-entries.html">
                        <i class="bi bi-journal-plus"></i>
                        New Journal Entry
                    </a></li>
                    <li><a class="dropdown-item" href="products.html">
                        <i class="bi bi-box-seam"></i>
                        Add Product
                    </a></li>
                    <li><hr class="dropdown-divider"></li>
                    <li><a class="dropdown-item" href="customers.html">
                        <i class="bi bi-person-plus"></i>
                        Add Customer
                    </a></li>
                    <li><a class="dropdown-item" href="suppliers.html">
                        <i class="bi bi-building-add"></i>
                        Add Supplier
                    </a></li>
                </ul>
            </li>
        `;
    }

    createNotifications() {
        return `
            <li class="nav-item dropdown">
                <a class="nav-link position-relative" href="#" role="button" data-bs-toggle="dropdown">
                    <i class="bi bi-bell me-1"></i>
                    <span class="notification-badge" id="notificationCount">0</span>
                </a>
                <ul class="dropdown-menu dropdown-menu-end" id="notificationsList">
                    <li><h6 class="dropdown-header">Notifications</h6></li>
                    <li><div class="dropdown-item text-center">Loading notifications...</div></li>
                </ul>
            </li>
        `;
    }

    createUserMenu() {
        return `
            <li class="nav-item dropdown user-menu">
                <a class="nav-link dropdown-toggle" href="#" role="button" data-bs-toggle="dropdown">
                    <i class="bi bi-person-circle me-1"></i>
                    <span id="userName">Loading...</span>
                </a>
                <ul class="dropdown-menu dropdown-menu-end">
                    <li><h6 class="dropdown-header">User Account</h6></li>
                    <li><a class="dropdown-item" href="profile.html">
                        <i class="bi bi-person"></i>
                        My Profile
                    </a></li>
                    <li><a class="dropdown-item" href="settings.html">
                        <i class="bi bi-gear"></i>
                        Account Settings
                    </a></li>
                    <li><a class="dropdown-item" href="preferences.html">
                        <i class="bi bi-sliders"></i>
                        Preferences
                    </a></li>
                    <li><hr class="dropdown-divider"></li>
                    <li><a class="dropdown-item" href="admin-panel.html">
                        <i class="bi bi-shield-lock"></i>
                        Admin Panel
                        <span class="badge-new">Admin</span>
                    </a></li>
                    <li><a class="dropdown-item" href="system-settings.html">
                        <i class="bi bi-gear-fill"></i>
                        System Settings
                    </a></li>
                    <li><a class="dropdown-item" href="logs-viewer.html">
                        <i class="bi bi-file-text"></i>
                        System Logs
                        <span class="badge-new">New</span>
                    </a></li>
                    <li><hr class="dropdown-divider"></li>
                    <li><a class="dropdown-item" href="help.html">
                        <i class="bi bi-question-circle"></i>
                        Help & Support
                    </a></li>
                    <li><a class="dropdown-item" href="about.html">
                        <i class="bi bi-info-circle"></i>
                        About CNPERP
                    </a></li>
                    <li><hr class="dropdown-divider"></li>
                    <li><a class="dropdown-item text-danger" href="#" onclick="cnperpNavbar.logout()">
                        <i class="bi bi-box-arrow-right"></i>
                        Logout
                    </a></li>
                </ul>
            </li>
        `;
    }

    bindEvents() {
        // Search functionality
        const searchBox = document.querySelector('.search-box');
        if (searchBox) {
            searchBox.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') {
                    e.preventDefault();
                    this.performSearch(searchBox.value.trim());
                }
            });
        }

        // Notification clicks
        document.addEventListener('click', (e) => {
            if (e.target.closest('.dropdown-item') && e.target.closest('#notificationsList')) {
                e.preventDefault();
                const notificationText = e.target.closest('.dropdown-item').textContent;
                this.handleNotificationClick(notificationText);
            }
        });

        // Active page highlighting
        this.highlightCurrentPage();
    }

    updateDateTime() {
        const updateTime = () => {
            const now = new Date();

            // Update time
            const timeString = now.toLocaleTimeString('en-US', {
                hour12: true,
                hour: '2-digit',
                minute: '2-digit',
                second: '2-digit'
            });
            const timeElement = document.getElementById('currentTime');
            if (timeElement) timeElement.textContent = timeString;

            // Update date
            const dateString = now.toLocaleDateString('en-US', {
                weekday: 'long',
                year: 'numeric',
                month: 'long',
                day: 'numeric'
            });
            const dateElement = document.getElementById('currentDate');
            if (dateElement) dateElement.textContent = dateString;
        };

        updateTime();
        setInterval(updateTime, 1000);
    }

    async loadUserData() {
        try {
            // Simulate API call to get user data
            this.currentUser = {
                name: 'Admin User',
                email: 'admin@cnperp.com',
                role: 'admin',
                branch: 'Main Office'
            };

            // Update UI
            const userNameElement = document.getElementById('userName');
            if (userNameElement) {
                userNameElement.textContent = this.currentUser.name;
            }

            const branchElement = document.getElementById('currentBranch');
            if (branchElement) {
                branchElement.textContent = this.currentUser.branch;
            }

        } catch (error) {
            console.error('Error loading user data:', error);
        }
    }

    async loadNotifications() {
        try {
            // Simulate API call to get notifications
            this.notifications = [
                {
                    id: 1,
                    type: 'warning',
                    icon: 'bi-exclamation-triangle',
                    message: 'Low stock alert: Product XYZ',
                    time: '2 minutes ago'
                },
                {
                    id: 2,
                    type: 'success',
                    icon: 'bi-check-circle',
                    message: 'Payment received: Invoice #1234',
                    time: '5 minutes ago'
                },
                {
                    id: 3,
                    type: 'info',
                    icon: 'bi-info-circle',
                    message: 'System backup completed',
                    time: '1 hour ago'
                }
            ];

            this.updateNotificationsUI();

        } catch (error) {
            console.error('Error loading notifications:', error);
        }
    }

    updateNotificationsUI() {
        const notificationsList = document.getElementById('notificationsList');
        const notificationCount = document.getElementById('notificationCount');

        if (notificationsList) {
            notificationsList.innerHTML = `
                <li><h6 class="dropdown-header">Notifications</h6></li>
                ${this.notifications.map(notification => `
                    <li><a class="dropdown-item" href="#" data-notification-id="${notification.id}">
                        <i class="bi ${notification.icon} text-${notification.type}"></i>
                        ${notification.message}
                        <small class="text-muted d-block">${notification.time}</small>
                    </a></li>
                `).join('')}
                <li><hr class="dropdown-divider"></li>
                <li><a class="dropdown-item text-center" href="notifications.html">
                    View All Notifications
                </a></li>
            `;
        }

        if (notificationCount) {
            notificationCount.textContent = this.notifications.length;
        }
    }

    performSearch(searchTerm) {
        if (searchTerm) {
            console.log(`Searching for: ${searchTerm}`);
            // In a real application, this would perform the search
            alert(`Searching for: ${searchTerm}`);
        }
    }

    handleNotificationClick(notificationText) {
        console.log('Notification clicked:', notificationText);
        alert(`Notification clicked: ${notificationText}`);
    }

    highlightCurrentPage() {
        const currentPage = window.location.pathname.split('/').pop() || 'index.html';
        const navLinks = document.querySelectorAll('.nav-link');

        navLinks.forEach(link => {
            if (link.getAttribute('href') === currentPage) {
                link.classList.add('active');
            }
        });
    }

    logout() {
        if (confirm('Are you sure you want to logout?')) {
            console.log('Logging out...');
            // In a real application, this would redirect to login page
            alert('Logging out...');
            // window.location.href = 'login.html';
        }
    }

    // Public methods for external use
    updateNotifications(newNotifications) {
        this.notifications = newNotifications;
        this.updateNotificationsUI();
    }

    updateUserData(newUserData) {
        this.currentUser = { ...this.currentUser, ...newUserData };
        this.loadUserData();
    }

    setActivePage(pageName) {
        const navLinks = document.querySelectorAll('.nav-link');
        navLinks.forEach(link => {
            link.classList.remove('active');
            if (link.getAttribute('href') === pageName) {
                link.classList.add('active');
            }
        });
    }
}

// Global instance
let cnperpNavbar;

// Initialize navbar when DOM is loaded
document.addEventListener('DOMContentLoaded', function () {
    cnperpNavbar = new CNPERPNavbar({
        brandName: 'CNPERP ERP',
        brandIcon: 'bi-building',
        showSearch: true,
        showNotifications: true,
        showQuickActions: true,
        showUserMenu: true
    });
});

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
    module.exports = CNPERPNavbar;
}
