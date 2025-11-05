// API Utilities for CNPERP Frontend
// Provides authenticated fetch functions and common API patterns

const API_BASE_URL = 'http://localhost:8000/api/v1';

class ApiClient {
    constructor(baseUrl = API_BASE_URL) {
        this.baseUrl = baseUrl;
    }

    // Get authentication headers
    getAuthHeaders() {
        if (typeof auth !== 'undefined' && auth.authHeader) {
            return auth.authHeader();
        }
        return {};
    }

    // Make authenticated GET request
    async get(endpoint) {
        const response = await fetch(`${this.baseUrl}${endpoint}`, {
            headers: this.getAuthHeaders()
        });

        if (response.status === 401) {
            // Token expired or invalid, redirect to login
            if (typeof auth !== 'undefined') {
                auth.logout('Session expired');
            }
            throw new Error('Authentication required');
        }

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.detail || `Request failed: ${response.status}`);
        }

        return response.json();
    }

    // Make authenticated POST request
    async post(endpoint, data) {
        const response = await fetch(`${this.baseUrl}${endpoint}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                ...this.getAuthHeaders()
            },
            body: JSON.stringify(data)
        });

        if (response.status === 401) {
            if (typeof auth !== 'undefined') {
                auth.logout('Session expired');
            }
            throw new Error('Authentication required');
        }

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.detail || `Request failed: ${response.status}`);
        }

        return response.json();
    }

    // Make authenticated PUT request
    async put(endpoint, data) {
        const response = await fetch(`${this.baseUrl}${endpoint}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
                ...this.getAuthHeaders()
            },
            body: JSON.stringify(data)
        });

        if (response.status === 401) {
            if (typeof auth !== 'undefined') {
                auth.logout('Session expired');
            }
            throw new Error('Authentication required');
        }

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.detail || `Request failed: ${response.status}`);
        }

        return response.json();
    }

    // Make authenticated DELETE request
    async delete(endpoint) {
        const response = await fetch(`${this.baseUrl}${endpoint}`, {
            method: 'DELETE',
            headers: this.getAuthHeaders()
        });

        if (response.status === 401) {
            if (typeof auth !== 'undefined') {
                auth.logout('Session expired');
            }
            throw new Error('Authentication required');
        }

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.detail || `Request failed: ${response.status}`);
        }

        return response.json();
    }
}

// Create global API client instance
const apiClient = new ApiClient();

// Make it available globally
window.apiClient = apiClient;
