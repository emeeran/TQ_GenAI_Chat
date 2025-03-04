/**
 * Modern UI interactions for TQ GenAI Chat
 */

document.addEventListener('DOMContentLoaded', function () {
    // Theme toggle functionality
    initThemeToggle();

    // Mobile sidebar toggle
    initSidebarToggle();

    // Modal functionality
    initModals();

    // Auto-resize textarea
    initTextareaResize();

    // Initialize tooltips
    initTooltips();

    // Initialize animations for messages
    initMessageAnimations();

    // Add scroll animation for messages
    initMessageScroll();

    // Code highlight functionality
    highlightCode();

    // Initialize keyboard navigation
    initKeyboardNavigation();

    // Initialize command palette
    initCommandPalette();
});

// Theme Toggle
function initThemeToggle() {
    const themeToggle = document.getElementById('theme-toggle-input');

    // Check for saved theme preference or respect OS preference
    const prefersDarkMode = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
    const savedTheme = localStorage.getItem('theme');

    // Apply theme
    if (savedTheme === 'dark' || (!savedTheme && prefersDarkMode)) {
        document.body.classList.add('dark-theme');
        themeToggle.checked = true;
    }

    // Handle theme toggle click
    themeToggle.addEventListener('change', function () {
        if (this.checked) {
            document.body.classList.add('dark-theme');
            localStorage.setItem('theme', 'dark');
        } else {
            document.body.classList.remove('dark-theme');
            localStorage.setItem('theme', 'light');
        }
    });
}

// Mobile Sidebar Toggle
function initSidebarToggle() {
    const sidebarToggle = document.getElementById('sidebar-toggle');
    const sidebar = document.querySelector('.sidebar');

    if (sidebarToggle && sidebar) {
        sidebarToggle.addEventListener('click', function () {
            sidebar.classList.toggle('active');
        });

        // Close sidebar when clicking outside on mobile
        document.addEventListener('click', function (event) {
            if (window.innerWidth <= 768 &&
                sidebar.classList.contains('active') &&
                !sidebar.contains(event.target) &&
                event.target !== sidebarToggle) {
                sidebar.classList.remove('active');
            }
        });
    }
}

// Modal functionality
function initModals() {
    // Upload modal
    const uploadBtn = document.getElementById('upload-btn');
    const uploadModal = document.getElementById('upload-modal');
    const closeModalBtns = document.querySelectorAll('.close-modal');

    if (uploadBtn && uploadModal) {
        uploadBtn.addEventListener('click', function () {
            uploadModal.classList.remove('hidden');
            document.body.style.overflow = 'hidden'; // Prevent scrolling
        });
    }

    closeModalBtns.forEach(btn => {
        btn.addEventListener('click', closeModal);
    });

    // Close modal when clicking outside
    document.addEventListener('click', function (event) {
        if (event.target.classList.contains('modal')) {
            closeModal();
        }
    });

    // Close modal with ESC key
    document.addEventListener('keydown', function (event) {
        if (event.key === 'Escape') {
            closeModal();
        }
    });

    function closeModal() {
        const modals = document.querySelectorAll('.modal');
        modals.forEach(modal => {
            modal.classList.add('hidden');
        });
        document.body.style.overflow = '';
    }
}

// Auto-resize textarea
function initTextareaResize() {
    const chatInput = document.getElementById('chat-input');
    if (chatInput) {
        chatInput.addEventListener('input', function () {
            this.style.height = 'auto';
            this.style.height = Math.min(200, this.scrollHeight) + 'px';
        });

        // Initialize height on page load
        setTimeout(() => {
            chatInput.style.height = 'auto';
            chatInput.style.height = Math.min(200, chatInput.scrollHeight) + 'px';
        }, 100);
    }
}

