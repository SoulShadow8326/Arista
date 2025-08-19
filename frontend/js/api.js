class ApiClient {
    constructor() {
    const origin = (typeof window !== 'undefined' && window.location && window.location.origin) ? window.location.origin : '';
    this.baseUrl = origin + '/api';
    }

    async request(endpoint, options = {}) {
        const url = `${this.baseUrl}${endpoint}`;
        const token = localStorage.getItem('token');
        const headers = {
            'Content-Type': 'application/json',
            ...options.headers
        };

        const config = {
            headers,
            credentials: 'include',
            ...options
        };

        if (token) {
            headers['Authorization'] = `Bearer ${token}`;
        }

        try {
            const response = await fetch(url, config);

            if (response.status === 401) {
                window.location.href = '/login';
                throw new Error('Authentication required');
            }

            if (!response.ok) {
                let errorMessage = `HTTP ${response.status}: ${response.statusText}`;
                try {
                    const text = await response.text();
                    if (text) {
                        try {
                            const parsed = JSON.parse(text);
                            errorMessage = parsed.detail || parsed.message || JSON.stringify(parsed) || errorMessage;
                        } catch (e) {
                            errorMessage = text;
                        }
                    }
                } catch (e) {
                }
                throw new Error(errorMessage);
            }

            const contentType = response.headers.get('content-type');
            if (contentType && contentType.includes('application/json')) {
                return await response.json();
            }

            return response;
        } catch (error) {
            console.error('API request failed:', error);
            throw error;
        }
    }

    async get(endpoint) { return this.request(endpoint); }
    async post(endpoint, data) { return this.request(endpoint, { method: 'POST', body: JSON.stringify(data) }); }
    async put(endpoint, data) { return this.request(endpoint, { method: 'PUT', body: JSON.stringify(data) }); }
    async delete(endpoint) { return this.request(endpoint, { method: 'DELETE' }); }

    async signIn(email, password) {
        const response = await this.post('/auth/signin', { email, password });
        return response;
    }

    async signOut() {
        try {
            await this.post('/auth/signout', {});
            this.token = null;
            localStorage.removeItem('access_token');
            window.location.href = '/login';
        } catch (error) {
            console.error('Error during sign out:', error);
            window.location.href = '/login';
        }
    }

    async getMe() {
        return this.get('/me');
    }

    setAuthToken(token) {
        console.log('setAuthToken is no longer needed - using HTTP-only cookies');
    }

    getAuthToken() {
        console.log('getAuthToken is no longer needed - using HTTP-only cookies');
        return '';
    }
}

function showToast(message, type = 'info') {
    const toast = document.getElementById('toast');
    if (!toast) return;
    
    toast.textContent = message;
    toast.className = `toast ${type} show`;
    
    setTimeout(() => {
        toast.classList.remove('show');
    }, 3000);
}

function showModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.add('show');
    }
}

function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.remove('show');
    }
}

function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
}

function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

const api = new ApiClient();
