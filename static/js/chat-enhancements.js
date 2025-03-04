/**
 * Chat UI enhancements for TQ GenAI Chat
 * Provides formatting, code highlighting, and other improvements
 */

class ChatEnhancer {
    constructor() {
        this.messageFormatters = [];
        this.codeLanguages = {
            'js': 'javascript',
            'ts': 'typescript',
            'py': 'python',
            'rb': 'ruby',
            'java': 'java',
            'go': 'go',
            'php': 'php',
            'cs': 'csharp',
            'html': 'html',
            'css': 'css',
            'json': 'json',
            'md': 'markdown',
            'sql': 'sql',
            'sh': 'bash',
            'bash': 'bash',
            'yaml': 'yaml',
            'xml': 'xml'
        };

        this.initFormatters();
        this.attachEventListeners();
    }

    initFormatters() {
        // Add formatters in order of processing

        // Code block formatting
        this.messageFormatters.push((message) => {
            message = this.formatCodeBlocks(message);
            return message;
        });

        // Math expressions with KaTeX if available
        this.messageFormatters.push((message) => {
            return this.formatMathExpressions(message);
        });

        // Tables
        this.messageFormatters.push((message) => {
            return this.formatTables(message);
        });

        // Links
        this.messageFormatters.push((message) => {
            return this.formatLinks(message);
        });

        // Citations
        this.messageFormatters.push((message) => {
            return this.formatCitations(message);
        });
    }

    attachEventListeners() {
        // Listen for messages being added to DOM
        document.addEventListener('message-added', (e) => {
            if (e.detail && e.detail.element) {
                this.enhanceMessage(e.detail.element);
            }
        });

        // Process existing messages on init
        document.querySelectorAll('.message-bubble .message-text').forEach(messageEl => {
            this.enhanceMessage(messageEl);
        });
    }

    /**
     * Apply all formatters to a message
     */
    formatMessage(message) {
        if (!message) return '';

        // Apply each formatter in sequence
        let formattedMessage = message;
        for (const formatter of this.messageFormatters) {
            formattedMessage = formatter(formattedMessage);
        }

        return formattedMessage;
    }

    /**
     * Format code blocks in message
     */
    formatCodeBlocks(message) {
        // Replace multiline code blocks with proper syntax highlighting
        let formattedMessage = message.replace(/```([a-zA-Z]*)\n([\s\S]*?)```/g, (match, language, code) => {
            const lang = language.toLowerCase();
            const languageClass = this.codeLanguages[lang] || lang || 'plaintext';
            const escapedCode = this.escapeHtml(code);

            return `<pre><code class="language-${languageClass}">${escapedCode}</code></pre>`;
        });

        // Replace inline code
        formattedMessage = formattedMessage.replace(/`([^`]+)`/g, '<code>$1</code>');

        return formattedMessage;
    }

    /**
     * Format math expressions if KaTeX is available
     */
    formatMathExpressions(message) {
        // Check if KaTeX is available
        if (typeof katex === 'undefined') {
            return message;
        }

        // Replace display math: $$...$$
        let formattedMessage = message.replace(/\$\$([\s\S]*?)\$\$/g, (match, expr) => {
            try {
                return `<div class="math math-display">${katex.renderToString(expr, { displayMode: true })}</div>`;
            } catch (e) {
                console.error('KaTeX rendering error:', e);
                return match; // Return original on error
            }
        });

        // Replace inline math: $...$
        formattedMessage = formattedMessage.replace(/(?<!\$)\$(?!\$)(.*?)(?<!\$)\$(?!\$)/g, (match, expr) => {
            try {
                return `<span class="math math-inline">${katex.renderToString(expr)}</span>`;
            } catch (e) {
                console.error('KaTeX rendering error:', e);
                return match; // Return original on error
            }
        });

        return formattedMessage;
    }

    /**
     * Format markdown-style tables
     */
    formatTables(message) {
        // Find table blocks: | header | header | ... followed by | --- | --- | ...
        const tableRegex = /\|(.+)\|\n\|([\s-:]+)\|\n((?:\|.+\|\n?)+)/g;

        return message.replace(tableRegex, (match, headerRow, separatorRow, bodyRows) => {
            // Process header
            const headers = headerRow.split('|')
                .map(cell => cell.trim())
                .filter(cell => cell !== '');

            // Process separator to get alignment
            const separators = separatorRow.split('|')
                .map(cell => cell.trim())
                .filter(cell => cell !== '');

            const alignments = separators.map(sep => {
                if (sep.startsWith(':') && sep.endsWith(':')) return 'center';
                if (sep.endsWith(':')) return 'right';
                return 'left';
            });

            // Process body rows
            const rows = bodyRows.trim().split('\n').map(row => {
                return row.split('|')
                    .map(cell => cell.trim())
                    .filter(cell => cell !== '');
            });

            // Build HTML table
            let tableHtml = '<div class="table-responsive"><table class="modern-table">';

            // Add header row
            tableHtml += '<thead><tr>';
            headers.forEach((header, i) => {
                const align = alignments[i] || 'left';
                tableHtml += `<th style="text-align: ${align};">${header}</th>`;
            });
            tableHtml += '</tr></thead>';

            // Add body rows
            tableHtml += '<tbody>';
            rows.forEach(row => {
                tableHtml += '<tr>';
                row.forEach((cell, i) => {
                    const align = alignments[i] || 'left';
                    tableHtml += `<td style="text-align: ${align};">${cell}</td>`;
                });
                tableHtml += '</tr>';
            });
            tableHtml += '</tbody></table></div>';

            return tableHtml;
        });
    }

    /**
     * Format hyperlinks
     */
    formatLinks(message) {
        // Markdown-style links: [text](url)
        let formattedMessage = message.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>');

        // Detect URLs that are not already part of an HTML link
        const urlRegex = /(?<!['"])(?:https?:\/\/|www\.)[^\s<>]+/g;
        formattedMessage = formattedMessage.replace(urlRegex, url => {
            // Skip if already in a link
            if (url.match(/<a [^>]*>/)) return url;

            // Make sure URL starts with http:// or https://
            const href = url.startsWith('www.') ? `https://${url}` : url;

