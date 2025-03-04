/**
 * Modal Manager - Centralized modal handling for TQ GenAI Chat
 * Provides consistent modal creation and management to avoid conflicts
 */

(function () {
    // Private store for modal references
    const modals = {};

    // Public API
    window.modalManager = {
        // Create a new modal or return existing one
        createModal: function (id, options = {}) {
            // Return existing modal if already created
            if (modals[id]) {
                return modals[id];
            }

            console.log(`Creating modal: ${id}`);

            // Create modal element
            const modal = document.createElement('div');
            modal.id = id;
            modal.className = 'modal ' + (options.className || '');

            // Create modal content
            const content = document.createElement('div');
            content.className = 'modal-content';
            modal.appendChild(content);

            // Create header if title provided
            if (options.title) {
                const header = document.createElement('div');
                header.className = 'modal-header';
                header.innerHTML = `
                    <h3>${options.title}</h3>
                    <button class="modal-close">&times;</button>
                `;
                content.appendChild(header);
            }

            // Create body
            const body = document.createElement('div');
            body.className = 'modal-body';
            if (options.content) {
                body.innerHTML = options.content;
            }
            content.appendChild(body);

            // Add to document
            document.body.appendChild(modal);

            // Setup event handlers
            const closeBtn = modal.querySelector('.modal-close');
            if (closeBtn) {
                closeBtn.addEventListener('click', () => this.hideModal(id));
            }

            // Close on background click if configured
            if (options.closeOnBackgroundClick !== false) {
                modal.addEventListener('click', (event) => {
                    if (event.target === modal) {
                        this.hideModal(id);
                    }
                });
            }

            // Store reference
            modals[id] = {
                element: modal,
                body: body
            };

            return modals[id];
        },

        // Show a modal
        showModal: function (id) {
            const modal = modals[id]?.element;
            if (modal) {
                modal.style.display = 'flex';
                modal.classList.remove('hidden');

                // Trigger event
                window.dispatchEvent(new CustomEvent('modal-shown', {
                    detail: { id: id }
                }));
            } else {
                console.error(`Modal not found: ${id}`);
            }
        },

        // Hide a modal
        hideModal: function (id) {
            const modal = modals[id]?.element;
            if (modal) {
                modal.classList.add('hidden');

                // Trigger event
                window.dispatchEvent(new CustomEvent('modal-hidden', {
                    detail: { id: id }
                }));
            }
        },

        // Set modal content
        setModalContent: function (id, content) {
            const modalBody = modals[id]?.body;
            if (modalBody) {
                modalBody.innerHTML = content;
            }
        },

        // Get modal element
        getModalElement: function (id) {
            return modals[id]?.element;
        },

        // Get modal body element
        getModalBody: function (id) {
            return modals[id]?.body;
        }
    };
})();
