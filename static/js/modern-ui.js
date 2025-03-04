/**
 * Modern UI interactions for TQ GenAI Chat
 * Enhances the UI with modern interactions and animations
 */

// Initialize when document is loaded
document.addEventListener('DOMContentLoaded', function () {
    console.log('Modern UI initializing...');
    initializeUI();
    setupThemeToggle();
    setupCopyCodeButtons();
    setupTooltips();
    setupModals();
    setupHighlighting();
    setupDropdowns();
    initializeCommandPalette();
});

/**
 * Initialize base UI components
 */
function initializeUI() {
    // Auto-resize textarea on input
    const chatInput = document.getElementById('chat-input');
    if (chatInput) {
        chatInput.addEventListener('input', function () {
            this.style.height = 'auto';
            this.style.height = (this.scrollHeight) + 'px';
        });

        // Initial sizing
        chatInput.style.height = 'auto';
        chatInput.style.height = (chatInput.scrollHeight) + 'px';
    }

    // Add timestamp to messages
    document.querySelectorAll('.message').forEach(function (message) {
        if (!message.querySelector('.message-time')) {
            const timeEl = document.createElement('div');
            timeEl.className = 'message-time';
            timeEl.textContent = new Date().toLocaleTimeString();
            message.querySelector('.message-bubble').appendChild(timeEl);
        }
    });

    // Add scroll shadow to message container
    const msgContainer = document.getElementById('chat-messages');
    if (msgContainer) {
        msgContainer.addEventListener('scroll', function () {
            const hasScrollShadow = this.scrollTop > 0;
            this.classList.toggle('has-shadow', hasScrollShadow);
        });

        // Initial check
        msgContainer.dispatchEvent(new Event('scroll'));
    }
}

/**
 * Setup theme toggle functionality
 */
function setupThemeToggle() {
    const themeToggle = document.getElementById('theme-toggle-input');

    // Set initial theme based on preference
    const prefersDarkMode = window.matchMedia('(prefers-color-scheme: dark)').matches;
    const savedTheme = localStorage.getItem('theme');

    // Apply the saved theme or system preference
    if (savedTheme === 'dark' || (savedTheme !== 'light' && prefersDarkMode)) {
        document.body.classList.add('dark-theme');
        if (themeToggle) themeToggle.checked = true;
    }

    // Handle theme toggle
    if (themeToggle) {
        themeToggle.addEventListener('change', function () {
            document.body.classList.toggle('dark-theme', this.checked);
            localStorage.setItem('theme', this.checked ? 'dark' : 'light');

            // Dispatch theme change event
            window.dispatchEvent(new CustomEvent('themechange', {
                detail: { theme: this.checked ? 'dark' : 'light' }
            }));
        });
    }

    // Listen for system preference changes
    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', function (e) {
        if (localStorage.getItem('theme') === null) {
            document.body.classList.toggle('dark-theme', e.matches);
            if (themeToggle) themeToggle.checked = e.matches;
        }
    });
}

/**
 * Setup code copy buttons
 */
function setupCopyCodeButtons() {
    document.querySelectorAll('pre code').forEach(function (codeBlock) {
        if (!codeBlock.parentNode.querySelector('.copy-btn')) {
            const copyBtn = document.createElement('button');
            copyBtn.className = 'copy-btn';
            copyBtn.innerHTML = '<i class="fas fa-copy"></i>';
            copyBtn.title = 'Copy to clipboard';

            copyBtn.addEventListener('click', function () {
                const codeToCopy = codeBlock.textContent;

                // Copy to clipboard
                navigator.clipboard.writeText(codeToCopy).then(function () {
                    copyBtn.innerHTML = '<i class="fas fa-check"></i>';
                    copyBtn.classList.add('copied');

                    // Reset after 2 seconds
                    setTimeout(function () {
                        copyBtn.innerHTML = '<i class="fas fa-copy"></i>';
                        copyBtn.classList.remove('copied');
                    }, 2000);
                });
            });

            codeBlock.parentNode.appendChild(copyBtn);
        }
    });
}

/**
 * Setup tooltips for elements
 */
