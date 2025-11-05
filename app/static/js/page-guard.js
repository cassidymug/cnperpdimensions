// Page Access Guard - Restrict POS users to POS page only
console.log('🔒 page-guard.js loaded - version 20250121');

(function () {
    'use strict';

    // Get user from localStorage
    const user = JSON.parse(localStorage.getItem('user') || '{}');
    const role = (user.role || '').toLowerCase();
    const currentPath = window.location.pathname;

    // POS users can ONLY access pos.html and login.html
    if (role === 'pos_user' || role === 'cashier') {
        const allowedPages = [
            '/static/pos.html',
            '/static/login.html',
            '/static/logout.html',
            '/login.html',
            '/logout'
        ];

        // Check if current page is allowed
        const isAllowed = allowedPages.some(page => currentPath.includes(page));

        if (!isAllowed) {
            console.warn('🚫 POS user attempted to access restricted page:', currentPath);
            console.log('🔄 Redirecting to POS...');
            window.location.replace('/static/pos.html');
        } else {
            console.log('✅ POS user accessing allowed page:', currentPath);
        }
    }
})();
