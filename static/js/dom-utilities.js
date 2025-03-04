/**
 * DOM Utilities - Safe DOM manipulation functions
 * Prevents errors from null elements and adds debugging
 */

// Safe DOM operation wrapper
function safeDOM(fn) {
    return function (...args) {
        try {
            return fn.apply(this, args);
        } catch (error) {
            console.warn(`DOM operation failed: ${error.message}`);
            return null;
        }
    };
}

// Safe element selection functions
const dom = {
    // Get element by ID with null check
    get: safeDOM(function (id) {
        const element = document.getElementById(id);
        if (!element && window.errorCapture) {
            window.errorCapture.log(`Element not found: #${id}`, 'dom-utilities');
        }
        return element;
    }),

    // Query selector with null check
    query: safeDOM(function (selector, parent = document) {
        if (!parent) return null;
        return parent.querySelector(selector);
    }),

    // Query selector all with empty array fallback
    queryAll: safeDOM(function (selector, parent = document) {
        if (!parent) return [];
        return Array.from(parent.querySelectorAll(selector));
    }),

    // Safe event binding that checks if element exists
    on: safeDOM(function (element, event, handler, options) {
        if (!element) {
            console.warn(`Cannot bind event ${event}: Element does not exist`);
            return { remove: () => { } }; // Return dummy object with remove method
        }

        element.addEventListener(event, handler, options);
        return {
            remove: () => element.removeEventListener(event, handler, options)
        };
    }),

    // Create element with attributes and children
    create: safeDOM(function (tag, attributes = {}, children = []) {
        const element = document.createElement(tag);

        // Set attributes
        Object.entries(attributes).forEach(([key, value]) => {
            if (key === 'style' && typeof value === 'object') {
                Object.assign(element.style, value);
            } else if (key === 'className') {
                element.className = value;
            } else if (key === 'dataset') {
                Object.entries(value).forEach(([dataKey, dataValue]) => {
                    element.dataset[dataKey] = dataValue;
                });
            } else {
                element.setAttribute(key, value);
            }
        });

        // Add children
        children.forEach(child => {
            if (typeof child === 'string') {
                element.appendChild(document.createTextNode(child));
            } else if (child instanceof Node) {
                element.appendChild(child);
            }
        });

        return element;
    }),

    // Safely append element to parent with checks
    append: safeDOM(function (parent, child) {
        if (!parent || !child) return null;
        return parent.appendChild(child);
    }),

    // Wait for an element to be available in DOM
    waitFor: function (selector, timeout = 5000) {
        return new Promise((resolve, reject) => {
            const element = document.querySelector(selector);
            if (element) {
                resolve(element);
                return;
            }

            const observer = new MutationObserver((mutations, obs) => {
                const element = document.querySelector(selector);
                if (element) {
                    obs.disconnect();
                    resolve(element);
                }
            });

            observer.observe(document.body, {
                childList: true,
                subtree: true
            });

            // Set timeout
            setTimeout(() => {
                observer.disconnect();
                reject(new Error(`Element ${selector} not found after ${timeout}ms`));
            }, timeout);
        });
    }
};

// Export to global scope
window.domUtils = dom;

console.log("DOM utilities loaded for safer DOM operations");
