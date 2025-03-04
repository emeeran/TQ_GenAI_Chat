/**
 * Global error handler for TQ GenAI Chat
 * Provides centralized error handling and logging
 */

(function () {
    // Error tracking
    const errorLog = [];
    const MAX_ERRORS = 50;

    // Add global error handler
    window.addEventListener('error', function (event) {
        logError({
            type: 'exception',
            message: event.message,
            source: event.filename,
            lineno: event.lineno,
            colno: event.colno,
            error: event.error ? event.error.stack : null,
            timestamp: new Date().toISOString()
        });

        // Show in console with timestamp
        console.error(
            `[${new Date().toLocaleTimeString()}] Error: ${event.message} (${event.filename}:${event.lineno})`
        );
    });

    // Add unhandled promise rejection handler
    window.addEventListener('unhandledrejection', function (event) {
        logError({
            type: 'promise',
            message: event.reason?.message || 'Unhandled promise rejection',
            error: event.reason?.stack || String(event.reason),
            timestamp: new Date().toISOString()
        });

        // Show in console with timestamp
        console.error(
            `[${new Date().toLocaleTimeString()}] Promise error: ${event.reason?.message || event.reason}`
        );
    });

    // Fix for null elements
    const originalGetElementById = document.getElementById;
    document.getElementById = function (id) {
        const element = originalGetElementById.call(document, id);
        if (!element) {
            console.warn(`getElementById('${id}') returned null`);
        }
        return element;
    };

    // Log error to internal store
    function logError(errorInfo) {
        // Add to error log
        errorLog.unshift(errorInfo);

        // Keep log size in check
        if (errorLog.length > MAX_ERRORS) {
            errorLog.pop();
        }

        // Trigger custom event for any listeners
        window.dispatchEvent(new CustomEvent('app-error', {
            detail: errorInfo
        }));
    }

    // Public API
    window.errorHandler = {
        logError: logError,
        getErrorLog: () => [...errorLog],
        clearErrorLog: () => {
            errorLog.length = 0;
        },
        showErrorOverlay: (error) => {
            // Create error notification
            const notification = document.createElement('div');
            notification.className = 'error-notification';
            notification.innerHTML = `
                <div class="error-notification-header">
                    <i class="fas fa-exclamation-triangle"></i>
                    Error
                    <button class="error-close">×</button>
                </div>
                <div class="error-notification-body">
                    ${error.message || 'An error occurred'}
                </div>
            `;

            // Style the notification
            notification.style.cssText = `
                position: fixed;
                bottom: 20px;
                right: 20px;
                background-color: #f44336;
                color: white;
                padding: 10px 15px;
                border-radius: 4px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.2);
                z-index: 10000;
                max-width: 350px;
                font-family: sans-serif;
                animation: slideIn 0.3s ease-out forwards;
            `;

            // Add animation style
            const style = document.createElement('style');
            style.textContent = `
                @keyframes slideIn {
                    from { transform: translateX(100%); opacity: 0; }
                    to { transform: translateX(0); opacity: 1; }
                }

                .error-notification-header {
                    display: flex;
                    align-items: center;
                    justify-content: space-between;
                    margin-bottom: 8px;
                    font-weight: bold;
                }

                .error-close {
                    background: none;
                    border: none;
                    color: white;
                    font-size: 20px;
                    cursor: pointer;
                    padding: 0;
                    line-height: 1;
                }
            `;

            document.head.appendChild(style);
            document.body.appendChild(notification);

            // Add close handler
            const closeBtn = notification.querySelector('.error-close');
            if (closeBtn) {
                closeBtn.addEventListener('click', () => {
                    notification.remove();
                });
            }

            // Auto remove after 5 seconds
            setTimeout(() => {
                notification.remove();
            }, 5000);
        }
    };

    // Initialize error logging
    console.info("Error handler initialized");
})();
