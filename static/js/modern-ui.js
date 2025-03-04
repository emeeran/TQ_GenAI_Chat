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

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    initMessageAnimations();
    initMessageScroll();
    highlightCode();
});