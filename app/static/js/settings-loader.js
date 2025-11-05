// CNPERP ERP System - Centralized Settings Loader
// This utility provides centralized access to application settings across all modules

class SettingsLoader {
    constructor() {
        this.settings = {
            currency: null,
            business: null,
            theme: null,
            inventory: null,
            sales: null,
            purchase: null,
            vat: null,
            security: null
        };
        this.isLoaded = false;
        this.loadingPromise = null;
    }

    // Initialize settings loading
    async init() {
        if (this.loadingPromise) {
            return this.loadingPromise;
        }

        this.loadingPromise = this.loadAllSettings();
        return this.loadingPromise;
    }

    // Load all application settings
    async loadAllSettings() {
        try {
            console.log('🔄 Loading application settings...');
            
            // Load all settings in parallel
            const [
                currencySettings,
                businessSettings,
                themeSettings,
                inventorySettings,
                salesSettings,
                purchaseSettings,
                vatSettings,
                securitySettings
            ] = await Promise.all([
                this.fetchSettings('/api/v1/settings/currency'),
                this.fetchSettings('/api/v1/settings/business'),
                this.fetchSettings('/api/v1/settings/theme'),
                this.fetchSettings('/api/v1/settings/inventory'),
                this.fetchSettings('/api/v1/settings/sales'),
                this.fetchSettings('/api/v1/settings/purchase'),
                this.fetchSettings('/api/v1/settings/vat'),
                this.fetchSettings('/api/v1/settings/security')
            ]);

            // Store settings
            this.settings.currency = currencySettings;
            this.settings.business = businessSettings;
            this.settings.theme = themeSettings;
            this.settings.inventory = inventorySettings;
            this.settings.sales = salesSettings;
            this.settings.purchase = purchaseSettings;
            this.settings.vat = vatSettings;
            this.settings.security = securitySettings;

            this.isLoaded = true;
            console.log('✅ Application settings loaded successfully');
            
            // Dispatch event for other modules
            document.dispatchEvent(new CustomEvent('settingsLoaded', { 
                detail: { settings: this.settings } 
            }));

            return this.settings;

        } catch (error) {
            console.error('❌ Error loading application settings:', error);
            throw error;
        }
    }

    // Fetch settings from API
    async fetchSettings(endpoint) {
        try {
            const response = await fetch(endpoint);
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            const result = await response.json();
            return result.data || result;
        } catch (error) {
            console.warn(`⚠️ Failed to load settings from ${endpoint}:`, error);
            return this.getDefaultSettings(endpoint);
        }
    }

    // Get default settings as fallback
    getDefaultSettings(endpoint) {
        const defaults = {
            '/api/v1/settings/currency': {
                currency: 'BWP',
                currency_symbol: 'P',
                currency_code: 'BWP',
                vat_rate: 14.0,
                default_vat_rate: 14.0,
                country: 'BW',
                locale: 'en',
                timezone: 'Africa/Gaborone'
            },
            '/api/v1/settings/business': {
                company_name: 'Your Company Name',
                app_name: 'CNPERP ERP System',
                address: '123 Business St, City, Country',
                phone: '+123 456 7890',
                email: 'info@example.com',
                website: 'www.your-erp-app.com',
                fiscal_year_start: '01-01',
                default_payment_terms: 30,
                late_payment_penalty: 0.0,
                early_payment_discount: 0.0
            },
            '/api/v1/settings/theme': {
                theme_mode: 'light',
                primary_color: '#0d6efd',
                secondary_color: '#6c757d',
                accent_color: '#198754',
                dark_mode_enabled: false
            },
            '/api/v1/settings/inventory': {
                default_warehouse: 'Main Warehouse',
                low_stock_threshold: 10,
                auto_reorder_enabled: false,
                inventory_valuation_method: 'FIFO'
            },
            '/api/v1/settings/sales': {
                default_payment_method: 'cash',
                invoice_prefix: 'INV',
                quote_prefix: 'QT',
                default_terms: 30
            },
            '/api/v1/settings/purchase': {
                default_supplier: null,
                purchase_order_prefix: 'PO',
                default_terms: 30,
                auto_approve_purchases: false
            },
            '/api/v1/settings/vat': {
                vat_enabled: true,
                vat_rate: 14.0,
                vat_number: '',
                vat_registration_date: null
            },
            '/api/v1/settings/security': {
                password_min_length: 8,
                require_special_chars: true,
                session_timeout: 30,
                max_login_attempts: 5
            }
        };

        return defaults[endpoint] || {};
    }

