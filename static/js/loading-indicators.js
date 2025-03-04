/**
 * Advanced loading indicators for TQ GenAI Chat
 * Provides various loading animations and states
 */

class LoadingIndicators {
    constructor() {
        // Track active loading indicators
        this.activeIndicators = new Map();

        // Create global loading bar
        this.setupGlobalLoadingBar();
    }

    setupGlobalLoadingBar() {
        // Create loading bar element if it doesn't exist
        if (!document.getElementById('global-loading-bar')) {
            const loadingBar = document.createElement('div');
            loadingBar.id = 'global-loading-bar';
            loadingBar.className = 'loading-bar';
            document.body.appendChild(loadingBar);
        }
    }

    startGlobalLoading() {
        const loadingBar = document.getElementById('global-loading-bar');
        if (!loadingBar) return;

        // Reset and start animation
        loadingBar.style.width = '0';
        loadingBar.style.opacity = '1';

        // Animate to 90% quickly, then slow down
        setTimeout(() => {
            loadingBar.style.width = '90%';
            loadingBar.style.transition = 'width 15s cubic-bezier(0.1, 0.05, 0.1, 0.05)';
        }, 50);
    }

    completeGlobalLoading() {
        const loadingBar = document.getElementById('global-loading-bar');
        if (!loadingBar) return;

        // Finish animation
        loadingBar.style.transition = 'width 0.3s ease-out';
        loadingBar.style.width = '100%';

        // Fade out
        setTimeout(() => {
            loadingBar.style.opacity = '0';

            // Reset after fade
            setTimeout(() => {
                loadingBar.style.width = '0';
                loadingBar.style.transition = '';
            }, 300);
        }, 300);
    }

    /**
     * Add a loading spinner to a container
     * @param {string|Element} container - Container element or selector
     * @param {Object} options - Options for the spinner
     * @returns {string} - ID of the spinner for later reference
     */
    addSpinner(container, options = {}) {
        const defaults = {
            size: 'medium', // small, medium, large
            text: 'Loading...',
            showText: true,
            centered: true,
            type: 'spinner', // spinner, dots, pulse
            color: 'var(--primary-color)'
        };

        const settings = { ...defaults, ...options };
        const targetEl = typeof container === 'string' ? document.querySelector(container) : container;

        if (!targetEl) {
            console.error('Loading target container not found');
            return null;
        }

        // Create unique ID
        const id = `loading-${Date.now()}-${Math.floor(Math.random() * 1000)}`;

        // Create spinner element
        const spinner = document.createElement('div');
        spinner.id = id;
        spinner.className = `loading-indicator loading-${settings.type} loading-${settings.size}`;

        // Set styles based on options
        if (settings.centered) {
            spinner.classList.add('loading-centered');
        }

        // Create spinner content based on type
        let spinnerHtml = '';

        switch (settings.type) {
            case 'spinner':
                spinnerHtml = '<div class="loading-spinner"></div>';
                break;

            case 'dots':
                spinnerHtml = `
                    <div class="loading-dots">
                        <div class="typing-dot"></div>
                        <div class="typing-dot"></div>
                        <div class="typing-dot"></div>
                    </div>
                `;
                break;

            case 'pulse':
                spinnerHtml = `
                    <div class="loading-pulse">
                        <div></div>
                        <div></div>
                        <div></div>
                    </div>
                `;
                break;
        }

        if (settings.showText && settings.text) {
            spinnerHtml += `<div class="loading-text">${settings.text}</div>`;
        }

        spinner.innerHTML = spinnerHtml;

        // Apply custom color
        if (settings.color) {
            spinner.style.setProperty('--loading-color', settings.color);
        }

        // Add to DOM
        targetEl.appendChild(spinner);

        // Store reference
        this.activeIndicators.set(id, {
            element: spinner,
            container: targetEl
        });

        return id;
    }

