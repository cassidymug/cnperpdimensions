// Modern UI Kit for CNPERP
// File: /app/static/js/modern-ui.js

// --- Notification System ---
function showNotification(message, type = 'info', duration = 3000) {
    const container = document.getElementById('notification-container') || createNotificationContainer();
    
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.textContent = message;
    
    container.appendChild(notification);
    
    setTimeout(() => {
        notification.style.opacity = '0';
        setTimeout(() => notification.remove(), 500);
    }, duration);
}

function createNotificationContainer() {
    const container = document.createElement('div');
    container.id = 'notification-container';
    document.body.appendChild(container);
    return container;
}

// --- Navbar Creation ---
function createNavbar(activePage) {
    const pages = [
        { name: 'Chart of Accounts', href: 'chart-of-accounts.html', icon: 'bi-list-ul', id: 'chart-of-accounts' },
        { name: 'Bank Accounts', href: 'bank-accounts.html', icon: 'bi-bank', id: 'bank-accounts' },
        { name: 'Journal Entries', href: 'journal-entries.html', icon: 'bi-journal-text', id: 'journal-entries' }
    ];

    let navLinks = '';
    pages.forEach(page => {
        const isActive = activePage === page.id ? 'active' : '';
        navLinks += `
            <li class="nav-item">
                <a class="nav-link ${isActive}" href="${page.href}">
                    <i class="bi ${page.icon} me-2"></i>${page.name}
                </a>
            </li>
        `;
    });

    const navbarHTML = `
        <nav class="navbar navbar-expand-lg navbar-dark bg-primary mb-4">
            <div class="container-fluid">
                <a class="navbar-brand" href="#">
                    <i class="bi bi-building me-2"></i>CNPERP
                </a>
                <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#mainNavbar">
                    <span class="navbar-toggler-icon"></span>
                </button>
                <div class="collapse navbar-collapse" id="mainNavbar">
                    <ul class="navbar-nav me-auto mb-2 mb-lg-0">
                        ${navLinks}
                    </ul>
                    <span class="navbar-text">
                        <i class="bi bi-calendar-event me-2"></i> ${new Date().toDateString()}
                    </span>
                </div>
            </div>
        </nav>
    `;
    
    return navbarHTML;
}

// --- DOM Ready ---
document.addEventListener('DOMContentLoaded', () => {
    // Inject notification container CSS
    const style = document.createElement('style');
    style.textContent = `
        #notification-container {
            position: fixed;
            top: 20px;
            right: 20px;
            z-index: 9999;
        }
        .notification {
            background-color: #333;
            color: white;
            padding: 15px;
            border-radius: 5px;
            margin-bottom: 10px;
            opacity: 1;
            transition: opacity 0.5s;
        }
        .notification-success { background-color: #28a745; }
        .notification-error { background-color: #dc3545; }
        .notification-warning { background-color: #ffc107; }
    `;
    document.head.appendChild(style);

    // Auto-initialize navbar if a container is present
    if (document.getElementById('navbar-container')) {
        const pageId = document.body.dataset.pageId || '';
        createNavbar(pageId);
    }
});
