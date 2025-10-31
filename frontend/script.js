// TQ GenAI Chat - Frontend JavaScript

class TQGenAIChat {
    constructor() {
        this.apiBase = 'http://127.0.0.1:5005';
        this.auth = {
            username: 'emeeran',
            password: '3u0qL1lizU19WE'
        };

        this.currentProvider = null;
        this.currentModel = null;
        this.isConnected = false;
        this.chatHistory = [];

        this.initElements();
        this.initEventListeners();
        this.checkConnection();
    }

    initElements() {
        // Connection status
        this.connectionStatus = document.getElementById('connectionStatus');

        // Provider controls
        this.providerSelect = document.getElementById('providerSelect');
        this.modelInfo = document.getElementById('modelInfo');
        this.modelDetails = document.getElementById('modelDetails');
        this.settingsToggle = document.getElementById('settingsToggle');
        this.advancedSettings = document.getElementById('advancedSettings');

        // Advanced settings
        this.temperatureSlider = document.getElementById('temperature');
        this.tempValue = document.getElementById('tempValue');
        this.maxTokensInput = document.getElementById('maxTokens');

        // Chat elements
        this.chatMessages = document.getElementById('chatMessages');
        this.messageInput = document.getElementById('messageInput');
        this.sendButton = document.getElementById('sendButton');
        this.clearChatBtn = document.getElementById('clearChat');
        this.charCount = document.getElementById('charCount');

        // UI elements
        this.loadingOverlay = document.getElementById('loadingOverlay');
        this.errorModal = document.getElementById('errorModal');
        this.errorMessage = document.getElementById('errorMessage');
        this.modalClose = document.getElementById('modalClose');
        this.modalOK = document.getElementById('modalOK');
    }

    initEventListeners() {
        // Provider selection
        this.providerSelect.addEventListener('change', () => this.handleProviderChange());

        // Settings toggle
        this.settingsToggle.addEventListener('click', () => this.toggleAdvancedSettings());

        // Advanced settings
        this.temperatureSlider.addEventListener('input', (e) => {
            this.tempValue.textContent = e.target.value;
        });

        // Message input
        this.messageInput.addEventListener('input', () => this.updateCharCount());
        this.messageInput.addEventListener('keydown', (e) => this.handleKeyDown(e));

        // Send button
        this.sendButton.addEventListener('click', () => this.sendMessage());

        // Clear chat
        this.clearChatBtn.addEventListener('click', () => this.clearChat());

        // Modal controls
        this.modalClose.addEventListener('click', () => this.hideError());
        this.modalOK.addEventListener('click', () => this.hideError());
        this.errorModal.addEventListener('click', (e) => {
            if (e.target === this.errorModal) this.hideError();
        });

        // Auto-resize textarea
        this.messageInput.addEventListener('input', () => this.autoResizeTextarea());
    }

    async checkConnection() {
        try {
            const response = await this.apiCall('/health');
            this.updateConnectionStatus(true);
        } catch (error) {
            this.updateConnectionStatus(false);
        }
    }

    updateConnectionStatus(connected) {
        this.isConnected = connected;
        const statusElement = this.connectionStatus;
        const icon = statusElement.querySelector('i');

        if (connected) {
            statusElement.className = 'status connected';
            statusElement.innerHTML = '<i class="fas fa-circle"></i> Connected';
        } else {
            statusElement.className = 'status disconnected';
            statusElement.innerHTML = '<i class="fas fa-circle"></i> Disconnected';
        }
    }

    handleProviderChange() {
        const selectedOption = this.providerSelect.options[this.providerSelect.selectedIndex];
        this.currentProvider = this.providerSelect.value;
        this.currentModel = selectedOption.dataset?.model || null;

        if (this.currentProvider && this.currentModel) {
            // Show model info
            this.modelInfo.style.display = 'flex';
            const providerName = selectedOption.text.split('(')[0].trim();
            this.modelDetails.textContent = `${providerName} - ${this.currentModel}`;

            // Enable input
            this.messageInput.disabled = false;
            this.sendButton.disabled = false;

            // Remove welcome message if it exists
            this.removeWelcomeMessage();
        } else {
            // Hide model info
            this.modelInfo.style.display = 'none';

            // Disable input
            this.messageInput.disabled = true;
            this.sendButton.disabled = true;
        }
    }

    toggleAdvancedSettings() {
        const isVisible = this.advancedSettings.style.display !== 'none';
        this.advancedSettings.style.display = isVisible ? 'none' : 'block';

        const icon = this.settingsToggle.querySelector('i');
        icon.className = isVisible ? 'fas fa-cog' : 'fas fa-times';
    }

    updateCharCount() {
        const length = this.messageInput.value.length;
        this.charCount.textContent = length;
    }

    autoResizeTextarea() {
        this.messageInput.style.height = 'auto';
        this.messageInput.style.height = Math.min(this.messageInput.scrollHeight, 120) + 'px';
    }