            return `<a href="${href}" target="_blank" rel="noopener noreferrer">${url}</a>`;
        });

        return formattedMessage;
    }

    /**
     * Format citations from sources
     */
    formatCitations(message) {
        // Format source citations: > Source: [filename] (relevance: XX%)
        return message.replace(/&gt; Source: \[([^\]]+)\] \(relevance: ([^)]+)\)/g, (match, filename, relevance) => {
            return `<div class="citation">
                <div class="citation-title">
                    <i class="fas fa-file-alt"></i> Source: ${filename}
                </div>
                <div class="citation-meta">Relevance: ${relevance}</div>
            </div>`;
        });
    }

    /**
     * Enhance a message element after it's added to the DOM
     */
    enhanceMessage(messageEl) {
        // Apply code highlighting if available
        this.highlightCode(messageEl);

        // Add class for special content
        if (messageEl.querySelector('pre code')) {
            messageEl.closest('.message-bubble').classList.add('has-code');
        }

        if (messageEl.querySelector('.math')) {
            messageEl.closest('.message-bubble').classList.add('has-math');
        }

        // Make long code blocks collapsible
        this.makeCodeBlocksCollapsible(messageEl);

        // Add copy buttons to code blocks
        this.addCodeBlockCopyButtons(messageEl);
    }

    /**
     * Add syntax highlighting to code blocks
     */
    highlightCode(messageEl) {
        // Check if highlight.js is available
        if (window.hljs) {
            messageEl.querySelectorAll('pre code').forEach(block => {
                hljs.highlightBlock(block);
            });
            return;
        }

        // Simple fallback highlighting
        messageEl.querySelectorAll('pre code').forEach(block => {
            // Skip if already highlighted
            if (block.classList.contains('highlighted')) return;

            // Language-specific keywords
            const languages = {
                'javascript': ['function', 'const', 'let', 'var', 'return', 'if', 'else', 'for', 'while', 'class', 'import', 'export', 'async', 'await'],
                'python': ['def', 'class', 'import', 'from', 'return', 'if', 'else', 'for', 'while', 'try', 'except', 'with', 'as', 'lambda'],
                'html': ['html', 'head', 'body', 'div', 'span', 'p', 'a', 'img', 'script', 'style', 'link']
            };

            // Get language from class
            let lang = 'plaintext';
            Array.from(block.classList).forEach(cls => {
                if (cls.startsWith('language-')) {
                    lang = cls.replace('language-', '');
                }
            });

            // Apply simple highlighting
            let html = block.innerHTML;

            // Highlight strings
            html = html.replace(/"([^"]*)"/g, '<span class="hljs-string">"$1"</span>');
            html = html.replace(/'([^']*)'/g, '<span class="hljs-string">\'$1\'</span>');

            // Highlight numbers
            html = html.replace(/\b(\d+)\b/g, '<span class="hljs-number">$1</span>');

            // Highlight comments
            html = html.replace(/(\/\/[^\n]*)/g, '<span class="hljs-comment">$1</span>');
            html = html.replace(/(#[^\n]*)/g, '<span class="hljs-comment">$1</span>');

            // Highlight language-specific keywords
            const keywords = languages[lang] || [];
            keywords.forEach(word => {
                const regex = new RegExp(`\\b${word}\\b`, 'g');
                html = html.replace(regex, `<span class="hljs-keyword">${word}</span>`);
            });

            block.innerHTML = html;
            block.classList.add('highlighted');
        });
    }

    /**
     * Make long code blocks collapsible
     */
    makeCodeBlocksCollapsible(messageEl) {
        messageEl.querySelectorAll('pre').forEach(pre => {
            const code = pre.querySelector('code');
            if (!code) return;

            // Count lines
            const lineCount = (code.textContent.match(/\n/g) || []).length + 1;

            // If more than 15 lines, make collapsible
            if (lineCount > 15) {
                pre.classList.add('collapsible-code');

                // Create collapse UI
                const collapseUI = document.createElement('div');
                collapseUI.className = 'code-collapse-ui';

                const toggleButton = document.createElement('button');
                toggleButton.className = 'code-collapse-toggle';
                toggleButton.innerHTML = `<span class="expand">Show all ${lineCount} lines</span><span class="collapse">Show less</span>`;
                collapseUI.appendChild(toggleButton);

                // Add line count
                const lineCountEl = document.createElement('div');
                lineCountEl.className = 'code-line-count';
                lineCountEl.textContent = `${lineCount} lines`;
                collapseUI.appendChild(lineCountEl);

                // Insert before pre
                pre.parentNode.insertBefore(collapseUI, pre);

                // Add toggle behavior
                toggleButton.addEventListener('click', () => {
                    pre.classList.toggle('expanded');
                    toggleButton.classList.toggle('expanded');
                });

                // Start collapsed
                pre.style.maxHeight = '300px';
            }
        });
    }

    /**
     * Add copy buttons to code blocks
     */
    addCodeBlockCopyButtons(messageEl) {
        messageEl.querySelectorAll('pre').forEach(pre => {
            const code = pre.querySelector('code');
            if (!code) return;

            // Skip if already has copy button
            if (pre.querySelector('.code-copy-btn')) return;

            // Create copy button
            const copyBtn = document.createElement('button');
            copyBtn.className = 'code-copy-btn';
            copyBtn.innerHTML = '<i class="fas fa-copy"></i>';
            copyBtn.setAttribute('title', 'Copy to clipboard');
            copyBtn.setAttribute('aria-label', 'Copy code to clipboard');

            // Add to pre element
            pre.appendChild(copyBtn);

            // Add click handler
            copyBtn.addEventListener('click', () => {
                const textToCopy = code.textContent;

                // Copy to clipboard
                navigator.clipboard.writeText(textToCopy).then(() => {
                    // Show success state
                    copyBtn.innerHTML = '<i class="fas fa-check"></i>';
                    copyBtn.classList.add('copied');

                    // Reset after delay
                    setTimeout(() => {
                        copyBtn.innerHTML = '<i class="fas fa-copy"></i>';
                        copyBtn.classList.remove('copied');
                    }, 2000);
                }).catch(err => {
                    console.error('Failed to copy code:', err);
                });
            });
        });
    }

    /**
     * Escape HTML special characters
     */
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// Initialize chat enhancer on page load
document.addEventListener('DOMContentLoaded', () => {
    window.chatEnhancer = new ChatEnhancer();
});