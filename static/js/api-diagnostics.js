/**
 * API Diagnostics tool for TQ GenAI Chat
 * Provides debugging and diagnostics functionality for API calls
 */

class APIDiagnostics {
    constructor() {
        this.intercepted = false;
        this.apiCalls = [];
        this.maxLogEntries = 20;
        this.lastProviderCall = {};
    }

    /**
     * Start intercepting and logging API calls
     */
    startInterception() {
        if (this.intercepted) return;

        const originalFetch = window.fetch;

        window.fetch = async (url, options) => {
            const startTime = performance.now();
            const isApiCall = url.includes('/chat') ||
                url.includes('/get_models') ||
                url.includes('/get_providers');

            let provider = 'unknown';
            let model = 'unknown';

            // Try to extract provider and model info from request body
            if (options && options.body && isApiCall) {
                try {
                    const body = JSON.parse(options.body);
                    provider = body.provider || 'unknown';
                    model = body.model || 'unknown';

                    // Store last provider and model for retry diagnostics
                    if (url.includes('/chat')) {
                        this.lastProviderCall[provider] = model;
                    }
                } catch (e) { /* Ignore parsing errors */ }
            }

            // Extract provider from URL for get_models endpoint
            if (url.includes('/get_models/')) {
                provider = url.split('/get_models/')[1];
            }

            // Log the request
            const requestId = Date.now().toString(36) + Math.random().toString(36).substr(2, 5);
            const requestEntry = {
                id: requestId,
                url,
                method: options?.method || 'GET',
                provider,
                model,
                startTime,
                status: 'pending'
            };

            if (isApiCall) {
                this.logApiCall(requestEntry);
            }

            try {
                // Call the original fetch function
                const response = await originalFetch(url, options);

                // Update the log entry with response info
                const endTime = performance.now();
                const duration = endTime - startTime;

                if (isApiCall) {
                    const responseClone = response.clone();
                    let responseBody;

                    try {
                        if (responseClone.headers.get('content-type')?.includes('application/json')) {
                            responseBody = await responseClone.json();
                        } else {
                            responseBody = await responseClone.text();
                        }
                    } catch (e) {
                        responseBody = 'Error parsing response: ' + e.message;
                    }

                    this.updateApiCall(requestId, {
                        status: response.ok ? 'success' : 'error',
                        statusCode: response.status,
                        duration,
                        response: responseBody
                    });
                }

                return response;
            } catch (error) {
                // Update log entry for failed requests
                if (isApiCall) {
                    const endTime = performance.now();
                    this.updateApiCall(requestId, {
                        status: 'error',
                        error: error.message,
                        duration: endTime - startTime
                    });
                }

                // Re-throw the error to not disrupt normal error handling
                throw error;
            }
        };

        this.intercepted = true;
        console.log('API call interception started');
    }

    /**
     * Log an API call
     */
    logApiCall(entry) {
        this.apiCalls.unshift(entry);

        // Limit the number of entries
        if (this.apiCalls.length > this.maxLogEntries) {
            this.apiCalls = this.apiCalls.slice(0, this.maxLogEntries);
        }

        // Trigger update event
        this.triggerUpdate();
    }

    /**
     * Update an existing API call log entry
     */
    updateApiCall(id, updates) {
        const entry = this.apiCalls.find(call => call.id === id);
        if (entry) {
            Object.assign(entry, updates);
            this.triggerUpdate();
        }
    }

    /**
     * Trigger an update event
     */
    triggerUpdate() {
        window.dispatchEvent(new CustomEvent('api-diagnostics-update', {
            detail: { calls: this.apiCalls }
        }));
    }

    /**
     * Get a diagnostic status report for recent API calls
     */
    getDiagnosticsReport() {
        const providerStats = {};
        let totalCalls = 0;
        let failedCalls = 0;
        let averageResponseTime = 0;
        let totalResponseTime = 0;

        // Process all completed calls
        const completedCalls = this.apiCalls.filter(call =>
            call.status === 'success' || call.status === 'error');

        totalCalls = completedCalls.length;

        completedCalls.forEach(call => {
            // Count failed calls
            if (call.status === 'error') failedCalls++;

            // Calculate average response time
            if (call.duration) totalResponseTime += call.duration;

            // Gather provider statistics
            if (!providerStats[call.provider]) {
                providerStats[call.provider] = {
                    calls: 0,
                    failures: 0,
                    models: {}
                };
            }

            const providerStat = providerStats[call.provider];
            providerStat.calls++;

            if (call.status === 'error') {
                providerStat.failures++;
            }

            // Model statistics
            if (call.model && call.model !== 'unknown') {
                if (!providerStat.models[call.model]) {
                    providerStat.models[call.model] = { calls: 0, failures: 0 };
                }

                const modelStat = providerStat.models[call.model];
                modelStat.calls++;

                if (call.status === 'error') {
                    modelStat.failures++;
                }
            }
        });

        averageResponseTime = totalCalls ? totalResponseTime / totalCalls : 0;

        return {
            totalCalls,
            failedCalls,
            averageResponseTime: Math.round(averageResponseTime),
            successRate: totalCalls ? ((totalCalls - failedCalls) / totalCalls * 100).toFixed(1) + '%' : 'N/A',
            providers: providerStats,
            lastProviderCall: this.lastProviderCall
        };
    }

