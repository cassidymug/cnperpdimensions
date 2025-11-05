/**
 * CNPERP Core JavaScript Library
 * Provides unified API client, configuration, and utility functions
 * Version: 1.0.0
 */

// Global Configuration
window.CNPERP = window.CNPERP || {};

// Configuration Management
window.CNPERP.Config = {
    API_BASE: 'http://localhost:8010/api/v1',
    ENDPOINTS: {
        auth: '/auth',
        purchases: '/purchases',
        banking: '/banking',
        accounting: '/accounting',
        accounting_codes: '/accounting-codes',
        assets: '/asset-management',
        inventory: '/inventory',
        sales: '/sales',
        reports: '/reports'
    },
    UI: {
        dateFormat: 'YYYY-MM-DD',
        currencySymbol: 'P',
        pageSize: 25,
        errorDisplayDuration: 5000
    },
    SYSTEM_NAME: 'CNPERP ERP'
};

// Unified API Client
window.CNPERP.API = {
    /**
     * Make API request with unified error handling
     */
    async request(endpoint, options = {}) {
        const url = endpoint.startsWith('http') ? endpoint : `${window.CNPERP.Config.API_BASE}${endpoint}`;
        
        const defaultOptions = {
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }
        };
        
        const finalOptions = { ...defaultOptions, ...options };
        
        if (finalOptions.body && typeof finalOptions.body === 'object') {
            finalOptions.body = JSON.stringify(finalOptions.body);
        }
        
        try {
            console.log(`🔗 API Request: ${finalOptions.method || 'GET'} ${url}`);

            const response = await fetch(url, finalOptions);

            // Attempt to parse JSON; fall back to text if needed
            let parsedBody = null;
            let rawText = null;
            const contentType = response.headers.get('content-type') || '';
            try {
                if (contentType.includes('application/json')) {
                    parsedBody = await response.json();
                } else {
                    rawText = await response.text();
                }
            } catch (parseErr) {
                // Ignore parse errors; we'll surface minimal info below
                try { rawText = await response.text(); } catch {}
            }

            if (!response.ok) {
                const err = new Error(
                    (parsedBody && (parsedBody.message || parsedBody.detail || parsedBody.error?.message)) ||
                    rawText ||
                    `HTTP ${response.status}`
                );
                // Attach rich context for UI handlers
                err.status = response.status;
                err.statusText = response.statusText;
                err.url = url;
                err.data = parsedBody;
                err.raw = rawText;
                console.error(`❌ API Error: ${url}`, { status: err.status, data: err.data, raw: err.raw });
                throw err;
            }

            const data = parsedBody !== null ? parsedBody : rawText;
            console.log(`✅ API Success: ${url}`, data);
            return data;

        } catch (error) {
            console.error(`❌ API Error: ${url}`, error);
            throw error;
        }
    },
    
    // HTTP Method Shortcuts
    async get(endpoint, params = {}) {
        const url = new URL(endpoint.startsWith('http') ? endpoint : `${window.CNPERP.Config.API_BASE}${endpoint}`);
        Object.keys(params).forEach(key => url.searchParams.append(key, params[key]));
        return this.request(url.toString());
    },
    
    async post(endpoint, data = {}) {
        return this.request(endpoint, {
            method: 'POST',
            body: data
        });
    },
    
    async put(endpoint, data = {}) {
        return this.request(endpoint, {
            method: 'PUT',
            body: data
        });
    },
    
    async delete(endpoint) {
        return this.request(endpoint, {
            method: 'DELETE'
        });
    }
};