function setupTooltips() {
    document.querySelectorAll('[data-tooltip]').forEach(function (element) {
        const tooltipText = element.getAttribute('data-tooltip');

        element.addEventListener('mouseenter', function (e) {
            // Create tooltip element if it doesn't exist
            let tooltip = document.getElementById('tooltip');
            if (!tooltip) {
                tooltip = document.createElement('div');
                tooltip.id = 'tooltip';
                tooltip.className = 'tooltip';
                document.body.appendChild(tooltip);
            }

            // Position tooltip and show it
            tooltip.textContent = tooltipText;
            tooltip.style.top = (e.target.getBoundingClientRect().top - tooltip.offsetHeight - 10) + 'px';
            tooltip.style.left = (e.target.getBoundingClientRect().left + e.target.offsetWidth / 2 - tooltip.offsetWidth / 2) + 'px';
            tooltip.classList.add('visible');
        });

        element.addEventListener('mouseleave', function () {
            const tooltip = document.getElementById('tooltip');
            if (tooltip) tooltip.classList.remove('visible');
        });
    });
}

/**
 * Setup modal functionality
 */
function setupModals() {
    // Modal triggers
    document.querySelectorAll('[data-modal-target]').forEach(function (trigger) {
        trigger.addEventListener('click', function () {
            const targetId = this.getAttribute('data-modal-target');
            const modal = document.getElementById(targetId);

            if (modal) {
                modal.classList.add('open');

                // Find and focus first focusable element
                const focusable = modal.querySelectorAll('button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])');
                if (focusable.length) focusable[0].focus();

                // Trap focus in the modal
                modal.addEventListener('keydown', trapFocus);
            }
        });
    });

    // Close modal buttons
    document.querySelectorAll('.close-modal, [data-modal-close]').forEach(function (closeButton) {
        closeButton.addEventListener('click', function () {
            const modal = this.closest('.modal');
            if (modal) {
                modal.classList.remove('open');
                modal.removeEventListener('keydown', trapFocus);
            }
        });
    });

    // Close modal when clicking on backdrop
    document.querySelectorAll('.modal').forEach(function (modal) {
        modal.addEventListener('click', function (e) {
            // Only close if clicking the backdrop (modal itself), not its children
            if (e.target === modal) {
                modal.classList.remove('open');
                modal.removeEventListener('keydown', trapFocus);
            }
        });
    });

    // Helper for trapping focus in modals
    function trapFocus(e) {
        if (e.key !== 'Tab') return;

        const modal = e.currentTarget;
        const focusable = Array.from(
            modal.querySelectorAll('button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])')
        ).filter(element => element.offsetWidth > 0 && element.offsetHeight > 0);

        const firstFocusable = focusable[0];
        const lastFocusable = focusable[focusable.length - 1];

        // Shift+Tab on first element should focus last element
        if (e.shiftKey && document.activeElement === firstFocusable) {
            e.preventDefault();
            lastFocusable.focus();
        }

        // Tab on last element should focus first element
        else if (!e.shiftKey && document.activeElement === lastFocusable) {
            e.preventDefault();
            firstFocusable.focus();
        }
    }
}

/**
 * Setup syntax highlighting
 */
function setupHighlighting() {
    // If highlight.js is loaded
    if (window.hljs) {
        document.querySelectorAll('pre code').forEach(function (block) {
            hljs.highlightBlock(block);
        });
    } else {
        // Simple syntax highlight for code blocks
        document.querySelectorAll('pre code').forEach(function (block) {
            // Skip if already highlighted
            if (block.classList.contains('highlighted')) return;

            // Apply simple highlighting based on language
            const language = Array.from(block.classList)
                .find(cls => cls.startsWith('language-'))?.replace('language-', '') || '';

            // Add class for styling
            block.parentNode.classList.add('code-block');
            block.classList.add('highlighted');

            // Add language label if available
            if (language && !block.parentNode.querySelector('.code-language')) {
                const langLabel = document.createElement('div');
                langLabel.className = 'code-language';
                langLabel.textContent = language;
                block.parentNode.appendChild(langLabel);
            }

            // Apply basic syntax highlighting for common tokens
            let html = block.innerHTML;

            // Highlight strings
            html = html.replace(/"([^"]*)"/g, '<span class="string">"$1"</span>');
            html = html.replace(/'([^']*)'/g, '<span class="string">\'$1\'</span>');

            // Highlight numbers
            html = html.replace(/\b(\d+)\b/g, '<span class="number">$1</span>');

            // Highlight comments
            html = html.replace(/(\/\/[^\n]*)/g, '<span class="comment">$1</span>');
            html = html.replace(/(#[^\n]*)/g, '<span class="comment">$1</span>');

            // Highlight keywords based on language
            if (language === 'javascript' || language === 'js') {
                const keywords = ['function', 'return', 'if', 'else', 'for', 'while', 'let', 'const', 'var', 'class', 'new', 'this', 'import', 'export'];
                keywords.forEach(function (keyword) {
                    const regex = new RegExp(`\\b${keyword}\\b`, 'g');
                    html = html.replace(regex, `<span class="keyword">${keyword}</span>`);
                });
            } else if (language === 'python' || language === 'py') {
                const keywords = ['def', 'class', 'import', 'from', 'return', 'if', 'else', 'for', 'while', 'in', 'as', 'with', 'try', 'except', 'finally'];
                keywords.forEach(function (keyword) {
                    const regex = new RegExp(`\\b${keyword}\\b`, 'g');
                    html = html.replace(regex, `<span class="keyword">${keyword}</span>`);
                });
            }

            block.innerHTML = html;
        });
    }
}

