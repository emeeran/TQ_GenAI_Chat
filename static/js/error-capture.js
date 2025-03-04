/**
 * Error capture utility for TQ GenAI Chat
 * Captures and logs client-side errors for better debugging
 */

// Use window.errorLog instead of a global variable to avoid duplicate declaration
if (!window.errorLog) {
    window.errorLog = [];
}

// Create a global error handler
window.addEventListener('error', function (event) {
    const error = {
        message: event.message,
        source: event.filename,
        lineno: event.lineno,
        colno: event.colno,
        stack: event.error ? event.error.stack : null,
        timestamp: new Date().toISOString(),
        userAgent: navigator.userAgent
    };

    // Add to error log
    window.errorLog.push(error);

    // Log to console with clear formatting
    console.error(
        `%c JS Error: ${error.message}`,
        'color: #ff3333; font-weight: bold;',
        `\nSource: ${error.source}:${error.lineno}:${error.colno}`,
        `\nTimestamp: ${error.timestamp}`,
        `\nStack trace:`, error.stack
    );

    // You can send errors to server here
    // sendErrorToServer(error);

    // Return false to allow the error to appear in the console
    return false;
});

// Unhandled promise rejection handler
window.addEventListener('unhandledrejection', function (event) {
    const error = {
        message: event.reason.message || 'Unhandled Promise rejection',
        reason: event.reason.toString(),
        stack: event.reason.stack,
        timestamp: new Date().toISOString(),
        userAgent: navigator.userAgent
    };

    // Add to error log
    window.errorLog.push(error);

    // Log to console with clear formatting
    console.error(
        `%c Promise Error: ${error.message}`,
        'color: #ff8800; font-weight: bold;',
        `\nReason: ${error.reason}`,
        `\nTimestamp: ${error.timestamp}`,
        `\nStack trace:`, error.stack
    );
});

// Function to send error to server
function sendErrorToServer(error) {
    const url = '/api/log-error';

    // Don't block the UI thread with error reporting
    setTimeout(() => {
        try {
            fetch(url, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(error)
            })
                .then(response => {
                    if (!response.ok) {
                        console.warn('Failed to send error to server:', response.statusText);
                    }
                })
                .catch(sendError => {
                    console.warn('Error sending error to server:', sendError);
                });
        } catch (e) {
            // Silently fail if we can't report the error
            console.warn('Failed to send error:', e);
        }
    }, 0);
}

// Export a function to get the error log
function getErrorLog() {
    return window.errorLog;
}

// Function to clear the error log
function clearErrorLog() {
    window.errorLog = [];
}

// Console overrides to capture logs
if (!window.originalConsole) {
    window.originalConsole = {
        log: console.log,
        warn: console.warn,
        error: console.error,
        info: console.info
    };

    // Override console methods to capture logs
    console.log = function () {
        window.originalConsole.log.apply(console, arguments);
    };

    console.warn = function () {
        window.originalConsole.warn.apply(console, arguments);
    };

    console.error = function () {
        window.originalConsole.error.apply(console, arguments);
    };

    console.info = function () {
        window.originalConsole.info.apply(console, arguments);
    };
}

// Get a stack trace of the DOM elements at the point of error
function getElementStackTrace() {
    // Try to identify the relevant DOM context where error occurred
    const activeElement = document.activeElement;
    const focused = activeElement ? {
        tagName: activeElement.tagName,
        id: activeElement.id,
        className: activeElement.className
    } : null;

    // Check recently created elements
    const recentlyCreated = Array.from(document.querySelectorAll('[id^="retry"], .modal, .modal *')).map(el => ({
        tagName: el.tagName,
        id: el.id,
        className: el.className,
        exists: document.body.contains(el)
    }));

    return {
        activeElement: focused,
        recentElements: recentlyCreated.slice(0, 10),
        modals: Array.from(document.querySelectorAll('.modal')).map(m => m.id)
    };
}

// Create an on-screen error viewer
document.addEventListener('DOMContentLoaded', function () {
    setTimeout(function () {
        // Create error viewer button only if errors exist
        if (window.errorLog.length > 0) {
            const viewerBtn = document.createElement('button');
            viewerBtn.textContent = `Errors (${window.errorLog.length})`;
            viewerBtn.id = 'error-viewer-btn';
            viewerBtn.style.cssText = `
                position: fixed;
                top: 10px;
                right: 10px;
                background-color: #f44336;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 5px 10px;
                font-size: 12px;
                cursor: pointer;
                z-index: 10000;
            `;

            viewerBtn.onclick = function () {
                showErrorViewer();
            };

            document.body.appendChild(viewerBtn);
        }
    }, 2000);
});

function showErrorViewer() {
    const viewer = document.createElement('div');
    viewer.style.cssText = `
        position: fixed;
        top: 50px;
        right: 10px;
        width: 80%;
        max-width: 600px;
        max-height: 80%;
        overflow-y: auto;
        background-color: #fff;
        border: 1px solid #ddd;
        border-radius: 4px;
        padding: 10px;
        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
        z-index: 10001;
        font-family: monospace;
    `;

    // Add close button
    const closeBtn = document.createElement('button');
    closeBtn.textContent = 'Close';
    closeBtn.style.cssText = `
        float: right;
        background-color: #f44336;
        color: white;
        border: none;
        border-radius: 4px;
        padding: 5px 10px;
        margin-left: 10px;
        cursor: pointer;
    `;

    closeBtn.onclick = function () {
        document.body.removeChild(viewer);
    };

    viewer.appendChild(closeBtn);

    // Add header
    const header = document.createElement('h3');
    header.textContent = `JavaScript Errors (${window.errorLog.length})`;
    viewer.appendChild(header);

    // Add error log
    const logContainer = document.createElement('div');
    window.errorLog.forEach((error, index) => {
        const errorDiv = document.createElement('div');
        errorDiv.style.cssText = `
            margin-bottom: 10px;
            padding: 10px;
            border: 1px solid #f44336;
            border-radius: 4px;
            background-color: #ffebee;
        `;

        errorDiv.innerHTML = `
            <strong>${index + 1}. ${error.message}</strong>
            <div>Location: ${error.source}:${error.lineno}:${error.colno}</div>
            <div>Time: ${new Date(error.timestamp).toLocaleTimeString()}</div>
            ${error.elementInfo?.activeElement ?
                `<div>Active Element: ${error.elementInfo.activeElement.tagName}
                 (id: ${error.elementInfo.activeElement.id},
                  class: ${error.elementInfo.activeElement.className})</div>` : ''}
            <pre style="max-height:200px;overflow:auto;margin-top:10px;padding:5px;background:#f5f5f5;">${error.stack || 'No stack trace available'}</pre>
        `;

        logContainer.appendChild(errorDiv);
    });

    viewer.appendChild(logContainer);
    document.body.appendChild(viewer);
}

// Expose API for manual error logging
window.errorCapture = {
    log: function (message, source) {
        window.errorLog.push({
            message,
            source,
            timestamp: new Date().toISOString(),
            manual: true
        });
    },
    getLog: function () {
        return [...window.errorLog];
    },
    showViewer: showErrorViewer
};

console.log('Error capture initialized');