// Data Utilities
window.CNPERP.Utils = {
    /**
     * Get product tax status (returns true/false)
     */
    getProductTaxStatus(product) {
        return product && typeof product.is_taxable !== 'undefined' ? !!product.is_taxable : true;
    },
    /**
     * Format currency value
     */
    formatCurrency(amount, showSymbol = true) {
        if (!amount && amount !== 0) return showSymbol ? `${window.CNPERP.Config.UI.currencySymbol} 0.00` : '0.00';
        const formatted = parseFloat(amount).toLocaleString('en-US', {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        });
        return showSymbol ? `${window.CNPERP.Config.UI.currencySymbol} ${formatted}` : formatted;
    },
    
    /**
     * Format date
     */
    formatDate(dateString) {
        if (!dateString) return 'N/A';
        try {
            return new Date(dateString).toLocaleDateString();
        } catch {
            return 'Invalid Date';
        }
    },
    
    /**
     * Escape HTML
     */
    escapeHtml(text) {
        if (!text) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    },
    
    /**
     * Debounce function
     */
    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    },
    
    /**
     * Extract data from API response
     */
    extractData(response) {
        // Handle unified response format
        if (response && typeof response === 'object') {
            if ('success' in response && 'data' in response) {
                return response.data;
            }
            if ('data' in response) {
                return response.data;
            }
        }
        // Return as-is if it's already an array or simple object
        return response;
    },

    /**
     * Normalize error object to a user-friendly message
     */
    getErrorMessage(error) {
        try {
            if (!error) return 'An unknown error occurred';
            // Prefer server-provided details
            const d = error.data;
            if (d) {
                if (typeof d === 'string') return d;
                if (typeof d.message === 'string' && d.message.trim()) return d.message;
                if (typeof d.detail === 'string' && d.detail.trim()) return d.detail;
                if (d.error && typeof d.error.message === 'string' && d.error.message.trim()) return d.error.message;
            }
            // Fallback to Error.message
            if (typeof error.message === 'string' && error.message.trim()) return error.message;
            // Include status if available
            if (error.status) return `Request failed with status ${error.status}`;
            return 'Request failed';
        } catch {
            return 'Request failed';
        }
    }
};

// UI Components
window.CNPERP.UI = {
    /**
     * Show notification
     */
    showNotification(message, type = 'info', duration = 5000) {
        // Create notification element
        const notification = document.createElement('div');
        notification.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
        notification.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
        notification.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        document.body.appendChild(notification);
        
        // Auto-remove after duration
        setTimeout(() => {
            if (notification.parentNode) {
                notification.remove();
            }
        }, duration);
    },
    
    /**
     * Show loading state
     */
    showLoading(element, show = true) {
        if (show) {
            element.innerHTML = `
                <div class="d-flex justify-content-center align-items-center" style="height: 100px;">
                    <div class="spinner-border text-primary" role="status">
                        <span class="visually-hidden">Loading...</span>
                    </div>
                </div>
            `;
        }
    },
    
    /**
     * Populate select dropdown
     */
    populateSelect(selectElement, items, valueField = 'id', textField = 'name', placeholder = 'Select...') {
        if (!selectElement) return;
        
        selectElement.innerHTML = `<option value="">${placeholder}</option>`;
        
        const data = window.CNPERP.Utils.extractData(items);
        if (Array.isArray(data)) {
            data.forEach(item => {
                const option = document.createElement('option');
                option.value = item[valueField] || '';
                option.textContent = item[textField] || 'Unnamed';
                selectElement.appendChild(option);
            });
        }
    }
};

// Error Handling
window.CNPERP.ErrorHandler = {
    handle(error, context = 'Application') {
        console.error(`${context} Error:`, error);
        
        const message = window.CNPERP.Utils.getErrorMessage(error);
        window.CNPERP.UI.showNotification(message, 'danger');
    }
};

// Page Initialization Helper
window.CNPERP.initPage = function(pageName, initFunction) {
    document.addEventListener('DOMContentLoaded', async function() {
        try {
            console.log(`🚀 Initializing ${pageName} page...`);
            await initFunction();
            console.log(`✅ ${pageName} page initialized successfully`);
        } catch (error) {
            console.error(`❌ Failed to initialize ${pageName} page:`, error);
            window.CNPERP.ErrorHandler.handle(error, pageName);
        }
    });
};

console.log('✅ CNPERP Core Library loaded successfully');
console.log('🔧 API Base:', window.CNPERP.Config.API_BASE);