// Tooltips
function initTooltips() {
    const tooltipElements = document.querySelectorAll('[data-tooltip]');

    tooltipElements.forEach(element => {
        const tooltipText = element.getAttribute('data-tooltip');
        const tooltip = document.createElement('div');
        tooltip.className = 'tooltip';
        tooltip.textContent = tooltipText;

        element.addEventListener('mouseenter', () => {
            document.body.appendChild(tooltip);
            const rect = element.getBoundingClientRect();
            tooltip.style.top = `${rect.bottom + window.scrollY + 5}px`;
            tooltip.style.left = `${rect.left + window.scrollX + rect.width / 2 - tooltip.offsetWidth / 2}px`;
            tooltip.style.opacity = '1';
        });

        element.addEventListener('mouseleave', () => {
            tooltip.style.opacity = '0';
            setTimeout(() => {
                if (tooltip.parentNode) {
                    tooltip.parentNode.removeChild(tooltip);
                }
            }, 300);
        });
    });
}

// Code highlight functionality
function highlightCode() {
    document.querySelectorAll('pre code').forEach((block) => {
        // If using a library like highlight.js
        // hljs.highlightBlock(block);

        // Simple syntax highlighting
        if (block.classList.contains('language-javascript')) {
            const keywords = ['function', 'return', 'if', 'else', 'for', 'while', 'let', 'const', 'var', 'async', 'await', 'class', 'import', 'export'];
            keywords.forEach(word => {
                const regex = new RegExp(`\\b${word}\\b`, 'g');
                block.innerHTML = block.innerHTML.replace(
                    regex,
                    `<span class="keyword">${word}</span>`
                );
            });
        }
    });
}

// Add scroll animation for messages
function initMessageScroll() {
    const chatMessages = document.getElementById('chat-messages');
    if (chatMessages) {
        // Scroll to bottom when new messages arrive
        const observer = new MutationObserver(() => {
            chatMessages.scrollTop = chatMessages.scrollHeight;
        });

        observer.observe(chatMessages, { childList: true });
    }
}

// Initialize animations for messages
function initMessageAnimations() {
    const messages = document.querySelectorAll('.message');

    messages.forEach((message, index) => {
        // Add staggered fade-in animation
        message.style.opacity = '0';
        message.style.transform = 'translateY(20px)';

        setTimeout(() => {
            message.style.transition = 'opacity 0.3s ease, transform 0.3s ease';
            message.style.opacity = '1';
            message.style.transform = 'translateY(0)';
        }, 100 * index);
    });
}

// Add keyboard navigation support
function initKeyboardNavigation() {
    // Navigation between provider tabs using keyboard
    const providerTabs = document.getElementById('provider-tabs');
    if (providerTabs) {
        // Make tabs keyboard navigable
        providerTabs.setAttribute('role', 'tablist');
        const tabs = providerTabs.querySelectorAll('.provider-tab');

        tabs.forEach((tab, index) => {
            tab.setAttribute('role', 'tab');
            tab.setAttribute('tabindex', '0');
            tab.setAttribute('id', `provider-${tab.dataset.provider}`);
            tab.setAttribute('aria-selected', tab.classList.contains('active') ? 'true' : 'false');

            // Add keyboard navigation
            tab.addEventListener('keydown', (e) => {
                let nextTab;

                // Handle arrow keys
                switch (e.key) {
                    case 'ArrowRight':
                        nextTab = index < tabs.length - 1 ? tabs[index + 1] : tabs[0];
                        break;
                    case 'ArrowLeft':
                        nextTab = index > 0 ? tabs[index - 1] : tabs[tabs.length - 1];
                        break;
                    case 'Home':
                        nextTab = tabs[0];
                        break;
                    case 'End':
                        nextTab = tabs[tabs.length - 1];
                        break;
                    case ' ':
                    case 'Enter':
                        tab.click();
                        return;
                    default:
                        return; // Exit for other keys
                }

                if (nextTab) {
                    e.preventDefault();
                    nextTab.focus();
                }
            });
        });
    }

    // Add command palette (Ctrl+K)
    document.addEventListener('keydown', (e) => {
        if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
            e.preventDefault();
            toggleCommandPalette();
        }
        // Add Escape key handler for modals
        if (e.key === 'Escape') {
            const modals = document.querySelectorAll('.modal:not(.hidden)');
            if (modals.length > 0) {
                e.preventDefault();
                modals.forEach(modal => modal.classList.add('hidden'));
            }
        }
    });
}