    // Get specific setting value
    getSetting(category, key) {
        if (!this.isLoaded) {
            console.warn('⚠️ Settings not loaded yet. Call await settingsLoader.init() first.');
            return null;
        }
        return this.settings[category]?.[key];
    }

    // Get currency settings
    getCurrencySettings() {
        return this.settings.currency || this.getDefaultSettings('/api/v1/settings/currency');
    }

    // Get business settings
    getBusinessSettings() {
        return this.settings.business || this.getDefaultSettings('/api/v1/settings/business');
    }

    // Get VAT settings
    getVatSettings() {
        return this.settings.vat || this.getDefaultSettings('/api/v1/settings/vat');
    }

    // Format currency amount
    formatCurrency(amount, currency = null) {
        const currencySettings = this.getCurrencySettings();
        const symbol = currency || currencySettings.currency_symbol || 'P';
        const locale = currencySettings.locale || 'en';
        const country = currencySettings.country || 'BW';
        
        try {
            return new Intl.NumberFormat(`${locale}-${country}`, {
                style: 'currency',
                currency: currencySettings.currency || 'BWP',
                minimumFractionDigits: 2,
                maximumFractionDigits: 2
            }).format(amount);
        } catch (error) {
            // Fallback formatting
            return `${symbol}${Number(amount).toLocaleString('en-BW', {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2
            })}`;
        }
    }

    // Format percentage
    formatPercentage(value, decimals = 2) {
        return `${Number(value).toFixed(decimals)}%`;
    }

    // Calculate VAT amount
    calculateVat(amount, vatRate = null) {
        const vatSettings = this.getVatSettings();
        const rate = vatRate || vatSettings.vat_rate || 14.0;
        return (amount * rate) / 100;
    }

    // Get current date in fiscal year format
    getFiscalYearDate() {
        const businessSettings = this.getBusinessSettings();
        const fiscalStart = businessSettings.fiscal_year_start || '01-01';
        const [month, day] = fiscalStart.split('-');
        
        const now = new Date();
        const currentYear = now.getFullYear();
        const fiscalYearStart = new Date(currentYear, parseInt(month) - 1, parseInt(day));
        
        if (now < fiscalYearStart) {
            return new Date(currentYear - 1, parseInt(month) - 1, parseInt(day));
        }
        
        return fiscalYearStart;
    }

    // Get company information
    getCompanyInfo() {
        const businessSettings = this.getBusinessSettings();
        return {
            name: businessSettings.company_name || 'Your Company Name',
            address: businessSettings.address || '123 Business St, City, Country',
            phone: businessSettings.phone || '+123 456 7890',
            email: businessSettings.email || 'info@example.com',
            website: businessSettings.website || 'www.your-erp-app.com'
        };
    }

    // Update settings (for admin use)
    async updateSettings(category, settings) {
        try {
            const response = await fetch(`/api/v1/settings/${category}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(settings)
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            // Reload settings
            await this.loadAllSettings();
            return true;
        } catch (error) {
            console.error('❌ Error updating settings:', error);
            throw error;
        }
    }

    // Check if settings are loaded
    isSettingsLoaded() {
        return this.isLoaded;
    }

    // Get all settings
    getAllSettings() {
        return this.settings;
    }

    // Refresh settings
    async refresh() {
        this.isLoaded = false;
        this.loadingPromise = null;
        return await this.init();
    }
}

// Create global instance
window.settingsLoader = new SettingsLoader();

// Auto-initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    window.settingsLoader.init().catch(error => {
        console.error('❌ Failed to initialize settings loader:', error);
    });
});

// Export for module use
if (typeof module !== 'undefined' && module.exports) {
    module.exports = SettingsLoader;
}
