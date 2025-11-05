/**
 * API Endpoint Validation Script
 * 
 * This script tests all defined API endpoints to ensure they're accessible
 * and provides a report of which endpoints are working correctly.
 * 
 * Usage: Open browser console and run: testAllEndpoints()
 */

window.APIValidator = {
    async testEndpoint(name, url) {
        try {
            const startTime = Date.now();
            const response = await fetch(url, {
                method: 'GET',
                headers: {
                    'Accept': 'application/json',
                    ...window.authFetch?.authHeader() || {}
                }
            });
            const duration = Date.now() - startTime;
            
            return {
                name,
                url,
                status: response.status,
                ok: response.ok,
                duration: `${duration}ms`,
                error: null
            };
        } catch (error) {
            return {
                name,
                url,
                status: null,
                ok: false,
                duration: null,
                error: error.message
            };
        }
    },

    async testAllEndpoints() {
        console.log('🔍 Starting API Endpoint Validation...');
        console.log('Environment:', API_CONFIG.getEnvironmentInfo());
        
        const results = [];
        const endpoints = API_CONFIG.ENDPOINTS;
        
        // Test core endpoints
        const coreEndpoints = [
            'SETTINGS',
            'SALES',
            'SALES_CUSTOMERS',
            'INVENTORY_PRODUCTS',
            'BRANCHES_PUBLIC',
            'USERS'
        ];
        
        for (const endpointName of coreEndpoints) {
            if (endpoints[endpointName]) {
                console.log(`Testing ${endpointName}...`);
                const result = await this.testEndpoint(endpointName, endpoints[endpointName]);
                results.push(result);
            }
        }
        
        // Generate report
        this.generateReport(results);
        return results;
    },

    generateReport(results) {
        console.log('\n📊 API Endpoint Validation Report');
        console.log('='.repeat(50));
        
        const successful = results.filter(r => r.ok);
        const failed = results.filter(r => !r.ok);
        
        console.log(`✅ Successful: ${successful.length}`);
        console.log(`❌ Failed: ${failed.length}`);
        console.log(`📈 Success Rate: ${((successful.length / results.length) * 100).toFixed(1)}%\n`);
        
        // Successful endpoints
        if (successful.length > 0) {
            console.log('✅ Successful Endpoints:');
            successful.forEach(result => {
                console.log(`  ${result.name}: ${result.status} (${result.duration})`);
            });
            console.log('');
        }
        
        // Failed endpoints
        if (failed.length > 0) {
            console.log('❌ Failed Endpoints:');
            failed.forEach(result => {
                console.log(`  ${result.name}: ${result.error || 'HTTP ' + result.status}`);
                console.log(`    URL: ${result.url}`);
            });
            console.log('');
        }
        
        // Recommendations
        console.log('💡 Recommendations:');
        if (failed.length > 0) {
            console.log('  - Check if the FastAPI server is running on the correct port');
            console.log('  - Verify authentication tokens are valid');
            console.log('  - Check network connectivity');
        } else {
            console.log('  - All core endpoints are working correctly! 🎉');
        }
    },

    // Test a single endpoint by name
    async testSingle(endpointName) {
        const url = API_CONFIG.ENDPOINTS[endpointName];
        if (!url) {
            console.error(`❌ Endpoint '${endpointName}' not found in API_CONFIG.ENDPOINTS`);
            return null;
        }
        
        console.log(`🔍 Testing ${endpointName}...`);
        const result = await this.testEndpoint(endpointName, url);
        
        if (result.ok) {
            console.log(`✅ ${endpointName}: SUCCESS (${result.status}, ${result.duration})`);
        } else {
            console.log(`❌ ${endpointName}: FAILED (${result.error || 'HTTP ' + result.status})`);
        }
        
        return result;
    }
};

// Convenience functions for console usage
window.testAllEndpoints = () => APIValidator.testAllEndpoints();
window.testEndpoint = (name) => APIValidator.testSingle(name);

console.log('🛠️ API Validator loaded. Use testAllEndpoints() or testEndpoint("SETTINGS") in console.');