// Add command palette feature for quick actions
function initCommandPalette() {
    // Create command palette UI if not exists
    if (!document.getElementById('command-palette')) {
        const palette = document.createElement('div');
        palette.id = 'command-palette';
        palette.className = 'command-palette hidden';
        palette.setAttribute('role', 'dialog');
        palette.setAttribute('aria-modal', 'true');
        palette.setAttribute('aria-label', 'Command Palette');

        palette.innerHTML = `
            <div class="command-header">
                <div class="command-search">
                    <i class="fas fa-search"></i>
                    <input type="text" id="command-input" placeholder="Type a command or search..."
                        autocomplete="off" spellcheck="false">
                </div>
                <button class="close-command" aria-label="Close command palette">&times;</button>
            </div>
            <div class="command-results">
                <div class="command-group">
                    <div class="command-group-title">Commands</div>
                    <div class="command-list" id="command-list"></div>
                </div>
            </div>
            <div class="command-footer">
                <div class="command-help">
                    <span><kbd>↑</kbd><kbd>↓</kbd> to navigate</span>
                    <span><kbd>Enter</kbd> to select</span>
                    <span><kbd>Esc</kbd> to close</span>
                </div>
            </div>
        `;

        document.body.appendChild(palette);
    }

    // Define available commands
    const commands = [
        {
            id: 'toggle-theme',
            name: 'Toggle Dark/Light Mode',
            icon: 'fas fa-moon',
            shortcut: 'Ctrl+Shift+L',
            action: () => {
                const themeToggle = document.getElementById('theme-toggle-input');
                if (themeToggle) {
                    themeToggle.click();
                }
            }
        },
        {
            id: 'clear-chat',
            name: 'Clear Current Chat',
            icon: 'fas fa-eraser',
            action: () => {
                if (window.chatClient && typeof window.chatClient.clearChat === 'function') {
                    window.chatClient.clearChat();
                } else {
                    const chatMessages = document.getElementById('chat-messages');
                    if (chatMessages) {
                        chatMessages.innerHTML = '';
                    }
                }
            }
        },
        {
            id: 'save-chat',
            name: 'Save Current Chat',
            icon: 'fas fa-save',
            shortcut: 'Ctrl+S',
            action: () => {
                if (window.chatClient && typeof window.chatClient.saveChat === 'function') {
                    window.chatClient.saveChat();
                }
            }
        },
        {
            id: 'export-chat',
            name: 'Export Chat as Markdown',
            icon: 'fas fa-file-export',
            action: () => {
                if (window.chatClient && typeof window.chatClient.exportChat === 'function') {
                    window.chatClient.exportChat();
                }
            }
        },
        {
            id: 'upload-files',
            name: 'Upload Document',
            icon: 'fas fa-upload',
            action: () => {
                const uploadBtn = document.getElementById('upload-btn');
                if (uploadBtn) {
                    uploadBtn.click();
                }
            }
        },
        {
            id: 'toggle-preferences',
            name: 'Open Preferences',
            icon: 'fas fa-cog',
            shortcut: 'Ctrl+,',
            action: () => {
                const preferencesBtn = document.getElementById('preferences-btn');
                if (preferencesBtn) {
                    preferencesBtn.click();
                }
            }
        },
        {
            id: 'voice-input',
            name: 'Toggle Voice Input',
            icon: 'fas fa-microphone',
            action: () => {
                const micBtn = document.getElementById('mic-btn');
                if (micBtn) {
                    micBtn.click();
                }
            }
        }
    ];

    // Setup command palette functionality
    const commandInput = document.getElementById('command-input');
    const commandList = document.getElementById('command-list');
    const palette = document.getElementById('command-palette');
    const closeBtn = palette.querySelector('.close-command');

    function renderCommands(filterText = '') {
        // Filter commands based on input
        const filtered = filterText.length > 0
            ? commands.filter(cmd =>
                cmd.name.toLowerCase().includes(filterText.toLowerCase()) ||
                (cmd.tags && cmd.tags.some(tag => tag.toLowerCase().includes(filterText.toLowerCase())))
            )
            : commands;

        // Render commands to list
        commandList.innerHTML = filtered.length > 0
            ? filtered.map((cmd, index) => `
                <div class="command-item" data-id="${cmd.id}" tabindex="0" ${index === 0 ? 'aria-selected="true"' : ''}>
                    <div class="command-icon"><i class="${cmd.icon}"></i></div>
                    <div class="command-name">${cmd.name}</div>
                    ${cmd.shortcut ? `<div class="command-shortcut">${cmd.shortcut}</div>` : ''}
                </div>
            `).join('')
            : '<div class="command-empty">No commands found</div>';

        // Add click handlers
        commandList.querySelectorAll('.command-item').forEach(item => {
            item.addEventListener('click', () => {
                executeCommand(item.dataset.id);
            });

            item.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    executeCommand(item.dataset.id);
                }
            });
        });
    }

    function executeCommand(id) {
        const command = commands.find(cmd => cmd.id === id);
        if (command && typeof command.action === 'function') {
            command.action();
            toggleCommandPalette(false); // Hide palette after executing command
        }
    }

    // Input handling
    if (commandInput) {
        commandInput.addEventListener('input', () => {
            renderCommands(commandInput.value);
        });

        commandInput.addEventListener('keydown', (e) => {
            const items = commandList.querySelectorAll('.command-item');
            const selectedItem = commandList.querySelector('[aria-selected="true"]');
            let selectedIndex = Array.from(items).indexOf(selectedItem);

            switch (e.key) {
                case 'ArrowDown':
                    e.preventDefault();
                    if (selectedIndex < items.length - 1) {
                        selectedIndex++;
                    } else {
                        selectedIndex = 0; // Cycle to first item
                    }
                    break;
                case 'ArrowUp':
                    e.preventDefault();
                    if (selectedIndex > 0) {
                        selectedIndex--;
                    } else {
                        selectedIndex = items.length - 1; // Cycle to last item
                    }
                    break;
                case 'Enter':
                    e.preventDefault();
                    if (selectedItem) {
                        executeCommand(selectedItem.dataset.id);
                    }
                    break;
                case 'Escape':
                    e.preventDefault();
                    toggleCommandPalette(false);
                    break;
            }

            // Update selected state
            items.forEach((item, idx) => {
                item.setAttribute('aria-selected', idx === selectedIndex ? 'true' : 'false');
                if (idx === selectedIndex) {
                    item.focus();
                }
            });
        });
    }

    // Close button handler
    const closeBtn = document.querySelector('.close-command');
    if (closeBtn) {
        closeBtn.addEventListener('click', () => {
            toggleCommandPalette(false);
        });
    }

    // Render initial commands
    renderCommands();
}

