/**
 * Debug utilities for TQ GenAI Chat
 */

// Enable verbose console logging
const DEBUG = true;

// Global error handler
window.addEventListener('error', function (event) {
    if (DEBUG) {
        console.error(`[${new Date().toLocaleTimeString()}] Global error caught:`, event.error);

        // Show error in UI
        showDebugMessage(`Error: ${event.error.message || 'Unknown error'}`);
    }
});

// Promise rejection handler
window.addEventListener('unhandledrejection', function (event) {
    if (DEBUG) {
        console.error(`[${new Date().toLocaleTimeString()}] Unhandled promise rejection:`, event.reason);

        // Show error in UI
        showDebugMessage(`Promise error: ${event.reason.message || 'Unknown error'}`);
    }
});

// Debug logging function
function debugLog(...args) {
    if (DEBUG) {
        console.log(`[${new Date().toLocaleTimeString()}] %c[DEBUG]`, 'color: #4361ee; font-weight: bold;', ...args);
    }
}

// Show debug message in UI
function showDebugMessage(message) {
    // Check if debug overlay exists
    let debugOverlay = document.getElementById('debug-overlay');

    if (!debugOverlay) {
        // Create debug overlay
        debugOverlay = document.createElement('div');
        debugOverlay.id = 'debug-overlay';
        debugOverlay.style.cssText = `
            position: fixed;
            bottom: 10px;
            right: 10px;
            background-color: rgba(0, 0, 0, 0.8);
            color: #fff;
            padding: 10px;
            border-radius: 5px;
            font-family: monospace;
            font-size: 12px;
            max-width: 400px;
            z-index: 9999;
        `;

        // Add close button
        const debugCloseBtn = document.createElement('button');
        debugCloseBtn.textContent = 'X';
        debugCloseBtn.style.cssText = `
            position: absolute;
            top: 5px;
            right: 5px;
            background: none;
            border: none;
            color: white;
            cursor: pointer;
            font-size: 14px;
        `;
        debugCloseBtn.addEventListener('click', () => {
            debugOverlay.style.display = 'none';
        });

        debugOverlay.appendChild(debugCloseBtn);

        // Add message container
        const messageContainer = document.createElement('div');
        messageContainer.id = 'debug-messages';
        messageContainer.style.maxHeight = '200px';
        messageContainer.style.overflowY = 'auto';
        debugOverlay.appendChild(messageContainer);

        document.body.appendChild(debugOverlay);
    }

    // Add message to debug overlay
    const messageContainer = document.getElementById('debug-messages');
    if (messageContainer) {
        const messageElement = document.createElement('div');
        messageElement.textContent = `[${new Date().toLocaleTimeString()}] ${message}`;
        messageElement.style.borderBottom = '1px solid #333';
        messageElement.style.paddingBottom = '5px';
        messageElement.style.marginBottom = '5px';

        messageContainer.appendChild(messageElement);

        // Auto-scroll to bottom
        messageContainer.scrollTop = messageContainer.scrollHeight;

        // Make sure overlay is visible
        debugOverlay.style.display = 'block';
    }
}

// Add API call debug interceptor
function interceptFetch() {
    const originalFetch = window.fetch;

    window.fetch = async function (url, options) {
        debugLog(`🌐 Fetch request to ${url}`);

        if (options && options.body) {
            try {
                const body = JSON.parse(options.body);
                debugLog('Request body:', body);
            } catch (e) {
                debugLog('Request body (non-JSON):', options.body);
            }
        }

        try {
            const response = await originalFetch(url, options);

            // Clone the response to read its body
            const clone = response.clone();

            // Process JSON responses
            if (response.headers.get('content-type')?.includes('application/json')) {
                try {
                    const data = await clone.json();
                    debugLog(`Response from ${url}:`, data);
                } catch (e) {
                    debugLog(`Error parsing JSON response from ${url}`, e);
                }
            }

            return response;
        } catch (error) {
            debugLog(`❌ Error in fetch to ${url}:`, error);
            showDebugMessage(`Network error: ${error.message}`);
            throw error;
        }
    };
}

// Initialize debug features when DOM is loaded
document.addEventListener('DOMContentLoaded', function () {
    if (DEBUG) {
        debugLog('Debug mode enabled');
        interceptFetch();

        // Let's create a new function with a more unique name and safer implementation
        function createUniqueDebugButton() {
            const existingDebugBtn = document.getElementById('debug-toggle-btn');
            if (existingDebugBtn) {
                debugLog('Debug button already exists, not creating duplicate');
                return; // Don't create duplicates
            }

            try {
                const debugBtn = document.createElement('button');
                debugBtn.id = 'debug-toggle-btn';
                debugBtn.textContent = 'Debug';
                debugBtn.className = 'debug-toggle-btn'; // Use class for styling
                debugBtn.style.bottom = '130px'; // Ensure unique positioning

                // Use safer event binding
                if (debugBtn) {
                    debugBtn.onclick = function debugButtonClickHandler() {
                        showDebugMessage('Debug panel opened');
                    };
                }

                // Only append if body exists
                if (document.body) {
                    document.body.appendChild(debugBtn);
                    debugLog('Debug button created successfully');
                }
            } catch (error) {
                console.error('Failed to create debug button:', error);
            }
        }

        // Add a longer timeout to ensure DOM is fully loaded
        setTimeout(createUniqueDebugButton, 1500);
    }
});

// Export debug utilities
window.chatDebug = {
    log: debugLog,
    showMessage: showDebugMessage
};
