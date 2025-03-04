/**
 * Keyboard shortcuts system for TQ GenAI Chat
 * Provides configurable keyboard shortcuts for common actions
 */

class KeyboardShortcuts {
    constructor() {
        this.shortcuts = [
            {
                key: 'k',
                modifier: 'ctrl',
                description: 'Open command palette',
                action: () => {
                    if (typeof toggleCommandPalette === 'function') {
                        toggleCommandPalette(true);
                    }
                }
            },
            {
                key: '/',
                modifier: 'ctrl',
                description: 'Focus chat input',
                action: () => {
                    const chatInput = document.getElementById('chat-input');
                    if (chatInput) {
                        chatInput.focus();
                    }
                }
            },
            {
                key: 'ArrowUp',
                modifier: 'alt',
                description: 'Edit last message',
                action: () => {
                    if (window.chatClient && typeof window.chatClient.editLastMessage === 'function') {
                        window.chatClient.editLastMessage();
                    }
                }
            },
            {
                key: 'Escape',
                description: 'Close open dialogs',
                action: () => {
                    // Close command palette
                    if (typeof toggleCommandPalette === 'function') {
                        toggleCommandPalette(false);
                    }

                    // Close other dialogs
                    document.querySelectorAll('.modal:not(.hidden)').forEach(modal => {
                        modal.classList.add('hidden');
                    });

                    // Close preferences panel
                    const prefsPanel = document.getElementById('preferences-panel');
                    if (prefsPanel && !prefsPanel.classList.contains('hidden')) {
                        prefsPanel.classList.add('hidden');
                    }
                }
            },
            {
                key: 'Enter',
                modifier: 'ctrl',
                description: 'Send message',
                action: () => {
                    const chatForm = document.getElementById('chat-form');
                    if (chatForm) {
                        const event = new Event('submit', { cancelable: true });
                        chatForm.dispatchEvent(event);
                    }
                }
            },
            {
                key: 'l',
                modifier: ['ctrl', 'shift'],
                description: 'Clear chat',
                action: () => {
                    if (window.chatClient && typeof window.chatClient.clearChat === 'function') {
                        if (confirm('Are you sure you want to clear the chat?')) {
                            window.chatClient.clearChat();
                        }
                    }
                }
            },
            {
                key: 's',
                modifier: 'ctrl',
                description: 'Save chat',
                action: (e) => {
                    e.preventDefault();
                    if (window.chatClient && typeof window.chatClient.saveChat === 'function') {
                        window.chatClient.saveChat();
                    }
                }
            },
            {
                key: ',',
                modifier: 'ctrl',
                description: 'Open preferences',
                action: (e) => {
                    e.preventDefault();
                    const prefsBtn = document.getElementById('preferences-btn');
                    if (prefsBtn) {
                        prefsBtn.click();
                    }
                }
            }
        ];

        this.initShortcuts();
        this.initHelpModal();
    }

    initShortcuts() {
        document.addEventListener('keydown', (e) => {
            // Don't trigger shortcuts when typing in input fields
            if (['input', 'textarea', 'select'].includes(e.target.tagName.toLowerCase())) {
                return;
            }

            for (const shortcut of this.shortcuts) {
                if (this.matchesShortcut(e, shortcut)) {
                    shortcut.action(e);
                    break;
                }
            }
        });
    }

    matchesShortcut(event, shortcut) {
        // Check if key matches
        if (event.key !== shortcut.key) {
            return false;
        }

        // Check modifiers
        if (shortcut.modifier) {
            if (Array.isArray(shortcut.modifier)) {
                // Multiple modifiers required
                for (const mod of shortcut.modifier) {
                    if (!this.checkModifier(event, mod)) {
                        return false;
                    }
                }
            } else {
                // Single modifier
                if (!this.checkModifier(event, shortcut.modifier)) {
                    return false;
                }
            }
        }

        return true;
    }

    checkModifier(event, modifier) {
        switch (modifier) {
            case 'ctrl': return event.ctrlKey || event.metaKey;
            case 'alt': return event.altKey;
            case 'shift': return event.shiftKey;
            default: return false;
        }
    }

    initHelpModal() {
        // Create keyboard shortcuts help modal if it doesn't exist
        if (!document.getElementById('keyboard-shortcuts-modal')) {
            const modal = document.createElement('div');
            modal.id = 'keyboard-shortcuts-modal';
            modal.className = 'modal hidden';

            let shortcutList = '';
            this.shortcuts.forEach(shortcut => {
                const keys = [];

                if (Array.isArray(shortcut.modifier)) {
                    shortcut.modifier.forEach(mod => {
                        keys.push(this.formatModifier(mod));
                    });
                } else if (shortcut.modifier) {
                    keys.push(this.formatModifier(shortcut.modifier));
                }

                keys.push(this.formatKey(shortcut.key));

                shortcutList += `
                <div class="shortcut-item">
                    <div class="shortcut-keys">${keys.map(k => `<kbd>${k}</kbd>`).join(' + ')}</div>
                    <div class="shortcut-description">${shortcut.description}</div>
                </div>`;
            });

            modal.innerHTML = `
            <div class="modal-content">
                <div class="modal-header">
                    <h3>Keyboard Shortcuts</h3>
                    <button class="close-modal" aria-label="Close keyboard shortcuts">&times;</button>
                </div>
                <div class="modal-body">
                    <div class="shortcuts-list">
                        ${shortcutList}
                    </div>
                </div>
                <div class="modal-footer">
                    <button class="btn btn-outline close-modal">Close</button>
                </div>
            </div>`;

            document.body.appendChild(modal);

            // Add keyboard shortcut to show this modal
            this.shortcuts.push({
                key: '?',
                modifier: 'shift',
                description: 'Show this help menu',
                action: () => {
                    modal.classList.remove('hidden');
                }
            });
        }
    }

    formatModifier(mod) {
        switch (mod) {
            case 'ctrl': return navigator.platform.includes('Mac') ? '⌘' : 'Ctrl';
            case 'alt': return navigator.platform.includes('Mac') ? '⌥' : 'Alt';
            case 'shift': return navigator.platform.includes('Mac') ? '⇧' : 'Shift';
            default: return mod;
        }
    }

    formatKey(key) {
        switch (key) {
            case 'ArrowUp': return '↑';
            case 'ArrowDown': return '↓';
            case 'ArrowLeft': return '←';
            case 'ArrowRight': return '→';
            case 'Enter': return '↵';
            case 'Escape': return 'Esc';
            default: return key.toUpperCase();
        }
    }
}

// Initialize keyboard shortcuts on page load
document.addEventListener('DOMContentLoaded', () => {
    window.keyboardShortcuts = new KeyboardShortcuts();
});
