/**
 * CNPERP Currency Utilities
 * Ensures consistent currency display across all views using centralized settings
 */

// Global currency settings - will be populated from settings loader
window.CNPERP_CURRENCY = {
    code: 'BWP',
    symbol: 'P',
    name: 'Botswana Pula',
    vatRate: 14.0,
    locale: 'en-BW'
};

/**
 * Format currency amount with proper symbol from settings
 * @param {number} amount - The amount to format
 * @param {boolean} showSymbol - Whether to show the currency symbol
 * @returns {string} Formatted currency string
 */
function formatCurrency(amount, showSymbol = true) {
    if (amount === null || amount === undefined) return '';
    
    // Use settings loader if available, otherwise fall back to defaults
    if (window.settingsLoader && window.settingsLoader.isSettingsLoaded()) {
        return window.settingsLoader.formatCurrency(amount);
    }
    
    // Fallback formatting
    const formatted = new Intl.NumberFormat('en-BW', {
        style: 'currency',
        currency: CNPERP_CURRENCY.code,
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    }).format(amount);
    
    return showSymbol ? formatted : formatted.replace(CNPERP_CURRENCY.symbol, '').trim();
}

/**
 * Format currency without symbol (just the number)
 * @param {number} amount - The amount to format
 * @returns {string} Formatted number string
 */
function formatAmount(amount) {
    if (amount === null || amount === undefined) return '';
    
    // Use settings loader if available
    if (window.settingsLoader && window.settingsLoader.isSettingsLoaded()) {
        const currencySettings = window.settingsLoader.getCurrencySettings();
        return new Intl.NumberFormat(`${currencySettings.locale}-${currencySettings.country}`, {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        }).format(amount);
    }
    
    // Fallback formatting
    return new Intl.NumberFormat('en-BW', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    }).format(amount);
}

/**
 * Update all currency displays on the page
 */
function updateAllCurrencyDisplays() {
    // Get current settings
    let currencyCode = CNPERP_CURRENCY.code;
    let currencySymbol = CNPERP_CURRENCY.symbol;
    let currencyName = CNPERP_CURRENCY.name;
    let vatRate = CNPERP_CURRENCY.vatRate;
    
    // Use settings loader if available
    if (window.settingsLoader && window.settingsLoader.isSettingsLoaded()) {
        const currencySettings = window.settingsLoader.getCurrencySettings();
        const vatSettings = window.settingsLoader.getVatSettings();
        
        currencyCode = currencySettings.currency || currencyCode;
        currencySymbol = currencySettings.currency_symbol || currencySymbol;
        currencyName = currencySettings.currency_name || currencyName;
        vatRate = vatSettings.vat_rate || vatRate;
    }
    
    // Update currency symbols
    document.querySelectorAll('.currency-symbol').forEach(el => {
        el.textContent = currencySymbol;
    });
    
    // Update currency codes
    document.querySelectorAll('.currency-code').forEach(el => {
        el.textContent = currencyCode;
    });
    
    // Update currency names
    document.querySelectorAll('.currency-name').forEach(el => {
        el.textContent = currencyName;
    });
    
    // Update VAT rate displays
    document.querySelectorAll('.vat-rate').forEach(el => {
        el.textContent = vatRate + '%';
    });
    
    // Update currency selectors
    document.querySelectorAll('select[name="currency"], select[id="currency"]').forEach(select => {
        // Set current currency as selected
        Array.from(select.options).forEach(option => {
            if (option.value === currencyCode) {
                option.selected = true;
            }
        });
    });
}

/**
 * Load currency settings from server
 */
async function loadCurrencySettings() {
    try {
        // Use settings loader if available
        if (window.settingsLoader) {
            await window.settingsLoader.init();
            const currencySettings = window.settingsLoader.getCurrencySettings();
            const vatSettings = window.settingsLoader.getVatSettings();
            
            CNPERP_CURRENCY.code = currencySettings.currency || 'BWP';
            CNPERP_CURRENCY.symbol = currencySettings.currency_symbol || 'P';
            CNPERP_CURRENCY.name = currencySettings.currency_name || 'Botswana Pula';
            CNPERP_CURRENCY.vatRate = vatSettings.vat_rate || 14.0;
            CNPERP_CURRENCY.locale = currencySettings.locale || 'en';
            CNPERP_CURRENCY.country = currencySettings.country || 'BW';
        } else {
            // Fallback to direct API call
            const response = await fetch('/api/v1/settings/currency');
            
            if (response.ok) {
                const data = await response.json();
                if (data.data) {
                    CNPERP_CURRENCY.code = data.data.currency || 'BWP';
                    CNPERP_CURRENCY.symbol = data.data.currency_symbol || 'P';
                    CNPERP_CURRENCY.name = data.data.currency_name || 'Botswana Pula';
                    CNPERP_CURRENCY.vatRate = data.data.vat_rate || 14.0;
                    CNPERP_CURRENCY.locale = data.data.locale || 'en';
                    CNPERP_CURRENCY.country = data.data.country || 'BW';
                }
            }
        }
    } catch (error) {
        console.error('Error loading currency settings:', error);
        // Keep default BWP settings
    }
    
    // Update displays after loading settings
    updateAllCurrencyDisplays();
}

/**
 * Initialize currency utilities
 */
function initCurrencyUtils() {
    // Load settings and update displays
    loadCurrencySettings();
    
    // Update displays on DOM content loaded
    document.addEventListener('DOMContentLoaded', function() {
        updateAllCurrencyDisplays();
    });
    
    // Listen for settings loaded event
    document.addEventListener('settingsLoaded', function() {
        updateAllCurrencyDisplays();
    });
}

/**
 * Replace all $ symbols with proper currency symbol in text content
 */
function replaceDollarSigns() {
    const currencySymbol = CNPERP_CURRENCY.symbol || 'P';
    
    const walker = document.createTreeWalker(
        document.body,
        NodeFilter.SHOW_TEXT,
        null,
        false
    );
    
    const textNodes = [];
    let node;
    while (node = walker.nextNode()) {
        textNodes.push(node);
    }
    
    textNodes.forEach(textNode => {
        if (textNode.textContent.includes('$')) {
            textNode.textContent = textNode.textContent.replace(/\$/g, currencySymbol);
        }
    });
}

/**
 * Get current currency settings
 */
function getCurrentCurrencySettings() {
    if (window.settingsLoader && window.settingsLoader.isSettingsLoaded()) {
        return window.settingsLoader.getCurrencySettings();
    }
    return CNPERP_CURRENCY;
}

/**
 * Get current VAT settings
 */
function getCurrentVatSettings() {
    if (window.settingsLoader && window.settingsLoader.isSettingsLoaded()) {
        return window.settingsLoader.getVatSettings();
    }
    return { vat_rate: CNPERP_CURRENCY.vatRate };
}

// Auto-initialize when script loads
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initCurrencyUtils);
} else {
    initCurrencyUtils();
}

// Export functions for use in other scripts
window.formatCurrency = formatCurrency;
window.formatAmount = formatAmount;
window.updateAllCurrencyDisplays = updateAllCurrencyDisplays;
window.loadCurrencySettings = loadCurrencySettings;
window.replaceDollarSigns = replaceDollarSigns;
window.getCurrentCurrencySettings = getCurrentCurrencySettings;
window.getCurrentVatSettings = getCurrentVatSettings; 