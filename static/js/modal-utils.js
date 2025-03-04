/**
 * Modal utility functions for TQ GenAI Chat
 * Provides safe modal creation and management
 */

// Private store for modal state
const _modalState = {
    activeModals: new Set(),
    eventHandlers: {}
};

// Safe DOM manipulation helper
function safeDOM(func) {
    return function (...args) {
        try {
            return func(...args);
        } catch (error) {
            console.error(`DOM operation failed: ${error.message}`);
            return null;
        }
    };
}

// Safe querySelector that never throws
const safeQuerySelector = safeDOM((selector, parent = document) =>
    parent ? parent.querySelector(selector) : null);

// Safe getElementById that never throws
const safeGetElementById = safeDOM(id => document.getElementById(id));

// Create a modal with safe DOM operations
function createSafeModal(id, options = {}) {
    // Check if modal already exists
    const existingModal = safeGetElementById(id);
    if (existingModal) return existingModal;

    console.log(`Creating modal: ${id} safely`);

    try {
        // Create modal container
        const modal = document.createElement('div');
        modal.id = id;
        modal.className = `modal ${options.className || ''}`;

        // Create content structure
        const content = `
      <div class="modal-content">
        <div class="modal-header">
          <h3>${options.title || 'Modal'}</h3>
          <button class="modal-close" data-modal-id="${id}">&times;</button>
        </div>
        <div class="modal-body">
          ${options.content || ''}
        </div>
      </div>
    `;

        modal.innerHTML = content;

        // Add to DOM
        document.body.appendChild(modal);

        // Set up delegated event handling for this modal
        setupModalEvents(modal);

        return modal;
    } catch (error) {
        console.error(`Failed to create modal ${id}: ${error.message}`);
        return null;
    }
}

// Setup event delegation for a modal
function setupModalEvents(modal) {
    if (!modal) return;

    const modalId = modal.id;

    // Use event delegation instead of direct binding to avoid null errors
    if (!_modalState.eventHandlers[modalId]) {
        const handler = function (event) {
            // Close button clicked
            if (event.target.classList.contains('modal-close')) {
                hideModal(modalId);
                return;
            }

            // Background clicked (modal itself is the target)
            if (event.target === modal) {
                hideModal(modalId);
            }
        };

        modal.addEventListener('click', handler);
        _modalState.eventHandlers[modalId] = handler;
    }
}

// Show modal safely
function showModal(id) {
    const modal = safeGetElementById(id);
    if (!modal) {
        console.error(`Cannot show modal: Element with id "${id}" not found`);
        return false;
    }

    modal.style.display = 'flex';
    modal.classList.remove('hidden');
    _modalState.activeModals.add(id);

    return true;
}

// Hide modal safely
function hideModal(id) {
    const modal = safeGetElementById(id);
    if (!modal) {
        console.error(`Cannot hide modal: Element with id "${id}" not found`);
        return false;
    }

    modal.classList.add('hidden');
    setTimeout(() => {
        if (modal.classList.contains('hidden')) {
            modal.style.display = 'none';
        }
    }, 300);

    _modalState.activeModals.delete(id);

    return true;
}

// Set content safely
function setModalContent(id, content) {
    const modal = safeGetElementById(id);
    if (!modal) {
        console.error(`Cannot set modal content: Element with id "${id}" not found`);
        return false;
    }

    const body = safeQuerySelector('.modal-body', modal);
    if (!body) {
        console.error(`Modal body not found in modal ${id}`);
        return false;
    }

    body.innerHTML = content;
    return true;
}

// Export the modal utility functions
window.modalUtils = {
    createModal: createSafeModal,
    showModal: showModal,
    hideModal: hideModal,
    setContent: setModalContent
};
