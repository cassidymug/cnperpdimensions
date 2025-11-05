// Deprecated: navbar-fallback is no longer used. The standardized navbar is injected by navbar.js
document.addEventListener('DOMContentLoaded', function(){
    // Intentionally left blank to avoid conflicting with the standardized navbar
});
// Simple navbar with Quotations link for immediate testing
document.addEventListener('DOMContentLoaded', function() {
    const navbarContainer = document.getElementById('navbar-container');
    if (navbarContainer && navbarContainer.innerHTML.trim() === '') {
        navbarContainer.innerHTML = `
            <nav class="navbar navbar-expand-lg navbar-dark bg-primary fixed-top">
                <div class="container-fluid">
                    <a class="navbar-brand fw-bold" href="/static/index.html">
                        <i class="bi bi-building me-2"></i>CNPERP ERP
                    </a>
                    
                    <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarContent">
                        <span class="navbar-toggler-icon"></span>
                    </button>

                    <div class="collapse navbar-collapse" id="navbarContent">
                        <ul class="navbar-nav me-auto">
                            <li class="nav-item">
                                <a class="nav-link" href="/static/index.html">
                                    <i class="bi bi-speedometer2 me-1"></i>Dashboard
                                </a>
                            </li>
                            <li class="nav-item dropdown">
                                <a class="nav-link dropdown-toggle" href="#" role="button" data-bs-toggle="dropdown" aria-expanded="false">
                                    <i class="bi bi-cart me-1"></i>Sales
                                </a>
                                <ul class="dropdown-menu">
                                    <li><a class="dropdown-item" href="/static/pos.html">POS</a></li>
                                    <li><a class="dropdown-item" href="/static/sales.html">Sales</a></li>
                                    <li><a class="dropdown-item" href="/static/customers.html">Customers</a></li>
                                    <li><a class="dropdown-item" href="/static/invoices.html">Invoices</a></li>
                                    <li><a class="dropdown-item" href="/static/credit-notes.html">Credit Notes</a></li>
                                    <li><a class="dropdown-item" href="/static/receipts.html">Receipts</a></li>
                                        <li><a class="dropdown-item" href="/static/quotations.html">Quotations</a></li>
                                        <li><a class="dropdown-item" href="/static/job-cards.html">Job Cards</a></li>
                                        <li><hr class="dropdown-divider"></li>
                                    <li><a class="dropdown-item" href="/static/sales-reports.html">Sales Reports</a></li>
                                </ul>
                            </li>
                        </ul>
                    </div>
                </div>
            </nav>
        `;
        console.log('✅ Fallback navbar with Quotations loaded');
    }
});