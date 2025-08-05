/**
 * High-Performance Frontend Utilities
 * Optimized for modern browsers with async/await and performance monitoring
 */

class APIService {
    constructor() {
        this.baseURL = '/api/v1';
        this.requestQueue = new Map();
        this.cache = new Map();
        this.cacheTTL = 5 * 60 * 1000; // 5 minutes
    }

    /**
     * Debounced API request with caching
     */
    async request(endpoint, options = {}, cacheKey = null) {
        const url = `${this.baseURL}${endpoint}`;
        const method = options.method || 'GET';

        // Check cache first for GET requests
        if (method === 'GET' && cacheKey && this.cache.has(cacheKey)) {
            const cached = this.cache.get(cacheKey);
            if (Date.now() - cached.timestamp < this.cacheTTL) {
                return cached.data;
            }
        }

        // Prevent duplicate requests
        const requestKey = `${method}:${url}`;
        if (this.requestQueue.has(requestKey)) {
            return this.requestQueue.get(requestKey);
        }

        const requestPromise = this._executeRequest(url, options);
        this.requestQueue.set(requestKey, requestPromise);

        try {
            const result = await requestPromise;

            // Cache GET requests
            if (method === 'GET' && cacheKey) {
                this.cache.set(cacheKey, {
                    data: result,
                    timestamp: Date.now()
                });
            }

            return result;
        } finally {
            this.requestQueue.delete(requestKey);
        }
    }

    async _executeRequest(url, options) {
        const response = await fetch(url, {
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            },
            ...options
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        return response.json();
    }

    // Specialized methods
    async sendChatMessage(data) {
        return this.request('/chat', {
            method: 'POST',
            body: JSON.stringify(data)
        });
    }

    async getProviders() {
        return this.request('/providers', {}, 'providers');
    }

    async getModels(provider) {
        return this.request(`/models/${provider}`, {}, `models-${provider}`);
    }
}

class DOMUtils {
    /**
     * Efficient DOM manipulation utilities
     */
    static createElement(tag, attributes = {}, children = []) {
        const element = document.createElement(tag);

        // Set attributes
        Object.entries(attributes).forEach(([key, value]) => {
            if (key === 'className') {
                element.className = value;
            } else if (key === 'innerHTML') {
                element.innerHTML = value;
            } else {
                element.setAttribute(key, value);
            }
        });

        // Add children
        children.forEach(child => {
            if (typeof child === 'string') {
                element.appendChild(document.createTextNode(child));
            } else {
                element.appendChild(child);
            }
        });

        return element;
    }

    static debounce(func, wait) {
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

    static throttle(func, limit) {
        let inThrottle;
        return function() {
            const args = arguments;
            const context = this;
            if (!inThrottle) {
                func.apply(context, args);
                inThrottle = true;
                setTimeout(() => inThrottle = false, limit);
            }
        }
    }

    static animateValue(element, start, end, duration, callback) {
        const startTime = performance.now();
        const difference = end - start;

        function step(currentTime) {
            const elapsed = currentTime - startTime;
            const progress = Math.min(elapsed / duration, 1);

            const value = start + (difference * progress);
            callback(value);

            if (progress < 1) {
                requestAnimationFrame(step);
            }
        }

        requestAnimationFrame(step);
    }
}

class PerformanceMonitor {
    constructor() {
        this.metrics = new Map();
        this.startTimes = new Map();
    }

    startTimer(name) {
        this.startTimes.set(name, performance.now());
    }

    endTimer(name) {
        const startTime = this.startTimes.get(name);
        if (startTime) {
            const duration = performance.now() - startTime;
            this.recordMetric(name, duration);
            this.startTimes.delete(name);
            return duration;
        }
        return 0;
    }

    recordMetric(name, value) {
        if (!this.metrics.has(name)) {
            this.metrics.set(name, []);
        }
        this.metrics.get(name).push({
            value,
            timestamp: Date.now()
        });

        // Keep only last 100 measurements
        if (this.metrics.get(name).length > 100) {
            this.metrics.get(name).shift();
        }
    }

    getAverageMetric(name) {
        const values = this.metrics.get(name);
        if (!values || values.length === 0) return 0;

        const sum = values.reduce((acc, item) => acc + item.value, 0);
        return sum / values.length;
    }

    getAllMetrics() {
        const result = {};
        this.metrics.forEach((values, name) => {
            result[name] = {
                average: this.getAverageMetric(name),
                count: values.length,
                latest: values[values.length - 1]?.value || 0
            };
        });
        return result;
    }
}

// Export utilities
window.APIService = APIService;
window.DOMUtils = DOMUtils;
window.PerformanceMonitor = PerformanceMonitor;

// Global instances
window.apiService = new APIService();
window.perfMonitor = new PerformanceMonitor();
