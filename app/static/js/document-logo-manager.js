/**
 * Shared Logo Utility for Documents
 * Provides consistent logo handling across all document types
 */

class DocumentLogoManager {
    constructor() {
        this.appSettings = null;
        this.logoCache = new Map();
    }

    /**
     * Initialize the logo manager with app settings
     * @param {Object} appSettings - Application settings object
     */
    init(appSettings) {
        this.appSettings = appSettings;
    }

    /**
     * Get company logo data from app settings
     * @returns {Object} Logo data with base64 string and display settings
     */
    getCompanyLogo() {
        if (!this.appSettings) {
            console.warn('DocumentLogoManager not initialized with app settings');
            return null;
        }

        return {
            base64: this.appSettings.company_logo_base64 || null,
            url: this.appSettings.company_logo_url || null,
            showInInvoices: this.appSettings.invoice_show_logo || false,
            showInDocuments: this.appSettings.document_show_logo || false
        };
    }

    /**
     * Apply logo to a document element
     * @param {string} elementId - ID of the image element
     * @param {string} documentType - Type of document ('invoice', 'credit_note', 'receipt', etc.)
     * @param {Object} options - Additional options for logo display
     */
    applyLogoToDocument(elementId, documentType = 'invoice', options = {}) {
        const logoElement = document.getElementById(elementId);
        if (!logoElement) {
            console.warn(`Logo element with ID '${elementId}' not found`);
            return false;
        }

        const logoData = this.getCompanyLogo();
        if (!logoData || !logoData.base64) {
            // Hide logo if no logo data available
            logoElement.style.display = 'none';
            logoElement.classList.add('d-none');
            return false;
        }

        // Check if logo should be shown for this document type
        const shouldShow = this.shouldShowLogo(documentType, logoData);
        if (!shouldShow) {
            logoElement.style.display = 'none';
            logoElement.classList.add('d-none');
            return false;
        }

        // Apply logo
        logoElement.src = logoData.base64;
        logoElement.style.display = 'block';
        logoElement.classList.remove('d-none');

        // Apply any custom styling
        if (options.maxWidth) logoElement.style.maxWidth = options.maxWidth;
        if (options.maxHeight) logoElement.style.maxHeight = options.maxHeight;
        if (options.className) logoElement.className = options.className;

        return true;
    }

    /**
     * Determine if logo should be shown for a document type
     * @param {string} documentType - Type of document
     * @param {Object} logoData - Logo data from app settings
     * @returns {boolean} Whether logo should be displayed
     */
    shouldShowLogo(documentType, logoData) {
        switch (documentType) {
            case 'invoice':
                return logoData.showInInvoices;
            case 'credit_note':
            case 'receipt':
            case 'purchase_order':
            case 'quotation':
                return logoData.showInDocuments;
            default:
                return logoData.showInDocuments;
        }
    }

    /**
     * Create a logo element with proper styling
     * @param {string} documentType - Type of document
     * @param {Object} options - Styling options
     * @returns {HTMLElement|null} Logo img element or null if no logo
     */
    createLogoElement(documentType = 'invoice', options = {}) {
        const logoData = this.getCompanyLogo();
        if (!logoData || !logoData.base64) return null;

        const shouldShow = this.shouldShowLogo(documentType, logoData);
        if (!shouldShow) return null;

        const img = document.createElement('img');
        img.src = logoData.base64;
        img.alt = 'Company Logo';
        img.className = options.className || 'company-logo';
        
        // Apply default styling
        img.style.maxWidth = options.maxWidth || '200px';
        img.style.maxHeight = options.maxHeight || '100px';
        img.style.height = 'auto';
        img.style.width = 'auto';

        return img;
    }

    /**
     * Update all logo elements on the current page
     * @param {string} documentType - Type of document
     */
    updateAllLogos(documentType = 'invoice') {
        const logoElements = document.querySelectorAll('.company-logo, [id*="logo"], [id*="Logo"]');
        let updated = 0;

        logoElements.forEach(element => {
            if (element.tagName === 'IMG') {
                const success = this.applyLogoToDocument(element.id, documentType);
                if (success) updated++;
            }
        });

        console.log(`Updated ${updated} logo elements for document type: ${documentType}`);
        return updated;
    }

    /**
     * Check if company has a logo configured
     * @returns {boolean} True if logo is available
     */
    hasLogo() {
        const logoData = this.getCompanyLogo();
        return !!(logoData && logoData.base64);
    }

    /**
     * Get logo display settings for a document type
     * @param {string} documentType - Type of document
     * @returns {Object} Display settings
     */
    getLogoSettings(documentType) {
        const logoData = this.getCompanyLogo();
        return {
            hasLogo: this.hasLogo(),
            shouldShow: logoData ? this.shouldShowLogo(documentType, logoData) : false,
            base64: logoData ? logoData.base64 : null,
            settings: logoData || {}
        };
    }
}

// Create global instance
window.DocumentLogoManager = new DocumentLogoManager();

// Auto-initialize when app settings are loaded
document.addEventListener('DOMContentLoaded', function() {
    // Try to get app settings from global variable if available
    if (window.appSettings) {
        window.DocumentLogoManager.init(window.appSettings);
    }
    
    // Listen for custom app settings loaded event
    document.addEventListener('appSettingsLoaded', function(event) {
        window.DocumentLogoManager.init(event.detail);
    });
});

/**
 * Utility function to dispatch app settings loaded event
 * Call this after loading app settings to notify the logo manager
 */
function notifyAppSettingsLoaded(appSettings) {
    window.appSettings = appSettings; // Set global variable
    window.DocumentLogoManager.init(appSettings);
    
    // Dispatch custom event
    const event = new CustomEvent('appSettingsLoaded', { detail: appSettings });
    document.dispatchEvent(event);
}

// Export for module systems if needed
if (typeof module !== 'undefined' && module.exports) {
    module.exports = DocumentLogoManager;
}