    handleKeyDown(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            this.sendMessage();
        }
    }

    async sendMessage() {
        const message = this.messageInput.value.trim();
        if (!message || !this.currentProvider || !this.currentModel) return;

        // Add user message to chat
        this.addMessage('user', message);

        // Clear input
        this.messageInput.value = '';
        this.updateCharCount();
        this.autoResizeTextarea();

        // Show loading
        this.showLoading();

        try {
            // Prepare request
            const requestData = {
                provider: this.currentProvider,
                model: this.currentModel,
                message: message,
                temperature: parseFloat(this.temperatureSlider.value),
                max_tokens: parseInt(this.maxTokensInput.value),
                output_language: 'en'
            };

            // Make API call
            const response = await this.apiCall('/chat', {
                method: 'POST',
                body: JSON.stringify(requestData)
            });

            // Add AI response to chat
            if (response.response && response.response.text) {
                this.addMessage('assistant', response.response.text, response.response.metadata);
            } else {
                throw new Error('Invalid response format from server');
            }

        } catch (error) {
            console.error('API Error:', error);
            this.showError(`Failed to get response: ${error.message}`);

            // Add error message to chat
            this.addMessage('assistant', `Error: ${error.message}`, null, true);
        } finally {
            this.hideLoading();
        }
    }

    addMessage(role, content, metadata = null, isError = false) {
        // Remove welcome message if this is the first message
        if (this.chatHistory.length === 0) {
            this.removeWelcomeMessage();
        }

        const message = {
            role,
            content,
            metadata,
            timestamp: new Date(),
            isError
        };

        this.chatHistory.push(message);
        this.renderMessage(message);
        this.scrollToBottom();
    }

    renderMessage(message) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${message.role}`;

        // Avatar
        const avatar = document.createElement('div');
        avatar.className = 'message-avatar';
        avatar.innerHTML = message.role === 'user' ?
            '<i class="fas fa-user"></i>' :
            '<i class="fas fa-robot"></i>';

        // Content container
        const contentContainer = document.createElement('div');
        contentContainer.className = 'message-content';

        // Message bubble
        const bubble = document.createElement('div');
        bubble.className = 'message-bubble';
        if (message.isError) {
            bubble.style.backgroundColor = '#fef2f2';
            bubble.style.color = '#dc2626';
            bubble.style.borderColor = '#fecaca';
        }
        bubble.textContent = message.content;

        // Message info
        const info = document.createElement('div');
        info.className = 'message-info';

        if (message.role === 'assistant' && message.metadata) {
            // Provider badge
            if (message.metadata.provider) {
                const providerBadge = document.createElement('span');
                providerBadge.className = 'provider-badge';
                providerBadge.textContent = message.metadata.provider.toUpperCase();
                info.appendChild(providerBadge);
            }

            // Response time
            if (message.metadata.response_time) {
                const timeSpan = document.createElement('span');
                timeSpan.textContent = message.metadata.response_time;
                info.appendChild(timeSpan);
            }

            // Token usage
            if (message.metadata.usage && message.metadata.usage.total_tokens) {
                const tokensSpan = document.createElement('span');
                tokensSpan.textContent = `${message.metadata.usage.total_tokens} tokens`;
                info.appendChild(tokensSpan);
            }
        } else {
            // Timestamp for user messages
            const timeSpan = document.createElement('span');
            timeSpan.textContent = message.timestamp.toLocaleTimeString();
            info.appendChild(timeSpan);
        }

        contentContainer.appendChild(bubble);
        contentContainer.appendChild(info);

        messageDiv.appendChild(avatar);
        messageDiv.appendChild(contentContainer);

        this.chatMessages.appendChild(messageDiv);
    }

    removeWelcomeMessage() {
        const welcomeMessage = this.chatMessages.querySelector('.welcome-message');
        if (welcomeMessage) {
            welcomeMessage.remove();
        }
    }

    clearChat() {
        if (confirm('Are you sure you want to clear the chat history?')) {
            this.chatHistory = [];
            this.chatMessages.innerHTML = '';
            this.addWelcomeMessage();
        }
    }

    addWelcomeMessage() {
        const welcomeDiv = document.createElement('div');
        welcomeDiv.className = 'welcome-message';
        welcomeDiv.innerHTML = `
            <i class="fas fa-hand-wave"></i>
            <h2>Welcome to TQ GenAI Chat</h2>
            <p>Select an AI provider above and start chatting! Choose from:</p>
            <ul>
                <li><strong>Cohere</strong> - Fast and reliable (1.05s avg)</li>
                <li><strong>OpenRouter</strong> - Free Llama 3.2 access (8.66s avg)</li>
                <li><strong>Perplexity</strong> - Search-enhanced AI (3.32s avg)</li>
                <li><strong>Alibaba Ollama</strong> - Local private AI (3.14s avg)</li>
            </ul>
        `;
        this.chatMessages.appendChild(welcomeDiv);
    }

    scrollToBottom() {
        this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
    }

    showLoading() {
        this.loadingOverlay.style.display = 'flex';
        this.sendButton.disabled = true;
    }

    hideLoading() {
        this.loadingOverlay.style.display = 'none';
        this.sendButton.disabled = !this.currentProvider || !this.currentModel;
    }

    showError(message) {
        this.errorMessage.textContent = message;
        this.errorModal.style.display = 'flex';
    }

    hideError() {
        this.errorModal.style.display = 'none';
    }

    async apiCall(endpoint, options = {}) {
        const url = `${this.apiBase}${endpoint}`;

        const defaultOptions = {
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Basic ${btoa(`${this.auth.username}:${this.auth.password}`)}`
            }
        };

        const finalOptions = {
            ...defaultOptions,
            ...options,
            headers: {
                ...defaultOptions.headers,
                ...options.headers
            }
        };

        const response = await fetch(url, finalOptions);

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.detail || `HTTP ${response.status}: ${response.statusText}`);
        }

        return response.json();
    }
}

// Initialize the chat application when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    new TQGenAIChat();
});

// Utility functions
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function formatTime(timestamp) {
    return new Date(timestamp).toLocaleTimeString([], {
        hour: '2-digit',
        minute: '2-digit'
    });
}

function formatBytes(bytes) {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}