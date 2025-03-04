/**
 * Error capture script - Helps diagnose persistent JavaScript errors
 */

// Create a safe logging container
const errorLog = [];

// Setup early error capture
window.addEventListener('error', function (event) {
    const error = {
        message: event.message,
        filename: event.filename,
        lineno: event.lineno,
        colno: event.colno,
        stack: event.error && event.error.stack,
        timestamp: new Date().toISOString(),
        elementInfo: getElementStackTrace()
    };

    errorLog.push(error);

    // Log to console with more details
    console.error("[ERROR CAPTURE]", event.message,
        `at ${event.filename}:${event.lineno}:${event.colno}`,
        "\nStack:", error.stack,
        "\nElements:", error.elementInfo);

    return false; // Let other handlers run
});

// Capture unhandled promise rejections
window.addEventListener('unhandledrejection', function (event) {
    const error = {
        type: 'unhandled promise rejection',
        reason: event.reason,
        message: event.reason?.message || 'Unknown reason',
        stack: event.reason?.stack,
        timestamp: new Date().toISOString()
    };

    errorLog.push(error);
    console.error("[PROMISE ERROR]", error.message, error.stack);

    return false; // Let other handlers run
});

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
        if (errorLog.length > 0) {
            const viewerBtn = document.createElement('button');
            viewerBtn.textContent = `Errors (${errorLog.length})`;
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
    header.textContent = `JavaScript Errors (${errorLog.length})`;
    viewer.appendChild(header);

    // Add error log
    const logContainer = document.createElement('div');
    errorLog.forEach((error, index) => {
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
            <div>Location: ${error.filename}:${error.lineno}:${error.colno}</div>
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
        errorLog.push({
            message,
            source,
            timestamp: new Date().toISOString(),
            manual: true
        });
    },
    getLog: function () {
        return [...errorLog];
    },
    showViewer: showErrorViewer
};

console.log('Error capture initialized');
