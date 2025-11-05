// Offline Handler for CNPERP ERP System
// Detects offline status and provides user feedback

console.log('🌐 Loading offline handler...');

// Offline status tracking
let isOffline = false;
let offlineNotification = null;

// Check if we're offline
function checkOfflineStatus() {
    const wasOffline = isOffline;
    isOffline = !navigator.onLine;
    
    if (isOffline && !wasOffline) {
        console.log('⚠️ Going offline');
        showOfflineNotification();
    } else if (!isOffline && wasOffline) {
        console.log('✅ Back online');
        hideOfflineNotification();
    }
}

// Show offline notification
function showOfflineNotification() {
    if (offlineNotification) return;
    
    offlineNotification = document.createElement('div');
    offlineNotification.id = 'offline-notification';
    offlineNotification.innerHTML = `
        <div style="
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            background-color: #dc3545;
            color: white;
            padding: 10px;
            text-align: center;
            z-index: 9999;
            font-weight: bold;
            box-shadow: 0 2px 4px rgba(0,0,0,0.2);
        ">
            <span>⚠️ You are currently offline. Some features may not work properly.</span>
            <button onclick="hideOfflineNotification()" style="
                background: none;
                border: none;
                color: white;
                margin-left: 10px;
                cursor: pointer;
                font-size: 16px;
            ">✕</button>
        </div>
    `;
    
    document.body.appendChild(offlineNotification);
}

// Hide offline notification
function hideOfflineNotification() {
    if (offlineNotification) {
        offlineNotification.remove();
        offlineNotification = null;
    }
}

// Check for CDN resource failures
function checkCDNResources() {
    const cdnResources = [
        'https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css',
        'https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.css',
        'https://cdn.jsdelivr.net/npm/chart.js',
        'https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js'
    ];
    
    let failedResources = 0;
    
    cdnResources.forEach(url => {
        fetch(url, { method: 'HEAD', mode: 'no-cors' })
            .catch(() => {
                failedResources++;
                if (failedResources === cdnResources.length) {
                    console.log('⚠️ All CDN resources failed to load');
                    showOfflineNotification();
                }
            });
    });
}

// Initialize offline detection
function initOfflineDetection() {
    // Listen for online/offline events
    window.addEventListener('online', checkOfflineStatus);
    window.addEventListener('offline', checkOfflineStatus);
    
    // Check initial status
    checkOfflineStatus();
    
    // Check CDN resources after a delay
    setTimeout(checkCDNResources, 2000);
    
    console.log('✅ Offline detection initialized');
}

// Add offline styles to pages
function addOfflineStyles() {
    if (!document.getElementById('offline-styles')) {
        const style = document.createElement('style');
        style.id = 'offline-styles';
        style.textContent = `
            /* Offline mode styles */
            .offline-mode {
                opacity: 0.8;
            }
            
            .offline-mode .btn {
                pointer-events: none;
            }
            
            .offline-mode .chart-container {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 4px;
                padding: 20px;
                text-align: center;
                color: #6c757d;
            }
        `;
        document.head.appendChild(style);
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    initOfflineDetection();
    addOfflineStyles();
});

// Export functions for global use
window.offlineHandler = {
    isOffline: () => isOffline,
    showOfflineNotification,
    hideOfflineNotification,
    checkOfflineStatus
};
