/**
 * DOM utilities for TQ GenAI Chat
 * Provides safer DOM manipulation utilities
 */

// Use window.domUtils instead of creating global variable to avoid duplicate declaration
window.domUtils = (function () {
    // Store element references
    const elements = {};

    // Counter for generating unique IDs
    let idCounter = 0;

    // Utility functions
    return {
        /**
         * Safely get an element by ID, with caching for performance
         * @param {string} id - Element ID
         * @param {boolean} [forceRefresh=false] - Whether to bypass cache
         * @returns {HTMLElement|null} - The element or null if not found
         */
        get: function (id, forceRefresh = false) {
            if (!forceRefresh && elements[id]) {
                return elements[id];
            }

            const element = document.getElementById(id);
            if (element) {
                elements[id] = element;
                return element;
            }

            return null;
        },

        /**
         * Safely query for an element
         * @param {string} selector - CSS selector
         * @param {HTMLElement|Document} [context=document] - Parent element for query
         * @returns {HTMLElement|null} - First matching element or null
         */
        query: function (selector, context = document) {
            try {
                return context.querySelector(selector);
            } catch (e) {
                console.error('DOM query error:', e);
                return null;
            }
        },

        /**
         * Safely query for all matching elements
         * @param {string} selector - CSS selector
         * @param {HTMLElement|Document} [context=document] - Parent element for query
         * @returns {NodeList} - List of matching elements or empty NodeList
         */
        queryAll: function (selector, context = document) {
            try {
                return context.querySelectorAll(selector);
            } catch (e) {
                console.error('DOM queryAll error:', e);
                return document.createDocumentFragment().childNodes;
            }
        },

        /**
         * Safely create an element with attributes and properties
         * @param {string} tag - HTML tag name
         * @param {Object} [options] - Element options
         * @param {Object} [options.attrs] - HTML attributes
         * @param {Object} [options.props] - Element properties
         * @param {Object} [options.styles] - CSS styles
         * @param {Object} [options.events] - Event listeners
         * @param {string|Node|Array} [options.children] - Child nodes
         * @returns {HTMLElement} - The created element
         */
        create: function (tag, options = {}) {
            const element = document.createElement(tag);

            // Set attributes
            if (options.attrs) {
                Object.entries(options.attrs).forEach(([key, value]) => {
                    if (value !== null && value !== undefined) {
                        element.setAttribute(key, value);
                    }
                });
            }

            // Set properties
            if (options.props) {
                Object.entries(options.props).forEach(([key, value]) => {
                    if (value !== null && value !== undefined) {
                        element[key] = value;
                    }
                });
            }

            // Set styles
            if (options.styles) {
                Object.entries(options.styles).forEach(([key, value]) => {
                    if (value !== null && value !== undefined) {
                        element.style[key] = value;
                    }
                });
            }

            // Add event listeners
            if (options.events) {
                Object.entries(options.events).forEach(([event, handler]) => {
                    element.addEventListener(event, handler);
                });
            }

            // Add children
            if (options.children) {
                const addChild = (child) => {
                    if (typeof child === 'string') {
                        element.appendChild(document.createTextNode(child));
                    } else if (child instanceof Node) {
                        element.appendChild(child);
                    }
                };

                if (Array.isArray(options.children)) {
                    options.children.forEach(addChild);
                } else {
                    addChild(options.children);
                }
            }

            return element;
        },

        /**
         * Generate a unique ID for elements
         * @param {string} [prefix='element'] - ID prefix
         * @returns {string} - Unique ID
         */
        uniqueId: function (prefix = 'element') {
            return `${prefix}-${++idCounter}`;
        },

        /**
         * Safely remove an element
         * @param {HTMLElement|string} element - Element or element ID
         * @returns {boolean} - Whether removal was successful
         */
        remove: function (element) {
            try {
                if (typeof element === 'string') {
                    element = this.get(element);
                }

                if (element && element.parentNode) {
                    element.parentNode.removeChild(element);
                    return true;
                }
            } catch (e) {
                console.error('DOM remove error:', e);
            }

            return false;
        },

        /**
         * Add event listener with automatic cleanup
         * @param {HTMLElement|Window|Document} element - Element to attach listener to
         * @param {string} eventType - Event type (e.g., 'click')
         * @param {Function} handler - Event handler
         * @param {Object} [options] - Event listener options
         * @returns {Function} - Function to remove the event listener
         */
        addEvent: function (element, eventType, handler, options) {
            try {
                element.addEventListener(eventType, handler, options);

                // Return a function that removes the listener
                return function cleanup() {
                    element.removeEventListener(eventType, handler, options);
                };
            } catch (e) {
                console.error('DOM addEvent error:', e);
                // Return a no-op function
                return function noop() { };
            }
        },

        /**
         * Safely set HTML content
         * @param {HTMLElement|string} element - Element or element ID
         * @param {string} html - HTML content
         * @returns {HTMLElement|null} - The updated element or null
         */
        setHTML: function (element, html) {
            try {
                if (typeof element === 'string') {
                    element = this.get(element);
                }

                if (element) {
                    element.innerHTML = html;
                    return element;
                }
            } catch (e) {
                console.error('DOM setHTML error:', e);
            }

            return null;
        },

        /**
         * Safely set text content
         * @param {HTMLElement|string} element - Element or element ID
         * @param {string} text - Text content
         * @returns {HTMLElement|null} - The updated element or null
         */
        setText: function (element, text) {
            try {
                if (typeof element === 'string') {
                    element = this.get(element);
                }

                if (element) {
                    element.textContent = text;
                    return element;
                }
            } catch (e) {
                console.error('DOM setText error:', e);
            }

            return null;
        },

        /**
         * Toggle class on an element
         * @param {HTMLElement|string} element - Element or element ID
         * @param {string} className - CSS class to toggle
         * @param {boolean} [force] - Whether to force add or remove
         * @returns {boolean|undefined} - Result of the toggle operation
         */
        toggleClass: function (element, className, force) {
            try {
                if (typeof element === 'string') {
                    element = this.get(element);
                }

                if (element && element.classList) {
                    return element.classList.toggle(className, force);
                }
            } catch (e) {
                console.error('DOM toggleClass error:', e);
            }

            return undefined;
        },

        /**
         * Check if element has a class
         * @param {HTMLElement|string} element - Element or element ID
         * @param {string} className - CSS class to check
         * @returns {boolean} - Whether element has the class
         */
        hasClass: function (element, className) {
            try {
                if (typeof element === 'string') {
                    element = this.get(element);
                }

                return element && element.classList && element.classList.contains(className);
            } catch (e) {
                console.error('DOM hasClass error:', e);
                return false;
            }
        },

        /**
         * Add classes to an element
         * @param {HTMLElement|string} element - Element or element ID
         * @param {...string} classNames - CSS classes to add
         * @returns {HTMLElement|null} - The updated element or null
         */
        addClass: function (element, ...classNames) {
            try {
                if (typeof element === 'string') {
                    element = this.get(element);
                }

                if (element && element.classList) {
                    element.classList.add(...classNames);
                    return element;
                }
            } catch (e) {
                console.error('DOM addClass error:', e);
            }

            return null;
        },

        /**
         * Remove classes from an element
         * @param {HTMLElement|string} element - Element or element ID
         * @param {...string} classNames - CSS classes to remove
         * @returns {HTMLElement|null} - The updated element or null
         */
        removeClass: function (element, ...classNames) {
            try {
                if (typeof element === 'string') {
                    element = this.get(element);
                }

                if (element && element.classList) {
                    element.classList.remove(...classNames);
                    return element;
                }
            } catch (e) {
                console.error('DOM removeClass error:', e);
            }

            return null;
        },

        /**
         * Check if an element matches a selector
         * @param {HTMLElement} element - Element to check
         * @param {string} selector - CSS selector
         * @returns {boolean} - Whether element matches the selector
         */
        matches: function (element, selector) {
            try {
                if (!element) return false;

                const matchesMethod = element.matches ||
                    element.matchesSelector ||
                    element.msMatchesSelector ||
                    element.mozMatchesSelector ||
                    element.webkitMatchesSelector ||
                    element.oMatchesSelector;

                if (matchesMethod) {
                    return matchesMethod.call(element, selector);
                }
            } catch (e) {
                console.error('DOM matches error:', e);
            }

            return false;
        },

        /**
         * Find closest ancestor matching selector
         * @param {HTMLElement} element - Starting element
         * @param {string} selector - CSS selector
         * @returns {HTMLElement|null} - Matching ancestor or null
         */
        closest: function (element, selector) {
            try {
                if (!element) return null;

                // Use native closest if available
                if (element.closest) {
                    return element.closest(selector);
                }

                // Fallback implementation
                let currentEl = element;
                while (currentEl) {
                    if (this.matches(currentEl, selector)) {
                        return currentEl;
                    }
                    currentEl = currentEl.parentElement;
                }
            } catch (e) {
                console.error('DOM closest error:', e);
            }

            return null;
        }
    };
})();
