/**
 * Modern Chat Client for TQ GenAI Chat
 * Handles communication with AI providers and UI interactions
 */

class ChatClient {
    constructor() {
        this.chatHistory = [];
        this.selectedProvider = 'groq';
        this.selectedModel = '';
        this.isGenerating = false;
        this.chatForm = document.getElementById('chat-form');
        this.chatInput = document.getElementById('chat-input');
        this.chatMessages = document.getElementById('chat-messages');
        this.providerTabs = document.getElementById('provider-tabs');
        this.modelSelect = document.getElementById('model-select');
        this.saveBtn = document.getElementById('save-chat');
        this.exportBtn = document.getElementById('export-chat');
        this.micBtn = document.getElementById('mic-btn');
        this.recordingStatus = document.getElementById('recording-status');

        this.providers = [];

        this.initUI();
        this.bindEvents();
    }

    initUI() {
        this.fetchProviders().then(() => {
            let tabsHTML = '';
            this.providers.forEach(provider => {
                tabsHTML += `
                    <div class="provider-tab${provider.id === this.selectedProvider ? ' active' : ''}"
                         data-provider="${provider.id}">
                        <i class="fas fa-${this.getProviderIcon(provider.id)}"></i>
                        ${provider.name}
                    </div>
                `;
            });
            if (this.providerTabs) {
                this.providerTabs.innerHTML = tabsHTML;
            } else {
                console.warn('Provider tabs element not found');
            }

            // Load models for default provider
            this.loadModels(this.selectedProvider);
        });
    }

    async fetchProviders() {
        try {
            const response = await fetch('/get_providers');
            if (!response.ok) throw new Error('Failed to fetch providers');

            const providerIds = await response.json();

            this.providers = providerIds.map(id => ({
                id: id,
                name: this.formatProviderName(id),
                icon: this.getProviderIcon(id)
            }));

            console.log('Providers loaded:', this.providers);
        } catch (error) {
            console.error('Error fetching providers:', error);
            this.providers = [{ id: 'groq', name: 'Groq', icon: 'bolt' }];
        }
    }

    formatProviderName(id) {
        switch (id) {
            case 'openai': return 'OpenAI';
            case 'anthropic': return 'Anthropic';
            case 'xai': return 'xAI (Grok)';
            case 'groq': return 'Groq';
            case 'mistral': return 'Mistral';
            case 'cohere': return 'Cohere';
            case 'deepseek': return 'DeepSeek';
            default: return id.charAt(0).toUpperCase() + id.slice(1);
        }
    }

    getProviderIcon(id) {
        switch (id) {
            case 'openai': return 'brain';
            case 'anthropic': return 'lightbulb';
            case 'xai': return 'robot';
            case 'groq': return 'bolt';
            case 'mistral': return 'wind';
            case 'cohere': return 'layer-group';
            case 'deepseek': return 'search';
            default: return 'comment';
        }
    }

    bindEvents() {
        console.log("Binding ChatClient events");

        // Get all required elements and add safe null checks
        const elements = {
            chatForm: document.getElementById('chat-form'),
            chatInput: document.getElementById('chat-input'),
            chatMessages: document.getElementById('chat-messages'),
            providerSelect: document.getElementById('provider-select'),
            modelSelect: document.getElementById('model-select'),
            micButton: document.getElementById('mic-btn'),
            recordingStatus: document.getElementById('recording-status')
        };

        // Check if elements exist before binding events
        if (elements.chatForm) {
            elements.chatForm.addEventListener('submit', (e) => {
                e.preventDefault();
                this.sendMessage();
            });
            console.log("Chat form submit event bound");
        } else {
            console.error("Chat form element not found");
        }

        // Add similar checks for other elements
        if (elements.chatInput) {
            elements.chatInput.addEventListener('keydown', (e) => {
                // Handle Shift+Enter for new line
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    document.getElementById('chat-form')?.dispatchEvent(new Event('submit'));
                }

                // Auto-resize textarea
                setTimeout(() => {
                    e.target.style.height = 'auto';
                    e.target.style.height = e.target.scrollHeight + 'px';
                }, 0);
            });
            console.log("Chat input events bound");
        } else {
            console.error("Chat input element not found");
        }

        // Provider and model selection handling with null checks
        if (elements.providerSelect) {
            elements.providerSelect.addEventListener('change', () => {
                const provider = elements.providerSelect.value;
                this.selectedProvider = provider;
                this.loadModels(provider);
            });
            console.log("Provider select event bound");
        } else {
            console.error("Provider select element not found");
        }