/**
 * Setup dropdown menus
 */
function setupDropdowns() {
    document.querySelectorAll('.dropdown-toggle').forEach(function (toggle) {
        toggle.addEventListener('click', function (e) {
            e.preventDefault();
            e.stopPropagation();

            const dropdown = this.nextElementSibling;
            if (!dropdown || !dropdown.classList.contains('dropdown-menu')) return;

            // Close all other dropdowns
            document.querySelectorAll('.dropdown-menu.open').forEach(function (menu) {
                if (menu !== dropdown) menu.classList.remove('open');
            });

            // Toggle this dropdown
            dropdown.classList.toggle('open');

            // Add click outside handler
            if (dropdown.classList.contains('open')) {
                document.addEventListener('click', closeDropdownsOnClickOutside);
            }
        });
    });

    function closeDropdownsOnClickOutside(e) {
        if (!e.target.closest('.dropdown-menu') && !e.target.closest('.dropdown-toggle')) {
            document.querySelectorAll('.dropdown-menu.open').forEach(function (menu) {
                menu.classList.remove('open');
            });
            document.removeEventListener('click', closeDropdownsOnClickOutside);
        }
    }
}

/**
 * Initialize command palette
 */
function initializeCommandPalette() {
    // Create command palette if it doesn't exist yet
    if (!document.getElementById('command-palette')) {
        const palette = document.createElement('div');
        palette.id = 'command-palette';
        palette.className = 'command-palette hidden';

        palette.innerHTML = `
            <div class="command-header">
                <div class="command-search">
                    <i class="fas fa-search"></i>
                    <input id="command-input" type="text" placeholder="Search commands...">
                </div>
                <button class="close-command" id="close-command">&times;</button>
            </div>
            <div class="command-results">
                <div id="command-groups"></div>
            </div>
            <div class="command-footer">
                <div class="command-help">
                    <span>↑↓ to navigate</span>
                    <span>↵ to select</span>
                    <span>esc to close</span>
                </div>
            </div>
        `;

        document.body.appendChild(palette);

        // Set up event handlers for the command palette
        const commandInput = document.getElementById('command-input');
        // Fix here: Don't redeclare closeBtn, use a different variable name
        const closeCommandButton = document.getElementById('close-command');

        // Define commands
        const commands = [
            {
                name: 'Toggle Dark Mode',
                description: 'Switch between light and dark theme',
                group: 'Appearance',
                action: () => {
                    const themeToggle = document.getElementById('theme-toggle-input');
                    if (themeToggle) {
                        themeToggle.checked = !themeToggle.checked;
                        themeToggle.dispatchEvent(new Event('change'));
                    }
                    hideCommandPalette();
                }
            },
            {
                name: 'Clear Chat',
                description: 'Clear all messages in the current chat',
                group: 'Chat',
                action: () => {
                    const clearBtn = document.getElementById('clear-chat-btn');
                    if (clearBtn) clearBtn.click();
                    hideCommandPalette();
                }
            },
            {
                name: 'Save Chat',
                description: 'Save the current chat to your history',
                group: 'Chat',
                action: () => {
                    const saveBtn = document.getElementById('save-chat');
                    if (saveBtn) saveBtn.click();
                    hideCommandPalette();
                }
            },
            {
                name: 'Export Chat',
                description: 'Export the current chat as markdown',
                group: 'Chat',
                action: () => {
                    const exportBtn = document.getElementById('export-chat');
                    if (exportBtn) exportBtn.click();
                    hideCommandPalette();
                }
            }
        ];

        let selectedCommandIndex = -1;

        // Group commands by category
        function renderCommandGroups(filterText = '') {
            const commandGroupsEl = document.getElementById('command-groups');

            // Group by category
            const groups = {};

            // Filter and group commands
            commands.forEach(cmd => {
                if (!filterText || cmd.name.toLowerCase().includes(filterText.toLowerCase())) {
                    if (!groups[cmd.group]) {
                        groups[cmd.group] = [];
                    }
                    groups[cmd.group].push(cmd);
                }
            });

            // Clear previous results
            commandGroupsEl.innerHTML = '';

            // If no results
            if (Object.keys(groups).length === 0) {
                commandGroupsEl.innerHTML = '<div class="command-empty">No commands found</div>';
                return;
            }

            // Reset selected index
            selectedCommandIndex = -1;

            // Render each group
            Object.keys(groups).sort().forEach(groupName => {
                const groupEl = document.createElement('div');
                groupEl.className = 'command-group';

                const titleEl = document.createElement('div');
                titleEl.className = 'command-group-title';
                titleEl.textContent = groupName;
                groupEl.appendChild(titleEl);

                const listEl = document.createElement('div');
                listEl.className = 'command-list';

                groups[groupName].forEach(cmd => {
                    const itemEl = document.createElement('div');
                    itemEl.className = 'command-item';
                    itemEl.setAttribute('role', 'option');
                    itemEl.dataset.action = commands.indexOf(cmd);
                    itemEl.tabIndex = 0;

                    itemEl.innerHTML = `
                        <div class="command-icon">
                            <i class="fas fa-bolt"></i>
                        </div>
                        <div class="command-name">${cmd.name}</div>
                    `;

                    itemEl.addEventListener('click', () => {
                        cmd.action();
                    });

                    listEl.appendChild(itemEl);
                });

                groupEl.appendChild(listEl);
                commandGroupsEl.appendChild(groupEl);
            });
        }

        // Show command palette
        function showCommandPalette() {
            const commandPalette = document.getElementById('command-palette');
            commandPalette.classList.remove('hidden');

            // Focus search input
            setTimeout(() => {
                const commandInput = document.getElementById('command-input');
                if (commandInput) {
                    commandInput.focus();
                    renderCommandGroups();
                }
            }, 10);
        }

        // Hide command palette
        function hideCommandPalette() {
            const commandPalette = document.getElementById('command-palette');
            commandPalette.classList.add('hidden');

            // Clear search
            const commandInput = document.getElementById('command-input');
            if (commandInput) {
                commandInput.value = '';
            }
        }

        // Command input listener
        if (commandInput) {
            commandInput.addEventListener('input', () => {
                renderCommandGroups(commandInput.value);
            });

            // Handle keyboard navigation
            commandInput.addEventListener('keydown', (e) => {
                const commands = document.querySelectorAll('.command-item');

                if (e.key === 'ArrowDown') {
                    e.preventDefault();
                    selectedCommandIndex = Math.min(selectedCommandIndex + 1, commands.length - 1);
                    updateSelectedCommand();
                } else if (e.key === 'ArrowUp') {
                    e.preventDefault();
                    selectedCommandIndex = Math.max(selectedCommandIndex - 1, -1);
                    updateSelectedCommand();
                } else if (e.key === 'Enter' && selectedCommandIndex >= 0) {
                    e.preventDefault();
                    const selectedCommand = commands[selectedCommandIndex];
                    if (selectedCommand) {
                        const actionIndex = selectedCommand.dataset.action;
                        if (actionIndex && commands[actionIndex]) {
                            commands[actionIndex].action();
                        }
                    }
                } else if (e.key === 'Escape') {
                    e.preventDefault();
                    hideCommandPalette();
                }
            });
        }

        function updateSelectedCommand() {
            const commands = document.querySelectorAll('.command-item');

            // Remove selected from all
            commands.forEach((item, i) => {
                item.setAttribute('aria-selected', i === selectedCommandIndex ? 'true' : 'false');
            });

            // Scroll selected into view
            if (selectedCommandIndex >= 0 && commands[selectedCommandIndex]) {
                commands[selectedCommandIndex].scrollIntoView({
                    block: 'nearest'
                });
            }
        }

        // Close button listener
        if (closeCommandButton) {
            closeCommandButton.addEventListener('click', hideCommandPalette);
        }

        // Keyboard shortcut for command palette
        document.addEventListener('keydown', (e) => {
            if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
                e.preventDefault();
                showCommandPalette();
            }
        });

        // Make functions available on window
        window.commandPalette = {
            show: showCommandPalette,
            hide: hideCommandPalette
        };
    }
}

// Add any additional functions from modern-ui.js if needed
// ...