/**
 * Centralized API Configuration for CNPERP Application
 * 
 * This file provides a single source of truth for all API endpoints
 * and automatically detects the correct base URL based on environment.
 * 
 * Usage in HTML files:
 * <script src="js/api-config.js"></script>
 * <script>
 *   // Use API_CONFIG.BASE_URL instead of hardcoded URLs
 *   const response = await fetch(`${API_CONFIG.BASE_URL}/sales/customers`);
 *   
 *   // Or use predefined endpoints
 *   const response = await fetch(API_CONFIG.ENDPOINTS.CUSTOMERS);
 * </script>
 */

(function(window) {
    'use strict';

    // Detect environment and set base URL
    function detectApiBaseUrl() {
        const hostname = window.location.hostname;
        const protocol = window.location.protocol;
        
        // Development environment detection
        if (hostname === 'localhost' || hostname === '127.0.0.1') {
            return `${protocol}//${hostname}:8010/api/v1`;
        }
        
        // Production environment - use relative path
        return '/api/v1';
    }

    // Global API Configuration Object
    window.API_CONFIG = {
        // Base URL with automatic environment detection
        BASE_URL: detectApiBaseUrl(),
        
        // Version for cache busting
        VERSION: '20250127120000',
        
        // Common endpoint patterns
        ENDPOINTS: {
            // Sales Module
            SALES: detectApiBaseUrl() + '/sales',
            SALES_CUSTOMERS: detectApiBaseUrl() + '/sales/customers',
            SALES_EXPORT: detectApiBaseUrl() + '/sales/export',
            SALES_STATISTICS: detectApiBaseUrl() + '/sales/statistics',
            
            // Inventory Module
            INVENTORY_PRODUCTS: detectApiBaseUrl() + '/inventory/products',
            INVENTORY_UNITS: detectApiBaseUrl() + '/inventory/units-of-measure',
            
            // Purchases Module
            PURCHASES: detectApiBaseUrl() + '/purchases/purchases',
            SUPPLIERS: detectApiBaseUrl() + '/purchases/suppliers',
            PURCHASE_PRODUCTS: detectApiBaseUrl() + '/purchases/products',
            PURCHASE_DASHBOARD: detectApiBaseUrl() + '/purchases/dashboard-stats',
            
            // Accounting Module
            ACCOUNTING_CODES: detectApiBaseUrl() + '/accounting-codes/',
            GENERAL_LEDGER: detectApiBaseUrl() + '/general-ledger/general-ledger',
            TRIAL_BALANCE: detectApiBaseUrl() + '/general-ledger/trial-balance',
            
            // Banking Module
            BANKING_ACCOUNTS: detectApiBaseUrl() + '/banking/accounts',
            BANKING: detectApiBaseUrl() + '/banking',
            
            // Reports Module
            REPORTS_DEBTORS_AGING: detectApiBaseUrl() + '/reports/debtors-aging',
            REPORTS_CREDITORS_AGING: detectApiBaseUrl() + '/reports/creditors-aging',
            REPORTS_TRIAL_BALANCE: detectApiBaseUrl() + '/reports/trial-balance',
            REPORTS_BALANCE_SHEET: detectApiBaseUrl() + '/reports/balance-sheet',
            REPORTS_SALES_REPORT: detectApiBaseUrl() + '/reports/management/sales-report',
            REPORTS_PERFORMANCE_DASHBOARD: detectApiBaseUrl() + '/reports/performance/dashboard',
            REPORTS_KPI_METRICS: detectApiBaseUrl() + '/reports/management/kpi-metrics',
            REPORTS_CUSTOMER_ANALYSIS: detectApiBaseUrl() + '/reports/management/customer-analysis',
            REPORTS_PERFORMANCE_METRICS: detectApiBaseUrl() + '/reports/management/performance-metrics',
            REPORTS_FINANCIAL_DASHBOARD: detectApiBaseUrl() + '/reports/financial/dashboard',
            
            // Inventory Reports
            REPORTS_INVENTORY_SUMMARY: detectApiBaseUrl() + '/reports/inventory/summary',
            REPORTS_INVENTORY_CATEGORY: detectApiBaseUrl() + '/reports/inventory/category-analysis',
            REPORTS_INVENTORY_VALUATION: detectApiBaseUrl() + '/reports/inventory/valuation-methods',
            REPORTS_INVENTORY_MOVEMENT: detectApiBaseUrl() + '/reports/inventory/stock-movement',
            REPORTS_INVENTORY_AGING: detectApiBaseUrl() + '/reports/inventory/aging-analysis',
            REPORTS_INVENTORY_ABC: detectApiBaseUrl() + '/reports/inventory/abc-analysis',
            
            // COGS Reports
            REPORTS_COGS_MONTHLY: detectApiBaseUrl() + '/reports/cogs/monthly',
            REPORTS_COGS_TREND: detectApiBaseUrl() + '/reports/cogs/trend-analysis',
            
            // Invoice Module
            INVOICES: detectApiBaseUrl() + '/invoices',
            
            // Quotations Module
            QUOTATIONS: detectApiBaseUrl() + '/quotations',
            
            // Job Cards Module
            JOB_CARDS: detectApiBaseUrl() + '/job-cards',
            
            // COGS Module
            COGS: detectApiBaseUrl() + '/cogs/',
            MANUFACTURING: detectApiBaseUrl() + '/manufacturing/',
            
            // Settings Module
            SETTINGS: detectApiBaseUrl() + '/settings/',
            SETTINGS_CURRENCY: detectApiBaseUrl() + '/settings/currency',
            APP_SETTINGS: detectApiBaseUrl() + '/settings/', // Standardized to /settings/
            
            // User Management
            USERS: detectApiBaseUrl() + '/users',
            BRANCHES: detectApiBaseUrl() + '/branches',
            BRANCHES_PUBLIC: detectApiBaseUrl() + '/branches/public',
            
            // VAT Module
            VAT_TRACKING: detectApiBaseUrl() + '/vat/tracking',
            
            // POS Module
            POS_SALES: detectApiBaseUrl() + '/pos/sales',
            
            // Documents/Printing
            DOCUMENTS_PRINT: detectApiBaseUrl() + '/documents/print',
            
            // Asset Management
            ASSET_MANAGEMENT: detectApiBaseUrl() + '/asset-management',
            
            // Backup Management
            BACKUP: detectApiBaseUrl() + '/backup/',
            BACKUP_CREATE: detectApiBaseUrl() + '/backup/create',
            BACKUP_CONFIG: detectApiBaseUrl() + '/backup/config',
            BACKUP_STATUS: detectApiBaseUrl() + '/backup/status/summary'
        },
        
        // Helper functions
        buildUrl: function(endpoint, params = {}) {
            let url = this.BASE_URL + endpoint;
            const queryParams = new URLSearchParams(params);
            if (queryParams.toString()) {
                url += '?' + queryParams.toString();
            }
            return url;
        },
        
        // Add cache-busting parameter to URLs
        withCacheBuster: function(url) {
            const separator = url.includes('?') ? '&' : '?';
            return `${url}${separator}_=${this.VERSION}`;
        },
        
        // Environment info
        getEnvironmentInfo: function() {
            return {
                hostname: window.location.hostname,
                isProduction: !['localhost', '127.0.0.1'].includes(window.location.hostname),
                baseUrl: this.BASE_URL,
                version: this.VERSION
            };
        }
    };

    // Legacy compatibility - provide old variable names
    window.API_BASE = API_CONFIG.BASE_URL;
    window.apiBaseUrl = API_CONFIG.BASE_URL;

    // Console info for debugging
    console.log('🚀 API Config Loaded:', API_CONFIG.getEnvironmentInfo());

})(window);