        // Add safe check for other elements and their event handlers
        // ...

        // Initialize provider/model lists if elements exist
        if (elements.providerSelect) {
            this.loadProviders();
        }
    }

    async loadModels(provider) {
        try {
            // Show loading state
            this.modelSelect.innerHTML = '<option>Loading models...</option>';
            this.modelSelect.disabled = true;

            // Fetch models from server
            const response = await fetch(`/get_models/${provider}`);
            if (!response.ok) throw new Error('Failed to load models');

            const data = await response.json();

            // Populate select with models
            let optionsHTML = '';
            data.models.forEach(model => {
                const selected = model === data.default ? 'selected' : '';
                optionsHTML += `<option value="${model}" ${selected}>${model}</option>`;
            });

            this.modelSelect.innerHTML = optionsHTML;
            this.modelSelect.disabled = false;
            this.selectedModel = data.default || data.models[0];

        } catch (error) {
            console.error('Error loading models:', error);
            this.modelSelect.innerHTML = '<option>Error loading models</option>';
            this.modelSelect.disabled = true;
            this.showNotification('Error loading models. Please try again.', 'error');
        }
    }

    changeProvider(provider) {
        // Update UI
        document.querySelectorAll('.provider-tab').forEach(tab => {
            tab.classList.toggle('active', tab.dataset.provider === provider);
        });

        this.selectedProvider = provider;
        this.loadModels(provider);
    }

    async sendMessage() {
        const message = this.chatInput.value.trim();
        if (!message || this.isGenerating) return;

        // Clear input and reset height
        this.chatInput.value = '';
        this.chatInput.style.height = 'auto';

        // Add user message to UI
        this.addMessageToUI(message, true);

        // Add to chat history
        this.chatHistory.push({
            isUser: true,
            content: message
        });

        // Set generating state
        this.isGenerating = true;
        this.toggleLoadingState(true);

        // Start progress indication
        if (window.chatProgress) {
            window.chatProgress.start();
            window.chatProgress.updateStatus(`Generating with ${this.selectedProvider}...`);
        }

        try {
            // Send to server
            const response = await fetch('/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    message: message,
                    provider: this.selectedProvider,
                    model: this.selectedModel
                }),
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || 'Server error');
            }

            const data = await response.json();

            // Add AI response to UI and chat history
            const aiResponse = data.response;
            this.addMessageToUI(aiResponse, false);

            this.chatHistory.push({
                isUser: false,
                content: aiResponse
            });

            // Complete progress indication
            if (window.chatProgress) {
                window.chatProgress.complete();
            }

            // Play notification sound if enabled
            if (window.uiPreferences?.preferences?.sounds) {
                this.playSound('message-received');
            }

        } catch (error) {
            console.error('Chat error:', error);
            if (window.toast) {
                window.toast.error(`Error: ${error.message}`);
            } else {
                this.showNotification(`Error: ${error.message}`, 'error');
            }
            // Add error message to UI
            this.addErrorMessageToUI();

            // Complete progress with error
            if (window.chatProgress) {
                window.chatProgress.complete();
            }

        } finally {
            this.isGenerating = false;
            this.toggleLoadingState(false);
        }
    }

    addMessageToUI(content, isUser) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${isUser ? 'message-user' : 'message-ai'}`;

        // Create avatar
        const avatarDiv = document.createElement('div');
        avatarDiv.className = 'message-avatar';
        avatarDiv.innerHTML = isUser ?
            '<i class="fas fa-user"></i>' :
            '<i class="fas fa-robot"></i>';

        // Create message bubble
        const bubbleDiv = document.createElement('div');
        bubbleDiv.className = 'message-bubble';

        // Create message text
        const textDiv = document.createElement('div');
        textDiv.className = 'message-text';

        // Handle different content types
        if (typeof content === 'string') {
            // Render markdown content
            textDiv.innerHTML = this.renderMarkdown(content);
        } else {
            // Complex response object
            textDiv.innerHTML = this.renderMarkdown(content.text);

            // Add metadata if available
            if (content.metadata) {
                const metaDiv = document.createElement('div');
                metaDiv.className = 'message-metadata';
                metaDiv.textContent = `${content.metadata.provider || 'AI'} / ${content.metadata.model || 'Unknown'} (${content.metadata.response_time || '?'})`;
                bubbleDiv.appendChild(metaDiv);
            }
        }

        // Assemble message
        bubbleDiv.appendChild(textDiv);
        messageDiv.appendChild(avatarDiv);
        messageDiv.appendChild(bubbleDiv);

        // Add to chat container with animation
        messageDiv.style.opacity = '0';
        messageDiv.style.transform = 'translateY(20px)';
        this.chatMessages.appendChild(messageDiv);

        // Scroll to bottom
        this.chatMessages.scrollTop = this.chatMessages.scrollHeight;

        // Trigger animation
        setTimeout(() => {
            messageDiv.style.transition = 'opacity 0.3s ease, transform 0.3s ease';
            messageDiv.style.opacity = '1';
            messageDiv.style.transform = 'translateY(0)';

            // Apply syntax highlighting to code blocks
            this.highlightCodeBlocks();
        }, 10);
    }

    addErrorMessageToUI() {
        const messageDiv = document.createElement('div');
        messageDiv.className = 'message message-system';
        messageDiv.innerHTML = `
            <div class="message-bubble error">
                <div class="message-text">
                    <i class="fas fa-exclamation-triangle"></i>
                    Sorry, there was an error generating a response. Please try again.
                </div>
            </div>
        `;

        this.chatMessages.appendChild(messageDiv);
        this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
    }

    toggleLoadingState(isLoading) {
        const submitBtn = this.chatForm.querySelector('button[type="submit"]');

        if (isLoading) {
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
            this.chatInput.disabled = true;
        } else {
            submitBtn.disabled = false;
            submitBtn.innerHTML = '<i class="fas fa-paper-plane"></i>';
            this.chatInput.disabled = false;
            this.chatInput.focus();
        }
    }

    renderMarkdown(text) {
        if (!text) return '';

        // Convert headers
        text = text.replace(/^### (.*$)/gm, '<h3>$1</h3>')
            .replace(/^## (.*$)/gm, '<h2>$1</h2>')
            .replace(/^# (.*$)/gm, '<h1>$1</h1>');

        // Convert code blocks with language
        text = text.replace(/```([a-z]*)\n([\s\S]*?)```/g, (match, lang, code) => {
            return `<pre><code class="language-${lang || 'text'}">${this.escapeHtml(code)}</code></pre>`;
        });

        // Convert inline code
        text = text.replace(/`([^`]+)`/g, '<code>$1</code>');

        // Convert bold and italic
        text = text.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>');

        // Convert unordered lists
        text = text.replace(/^\* (.*$)/gm, '<ul><li>$1</li></ul>')
            .replace(/<\/ul>\s*<ul>/g, '');

        // Convert ordered lists
        text = text.replace(/^\d+\. (.*$)/gm, '<ol><li>$1</li></ol>')
            .replace(/<\/ol>\s*<ol>/g, '');

        // Convert blockquotes
        text = text.replace(/^> (.*$)/gm, '<blockquote>$1</blockquote>')
            .replace(/<\/blockquote>\s*<blockquote>/g, '<br>');

        // Convert line breaks
        text = text.replace(/\n/g, '<br>');

        return text;
    }

    highlightCodeBlocks() {
        // If using a library like highlight.js:
        // if (window.hljs) {
        //     document.querySelectorAll('pre code').forEach((block) => {
        //         hljs.highlightBlock(block);
        //     });
        // }

        // Simple syntax highlighting for now
        document.querySelectorAll('pre code').forEach((block) => {
            if (block.classList.contains('language-javascript')) {
                const keywords = ['function', 'return', 'if', 'else', 'for', 'while', 'let', 'const', 'var', 'async', 'await'];
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

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    showNotification(message, type = 'info') {
        const notif = document.createElement('div');
        notif.className = `notification ${type}`;
        notif.innerHTML = `<i class="fas fa-${type === 'error' ? 'exclamation-circle' : 'info-circle'}"></i> ${message}`;
        document.body.appendChild(notif);

        setTimeout(() => {
            notif.style.opacity = '1';
        }, 10);

        setTimeout(() => {
            notif.style.opacity = '0';
            setTimeout(() => {
                document.body.removeChild(notif);
            }, 300);
        }, 3000);
    }

    async saveChat() {
        if (this.chatHistory.length === 0) {
            this.showNotification('No chat to save', 'info');
            return;
        }

        try {
            const response = await fetch('/save_chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    history: this.chatHistory
                }),
            });

            if (!response.ok) {
                throw new Error('Failed to save chat');
            }

            const data = await response.json();
            this.showNotification(`Chat saved as: ${data.filename}`, 'info');

        } catch (error) {
            console.error('Error saving chat:', error);
            this.showNotification('Error saving chat', 'error');
        }
    }

    async exportChat() {
        if (this.chatHistory.length === 0) {
            this.showNotification('No chat to export', 'info');
            return;
        }

        try {
            const response = await fetch('/export_chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    history: this.chatHistory
                }),
            });

            if (!response.ok) {
                throw new Error('Failed to export chat');
            }

            const data = await response.json();
            this.showNotification(`Chat exported as: ${data.filename}`, 'info');

        } catch (error) {
            console.error('Error exporting chat:', error);
            this.showNotification('Error exporting chat', 'error');
        }
    }

    toggleVoiceInput() {
        if (!('webkitSpeechRecognition' in window)) {
            this.showNotification('Speech recognition is not supported in this browser', 'error');
            return;
        }

        // Toggle recording state
        if (this.isRecording) {
            // Stop recording
            this.recognition.stop();
            this.isRecording = false;
            this.micBtn.classList.remove('recording');
            this.micBtn.innerHTML = '<i class="fas fa-microphone"></i>';
            this.recordingStatus.textContent = '';
        } else {
            // Start recording
            this.recognition = new webkitSpeechRecognition();
            this.recognition.continuous = false;
            this.recognition.interimResults = true;

            this.recognition.onstart = () => {
                this.isRecording = true;
                this.micBtn.classList.add('recording');
                this.micBtn.innerHTML = '<i class="fas fa-microphone-slash"></i>';
                this.recordingStatus.textContent = 'Listening...';
            };

            this.recognition.onresult = (event) => {
                const transcript = Array.from(event.results)
                    .map(result => result[0].transcript)
                    .join('');

                this.chatInput.value = transcript;
                this.recordingStatus.textContent = transcript;
            };

            this.recognition.onerror = (event) => {
                console.error('Speech recognition error', event.error);
                this.isRecording = false;
                this.micBtn.classList.remove('recording');
                this.micBtn.innerHTML = '<i class="fas fa-microphone"></i>';
                this.recordingStatus.textContent = `Error: ${event.error}`;
            };

            this.recognition.onend = () => {
                this.isRecording = false;
                this.micBtn.classList.remove('recording');
                this.micBtn.innerHTML = '<i class="fas fa-microphone"></i>';
                this.recordingStatus.textContent = '';
            };

            this.recognition.start();
        }
    }

    cancelResponse() {
        if (!this.isGenerating) return;

        this.isGenerating = false;
        this.toggleLoadingState(false);

        // Add a system message about cancellation
        const systemMsg = document.createElement('div');
        systemMsg.className = 'message message-system';
        systemMsg.innerHTML = `
            <div class="message-bubble">
                <div class="message-text">
                    <i class="fas fa-ban"></i> Response generation canceled
                </div>
            </div>
        `;

        this.chatMessages.appendChild(systemMsg);
        this.chatMessages.scrollTop = this.chatMessages.scrollHeight;

        // Add to history
        this.chatHistory.push({
            isUser: false,
            isSystem: true,
            content: "Response generation canceled by user"
        });
    }

    // Add the missing loadProviders method
    async loadProviders() {
        try {
            const response = await fetch('/get_providers');
            if (!response.ok) throw new Error('Failed to fetch providers');

            const providerIds = await response.json();

            this.providers = providerIds.map(id => ({
                id: id,
                name: this.formatProviderName(id),
                icon: this.getProviderIcon(id)
            }));

            // Populate provider select dropdown if it exists
            const providerSelect = document.getElementById('provider-select');
            if (providerSelect) {
                providerSelect.innerHTML = '';
                this.providers.forEach(provider => {
                    const option = document.createElement('option');
                    option.value = provider.id;
                    option.textContent = provider.name;
                    if (provider.id === this.selectedProvider) {
                        option.selected = true;
                    }
                    providerSelect.appendChild(option);
                });

                // Load models for the selected provider
                this.loadModels(this.selectedProvider);
            }

            console.log('Providers loaded:', this.providers);
        } catch (error) {
            console.error('Error loading providers:', error);
        }
    }

    // Add back the retryLastMessage function
    retryLastMessage(newProvider = null, newModel = null) {
        console.log("⟳ Retry request initiated");

        // Find the last user message
        let lastUserMessage = null;
        let lastUserMessageIndex = -1;

        for (let i = this.chatHistory.length - 1; i >= 0; i--) {
            if (this.chatHistory[i].isUser) {
                lastUserMessage = this.chatHistory[i].content;
                lastUserMessageIndex = i;
                break;
            }
        }

        if (!lastUserMessage) {
            console.warn("⚠ No user message found to retry");
            return;
        }

        // Log useful information for debugging
        console.log(`⟳ Found last user message at index ${lastUserMessageIndex}: "${lastUserMessage.substring(0, 50)}..."`);
        console.log(`⟳ Current provider: ${this.selectedProvider}, model: ${this.selectedModel}`);
        console.log(`⟳ Requested provider: ${newProvider || 'current'}, model: ${newModel || 'current'}`);

        // Store original provider and model
        const originalProvider = this.selectedProvider;
        const originalModel = this.selectedModel;

        // If new provider or model is specified, update them for this request
        let providerChanged = false;
        let modelChanged = false;

        if (newProvider) {
            providerChanged = (newProvider !== this.selectedProvider);
            this.selectedProvider = newProvider;
            console.log(`⟳ Changed provider to: ${newProvider}`);

            // Update UI to reflect the change
            if (providerChanged) {
                const providerSelect = document.getElementById('provider-select');
                if (providerSelect) {
                    providerSelect.value = newProvider;
                }
            }
        }

        if (newModel) {
            modelChanged = (newModel !== this.selectedModel);
            this.selectedModel = newModel;
            console.log(`⟳ Changed model to: ${newModel}`);
        }

        // Remove the last AI response from the UI
        if (!this.isGenerating && this.chatMessages.lastElementChild &&
            !this.chatMessages.lastElementChild.classList.contains('message-user')) {
            console.log(`⟳ Removing last AI response from UI`);
            this.chatMessages.removeChild(this.chatMessages.lastElementChild);

            // Also remove from history
            if (this.chatHistory.length > 0 && !this.chatHistory[this.chatHistory.length - 1].isUser) {
                console.log(`⟳ Removing last AI response from history`);
                this.chatHistory.pop();
            }
        }

        // Set the message
        this.chatInput.value = lastUserMessage;
        console.log(`⟳ Set input field with last message`);

        // Create a temporary flag to prevent restoring provider/model too early
        this._isRetryingWithDifferent = providerChanged || modelChanged;
        console.log(`⟳ Retry with different config: ${this._isRetryingWithDifferent}`);

        // Send the message
        console.log(`⟳ Sending message for retry`);
        this.sendMessage();

        // Create a handler to restore original provider and model after sending is complete
        if (this._isRetryingWithDifferent) {
            console.log(`⟳ Setting up restoration of original provider/model`);

            const checkGeneratingState = () => {
                if (!this.isGenerating) {
                    // Request completed, now we can restore
                    console.log(`⟳ Restoring original provider (${originalProvider}) and model (${originalModel})`);
                    this.selectedProvider = originalProvider;
                    this.selectedModel = originalModel;

                    // Update UI to reflect the restored provider
                    const providerSelect = document.getElementById('provider-select');
                    if (providerSelect) {
                        providerSelect.value = originalProvider;
                    }

                    this._isRetryingWithDifferent = false;
                    console.log(`⟳ Retry completed successfully`);
                } else {
                    // Still generating, check again later
                    console.log(`⟳ Still generating, will check again later`);
                    setTimeout(checkGeneratingState, 500);
                }
            };

            // Start checking after a short delay
            setTimeout(checkGeneratingState, 500);
        }
    }
}

// Initialize the chat client when the DOM is loaded
document.addEventListener('DOMContentLoaded', function () {
    console.log("DOM content loaded for ChatClient initialization");

    // Check if required elements exist before creating ChatClient
    const requiredElements = [
        'chat-form',
        'chat-input',
        'chat-messages'
    ];

    const missingElements = requiredElements.filter(id => !document.getElementById(id));

    if (missingElements.length > 0) {
        console.error(`Cannot initialize ChatClient. Missing elements: ${missingElements.join(', ')}`);
        return;
    }

    // Create chat client if all required elements exist
    window.chatClient = new ChatClient();
    console.log("ChatClient initialized");
});