    /**
     * Add a skeleton loading animation
     * @param {string|Element} container - Container element or selector
     * @param {Object} options - Options for the skeleton
     * @returns {string} - ID of the skeleton for later reference
     */
    addSkeleton(container, options = {}) {
        const defaults = {
            type: 'text', // text, avatar, card, custom
            lines: 3,
            height: '16px',
            width: '100%',
            customHTML: null
        };

        const settings = { ...defaults, ...options };
        const targetEl = typeof container === 'string' ? document.querySelector(container) : container;

        if (!targetEl) {
            console.error('Skeleton target container not found');
            return null;
        }

        // Create unique ID
        const id = `skeleton-${Date.now()}-${Math.floor(Math.random() * 1000)}`;

        // Create skeleton element
        const skeleton = document.createElement('div');
        skeleton.id = id;
        skeleton.className = 'skeleton-container';

        // Create skeleton content based on type
        let skeletonHtml = '';

        switch (settings.type) {
            case 'text':
                // Create lines of skeleton text
                for (let i = 0; i < settings.lines; i++) {
                    // Last line is shorter
                    const width = i === settings.lines - 1 ? '70%' : '100%';
                    skeletonHtml += `
                        <div class="skeleton skeleton-text" style="height: ${settings.height}; width: ${width};"></div>
                    `;
                }
                break;

            case 'avatar':
                skeletonHtml = `
                    <div class="skeleton skeleton-avatar" style="width: ${settings.width}; height: ${settings.height};"></div>
                `;
                break;

            case 'card':
                skeletonHtml = `
                    <div class="skeleton" style="width: 100%; height: ${settings.height}; border-radius: var(--border-radius-md);"></div>
                `;
                break;

            case 'custom':
                // Use custom HTML if provided
                if (settings.customHTML) {
                    skeletonHtml = settings.customHTML;
                }
                break;
        }

        skeleton.innerHTML = skeletonHtml;

        // Add to DOM
        targetEl.appendChild(skeleton);

        // Store reference
        this.activeIndicators.set(id, {
            element: skeleton,
            container: targetEl
        });

        return id;
    }

    /**
     * Create a typing indicator for chat
     * @param {string|Element} container - Container element or selector
     * @returns {string} - ID of the indicator
     */
    addTypingIndicator(container) {
        const targetEl = typeof container === 'string' ? document.querySelector(container) : container;

        if (!targetEl) {
            console.error('Typing indicator target container not found');
            return null;
        }

        // Create unique ID
        const id = `typing-${Date.now()}-${Math.floor(Math.random() * 1000)}`;

        // Create message element with AI styling
        const typingIndicator = document.createElement('div');
        typingIndicator.id = id;
        typingIndicator.className = 'message message-ai is-typing';

        typingIndicator.innerHTML = `
            <div class="message-avatar">
                <i class="fas fa-robot"></i>
            </div>
            <div class="message-bubble">
                <div class="message-typing">
                    <div class="typing-dot"></div>
                    <div class="typing-dot"></div>
                    <div class="typing-dot"></div>
                </div>
            </div>
        `;

        // Add to DOM
        targetEl.appendChild(typingIndicator);

        // Scroll to bottom if this is a chat container
        if (targetEl.classList.contains('chat-messages')) {
            targetEl.scrollTop = targetEl.scrollHeight;
        }

        // Store reference
        this.activeIndicators.set(id, {
            element: typingIndicator,
            container: targetEl
        });

        return id;
    }

    /**
     * Remove a loading indicator
     * @param {string} id - ID of the indicator to remove
     */
    remove(id) {
        if (!this.activeIndicators.has(id)) {
            return false;
        }

        const { element } = this.activeIndicators.get(id);

        // Add exit animation class
        element.classList.add('loading-fade-out');

        // Remove after animation
        setTimeout(() => {
            if (element.parentNode) {
                element.parentNode.removeChild(element);
            }
            this.activeIndicators.delete(id);
        }, 300);

        return true;
    }

    /**
     * Update the text of a loading indicator
     * @param {string} id - ID of the indicator
     * @param {string} text - New text to display
     */
    updateText(id, text) {
        if (!this.activeIndicators.has(id)) {
            return false;
        }

        const { element } = this.activeIndicators.get(id);
        const textEl = element.querySelector('.loading-text');

        if (textEl) {
            textEl.textContent = text;
        }

        return true;
    }

    /**
     * Remove all active loading indicators
     */
    removeAll() {
        this.activeIndicators.forEach((info, id) => {
            this.remove(id);
        });
    }
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    window.loadingIndicators = new LoadingIndicators();
});