// Toggle command palette visibility
function toggleCommandPalette(show = null) {
    const palette = document.getElementById('command-palette');
    const input = document.getElementById('command-input');

    if (!palette) return;

    const isHidden = palette.classList.contains('hidden');
    const shouldShow = show !== null ? show : isHidden;

    if (shouldShow) {
        palette.classList.remove('hidden');
        if (input) {
            input.value = '';
            setTimeout(() => input.focus(), 10);
            renderCommands();
        }
    } else {
        palette.classList.add('hidden');
    }
}

// Create ripple effect for buttons
function createRipple(event) {
    const button = event.currentTarget;
    const circle = document.createElement('span');
    const diameter = Math.max(button.clientWidth, button.clientHeight);
    const radius = diameter / 2;

    // Position the ripple
    circle.style.width = circle.style.height = `${diameter}px`;
    circle.style.left = `${event.clientX - button.getBoundingClientRect().left - radius}px`;
    circle.style.top = `${event.clientY - button.getBoundingClientRect().top - radius}px`;
    circle.classList.add('ripple');

    // Clean up existing ripples
    const ripple = button.querySelector('.ripple');
    if (ripple) {
        ripple.remove();
    }

    // Add the new ripple
    button.appendChild(circle);
}

// Apply ripple effect to all buttons
function initRippleEffect() {
    const buttons = document.querySelectorAll('.btn, .provider-tab, .command-item');
    buttons.forEach(button => {
        button.addEventListener('click', createRipple);
    });
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    initMessageAnimations();
    initMessageScroll();
    highlightCode();
    initKeyboardNavigation();
    initCommandPalette();
    initRippleEffect();
});