// Chart.js Fallback for Offline Mode
// This provides basic chart functionality when Chart.js CDN is not available

console.log('📊 Loading Chart.js fallback...');

// Check if Chart.js is available
if (typeof Chart === 'undefined') {
    console.log('⚠️ Chart.js not available, creating fallback...');
    
    // Create a simple Chart fallback
    window.Chart = function(ctx) {
        this.ctx = ctx;
        this.data = {};
        this.options = {};
        this.destroyed = false;
        
        this.destroy = function() {
            this.destroyed = true;
            console.log('📊 Chart destroyed (fallback)');
        };
        
        // Simple chart rendering fallback
        this.render = function() {
            if (this.destroyed) return;
            
            const canvas = this.ctx.canvas;
            const ctx = this.ctx;
            
            // Clear canvas
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            
            // Draw a simple placeholder
            ctx.fillStyle = '#f8f9fa';
            ctx.fillRect(0, 0, canvas.width, canvas.height);
            
            ctx.fillStyle = '#6c757d';
            ctx.font = '14px Arial';
            ctx.textAlign = 'center';
            ctx.fillText('Chart not available offline', canvas.width / 2, canvas.height / 2);
            ctx.fillText('Please check your internet connection', canvas.width / 2, canvas.height / 2 + 20);
        };
        
        // Auto-render
        setTimeout(() => this.render(), 100);
        
        return this;
    };
    
    // Add basic chart types
    Chart.prototype = {
        destroy: function() {
            this.destroyed = true;
        },
        update: function() {
            if (!this.destroyed) this.render();
        }
    };
    
    console.log('✅ Chart.js fallback created');
} else {
    console.log('✅ Chart.js is available');
}

// Add error handling for chart initialization
window.addEventListener('error', function(e) {
    if (e.message.includes('Chart is not defined')) {
        console.log('🔄 Attempting to reload Chart.js fallback...');
        // The fallback should already be loaded
    }
});
