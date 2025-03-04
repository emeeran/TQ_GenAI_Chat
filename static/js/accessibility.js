/**
 * Accessibility enhancements for TQ GenAI Chat
 */

class AccessibilityHelper {
    constructor() {
        this.focusTrap = null;
        this.lastFocused = null;
        this.skipLink = null;
        this.init();
    }

    init() {
        this.createSkipLink();
        this.enhanceKeyboardNavigation();
        this.monitorFocusableElements();
        this.setupScreenReaderAnnouncements();
        this.improveFormLabels();
        this.setupAxe(); // Only in development
    }

    createSkipLink() {
        // Create a skip to main content link for keyboard users
        this.skipLink = document.createElement('a');
        this.skipLink.className = 'skip-link';
        this.skipLink.href = '#chat-messages';
        this.skipLink.innerText = 'Skip to main content';
        this.skipLink.setAttribute('tabindex', '0');

        document.body.insertBefore(this.skipLink, document.body.firstChild);

        this.skipLink.addEventListener('click', (e) => {
            e.preventDefault();
            const main = document.getElementById('chat-messages');
            if (main) {
                main.setAttribute('tabindex', '-1');
                main.focus();
            }
        });
    }

    enhanceKeyboardNavigation() {
        // Improve focus visibility
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Tab') {
                document.body.classList.add('keyboard-user');
            }
        });

        document.addEventListener('mousedown', () => {
            document.body.classList.remove('keyboard-user');
        });

        // Add keyboard shortcuts for common actions
        document.addEventListener('keydown', (e) => {
            // Ctrl+/ - Focus on chat input
            if (e.ctrlKey && e.key === '/') {
                e.preventDefault();
                const chatInput = document.getElementById('chat-input');
                if (chatInput) {
                    chatInput.focus();
                }
            }

            // Alt+S - Toggle sidebar on mobile
            if (e.altKey && e.key === 's') {
                e.preventDefault();
                const sidebarToggle = document.getElementById('sidebar-toggle');
                if (sidebarToggle) {
                    sidebarToggle.click();
                }
            }
        });
    }

    setupFocusTrap(container) {
        // Store last focused element before trapping
        this.lastFocused = document.activeElement;

        // Get all focusable elements
        const focusables = this.getFocusableElements(container);
        if (focusables.length === 0) return;

        // Set focus to first element
        focusables[0].focus();

        // Setup trap
        this.focusTrap = (e) => {
            if (e.key !== 'Tab') return;

            const firstFocusable = focusables[0];
            const lastFocusable = focusables[focusables.length - 1];

            // Handle shift+tab
            if (e.shiftKey) {
                if (document.activeElement === firstFocusable) {
                    e.preventDefault();
                    lastFocusable.focus();
                }
            }
            // Handle tab
            else {
                if (document.activeElement === lastFocusable) {
                    e.preventDefault();
                    firstFocusable.focus();
                }
            }
        };

        // Attach trap
        document.addEventListener('keydown', this.focusTrap);
    }

    releaseFocusTrap() {
        // Remove trap
        if (this.focusTrap) {
            document.removeEventListener('keydown', this.focusTrap);
            this.focusTrap = null;
        }

        // Restore focus
        if (this.lastFocused) {
            this.lastFocused.focus();
            this.lastFocused = null;
        }
    }

    getFocusableElements(container) {
        // All focusable elements
        const selector = 'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])';
        const elements = container.querySelectorAll(selector);

        // Filter only visible and enabled elements
        return Array.from(elements).filter(el => {
            return !el.disabled &&
                !el.hasAttribute('hidden') &&
                el.offsetParent !== null; // Check visibility
        });
    }

    monitorFocusableElements() {
        // Use MutationObserver to ensure dynamically added elements have proper focus
        const observer = new MutationObserver((mutations) => {
            mutations.forEach(mutation => {
                // Check for added nodes
                if (mutation.addedNodes.length) {
                    mutation.addedNodes.forEach(node => {
                        if (node.nodeType === Node.ELEMENT_NODE) {
                            this.checkElementAccessibility(node);
                        }
                    });
                }
            });
        });

        // Observe changes to the document body
        observer.observe(document.body, {
            childList: true,
            subtree: true
        });
    }

    checkElementAccessibility(element) {
        // Check for common accessibility issues and fix them

        // Images should have alt text
        const images = element.querySelectorAll('img:not([alt])');
        images.forEach(img => {
            img.alt = img.src.split('/').pop() || 'Image';
        });

        // Buttons should have accessible names
        const buttons = element.querySelectorAll('button:not([aria-label]):not(:has(*))');
        buttons.forEach(button => {
            if (!button.textContent.trim()) {
                button.setAttribute('aria-label', 'Button');
            }
        });

        // Inputs should have labels
        const inputs = element.querySelectorAll('input:not([aria-label]):not([type="hidden"])');
        inputs.forEach(input => {
            if (!this.hasAssociatedLabel(input)) {
                input.setAttribute('aria-label', input.name || 'Input field');
            }
        });

        // Links should have text content
        const links = element.querySelectorAll('a');
        links.forEach(link => {
            if (!link.textContent.trim() && !link.getAttribute('aria-label')) {
                link.setAttribute('aria-label', link.href || 'Link');
            }
        });
    }

    hasAssociatedLabel(input) {
        // Check if input has an associated label
        if (input.id) {
            // Check for label[for=id]
            const label = document.querySelector(`label[for="${input.id}"]`);
            if (label) return true;
        }

        // Check if input is inside a label
        return input.closest('label') !== null;
    }

    setupScreenReaderAnnouncements() {
        // Create a screen reader announcement area
        const announcer = document.createElement('div');
        announcer.id = 'sr-announcer';
        announcer.setAttribute('aria-live', 'polite');
        announcer.setAttribute('aria-atomic', 'true');
        announcer.className = 'sr-only';
        document.body.appendChild(announcer);

        // Create global announce function
        window.announce = (message, urgent = false) => {
            announcer.setAttribute('aria-live', urgent ? 'assertive' : 'polite');
            announcer.textContent = message;

            // Clear after 3 seconds to prevent announcer from getting too cluttered
            setTimeout(() => {
                announcer.textContent = '';
            }, 3000);
        };
    }

    improveFormLabels() {
        // Automatically enhance form labels for better accessibility
        const inputs = document.querySelectorAll('input:not([type="hidden"]), textarea, select');

        inputs.forEach(input => {
            // Skip if it already has label or aria-label
            if (this.hasAssociatedLabel(input) || input.getAttribute('aria-label')) {
                return;
            }

            // Create label from placeholder if exists
            const placeholder = input.getAttribute('placeholder');
            if (placeholder) {
                const id = input.id || `input-${Math.random().toString(36).substr(2, 9)}`;
                input.id = id;

                const label = document.createElement('label');
                label.setAttribute('for', id);
                label.className = 'sr-only'; // Visually hidden but available to screen readers
                label.textContent = placeholder;

                input.parentNode.insertBefore(label, input);
            }
        });
    }

    setupAxe() {
        // Only in development mode
        if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
            // Dynamically load axe-core for development testing
            const script = document.createElement('script');
            script.src = 'https://cdnjs.cloudflare.com/ajax/libs/axe-core/4.5.2/axe.min.js';
            document.head.appendChild(script);

            script.onload = () => {
                if (window.axe) {
                    window.axe.run((err, results) => {
                        if (err) throw err;
                        console.group('Accessibility Issues:');
                        console.log(results.violations);
                        console.groupEnd();
                    });
                }
            };
        }
    }
}

// Initialize accessibility helper
document.addEventListener('DOMContentLoaded', () => {
    window.accessibilityHelper = new AccessibilityHelper();
});