    /**
     * Check if there were recent failures with the specified provider
     */
    hasRecentFailure(provider, withinMs = 30000) {
        const now = performance.now();
        return this.apiCalls.some(call =>
            call.provider === provider &&
            call.status === 'error' &&
            (now - call.startTime) < withinMs
        );
    }

    /**
     * Create an on-screen diagnostic display
     */
    createDiagnosticDisplay() {
        // Create a floating diagnostic panel with a safe implementation
        try {
            // Check if panel already exists
            if (document.getElementById('api-diagnostics-panel')) {
                console.log('API diagnostics panel already exists');
                return;
            }

            const panel = document.createElement('div');
            panel.id = 'api-diagnostics-panel';
            panel.className = 'api-diagnostics-panel';
            panel.style.cssText = `
                position: fixed;
                bottom: 10px;
                left: 10px;
                width: 300px;
                max-height: 500px;
                overflow-y: auto;
                background-color: rgba(0, 0, 0, 0.8);
                color: #fff;
                padding: 10px;
                border-radius: 5px;
                font-family: monospace;
                z-index: 9999;
                font-size: 12px;
                display: none;
            `;

            // Use a unique variable name to prevent conflicts
            const diagnosticsToggleBtn = document.createElement('button');
            diagnosticsToggleBtn.textContent = 'API Diagnostics';
            diagnosticsToggleBtn.id = 'api-diagnostics-toggle-btn'; // Different ID
            diagnosticsToggleBtn.className = 'diagnostics-toggle-btn';
            diagnosticsToggleBtn.style.cssText = `
                position: fixed;
                bottom: 50px;
                left: 10px;
                padding: 5px 10px;
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 4px;
                cursor: pointer;
                font-family: sans-serif;
                z-index: 1000;
            `;

            // Safely append to body only if body exists
            if (document.body) {
                document.body.appendChild(panel);
                document.body.appendChild(diagnosticsToggleBtn);

                // Use a safe event binding approach
                const self = this; // Store reference to this for the closure
                diagnosticsToggleBtn.onclick = function () {
                    if (panel.style.display === 'none') {
                        panel.style.display = 'block';
                        self.updateDiagnosticDisplay(panel);
                    } else {
                        panel.style.display = 'none';
                    }
                };

                // Safer event binding for updates
                window.addEventListener('api-diagnostics-update', function (event) {
                    if (panel && panel.style.display !== 'none') {
                        self.updateDiagnosticDisplay(panel);
                    }
                });
            }
        } catch (error) {
            console.error('Failed to create API diagnostics display:', error);
        }
    }

    /**
     * Update the diagnostic display with current information
     */
    updateDiagnosticDisplay(panel) {
        const report = this.getDiagnosticsReport();

        let html = `
            <h3>API Diagnostics</h3>
            <div>Total Calls: ${report.totalCalls}</div>
            <div>Success Rate: ${report.successRate}</div>
            <div>Avg Response: ${report.averageResponseTime}ms</div>
            <h4>Recent API Calls</h4>
            <div style="border-top: 1px solid #555; margin: 5px 0;"></div>
        `;

        // Add recent calls
        this.apiCalls.slice(0, 5).forEach(call => {
            const statusColor = call.status === 'success' ? '#4CAF50' :
                call.status === 'error' ? '#f44336' : '#FFC107';

            html += `
                <div style="margin-bottom: 5px; padding: 3px; border-left: 3px solid ${statusColor};">
                    <div>${call.provider}/${call.model}</div>
                    <div style="display: flex; justify-content: space-between;">
                        <small>${call.url.split('/').pop()}</small>
                        <small>${call.status} ${call.statusCode || ''}</small>
                    </div>
                    ${call.duration ? `<small>${Math.round(call.duration)}ms</small>` : ''}
                </div>
            `;
        });

        panel.innerHTML = html;
    }
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    window.apiDiagnostics = new APIDiagnostics();
    window.apiDiagnostics.startInterception();

    // Only create display in development mode
    const isDev = window.location.hostname === 'localhost' ||
        window.location.hostname === '127.0.0.1';

    if (isDev) {
        window.apiDiagnostics.createDiagnosticDisplay();
    }
});
