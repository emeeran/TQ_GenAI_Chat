// Theme toggle logic
function setTheme(theme) {
    document.body.classList.remove('theme-dark', 'theme-light');
    document.body.classList.add(`theme-${theme}`);
    localStorage.setItem('theme', theme);
    const label = document.getElementById('theme-label');
    const icon = document.querySelector('#theme-toggle i');
    if (theme === 'dark') {
        if (label) label.textContent = 'Light';
        if (icon) icon.className = 'fas fa-sun';
    } else {
        if (label) label.textContent = 'Dark';
        if (icon) icon.className = 'fas fa-moon';
    }
}

function toggleTheme() {
    const current = localStorage.getItem('theme') || 'light';
    setTheme(current === 'dark' ? 'light' : 'dark');
}

// On load, set theme and restore saved settings
document.addEventListener('DOMContentLoaded', () => {
    setTheme(localStorage.getItem('theme') || 'light');

    // Restore saved provider and model settings
    const savedProvider = localStorage.getItem('defaultProvider');
    const savedModel = localStorage.getItem('defaultModel');

    if (savedProvider && document.getElementById('provider')) {
        document.getElementById('provider').value = savedProvider;
    }

    // Always refresh models on page load
    updateModels().then(() => {
        if (savedModel && document.getElementById('model')) {
            document.getElementById('model').value = savedModel;
        }
        updateProviderModelDisplay();
    });

    // Update provider/model display initially
    updateProviderModelDisplay();

    // Real-time polling for provider/model updates every 3 seconds
    // Real-time polling for provider/model updates every 20 minutes
    let providerModelPoller = setInterval(() => {
        updateModels().then(() => {
            updateProviderModelDisplay();
        });
    }, 1200000);

    // Stop polling on page unload
    window.addEventListener('beforeunload', () => {
        clearInterval(providerModelPoller);
    });
});
// Debounce function to limit rapid calls
const debounce = (func, wait) => {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
};

// Cache DOM queries
const elements = {
    chatBox: document.getElementById('chat-box'),
    userInput: document.getElementById('user-input'),
    provider: document.getElementById('provider'),
    model: document.getElementById('model'),
    persona: document.getElementById('persona'),
    customPersonaInput: document.getElementById('custom-persona-textarea'),
    personaContent: document.getElementById('persona-content')
};

// Always refresh models on provider change
if (elements.provider) {
    elements.provider.addEventListener('change', () => {
        updateModels();
        // Save provider selection
        localStorage.setItem('defaultProvider', elements.provider.value);
        updateProviderModelDisplay();
    });
}

// Save model selection when changed
if (elements.model) {
    elements.model.addEventListener('change', () => {
        localStorage.setItem('defaultModel', elements.model.value);
        updateProviderModelDisplay();
    });
}

// Function to truncate text to a specified length
function truncateText(text, maxLength) {
    if (text.length <= maxLength) return text;
    return text.substring(0, maxLength - 3) + '...';
}

// Function to reset all global defaults
function resetGlobalDefaults() {
    if (confirm('Reset all global defaults? This will clear your saved provider and model preferences.')) {
        localStorage.removeItem('defaultProvider');
        localStorage.removeItem('defaultModel');
        localStorage.removeItem('defaultPersona');

        // Reset to first options
        const providerSelect = document.getElementById('provider');
        const modelSelect = document.getElementById('model');
        const personaSelect = document.getElementById('persona');

        if (providerSelect) providerSelect.selectedIndex = 0;
        if (modelSelect) {
            modelSelect.innerHTML = '<option value="">Select Model</option>';
            modelSelect.disabled = true;
        }
        if (personaSelect) personaSelect.selectedIndex = 0;

        updateProviderModelDisplay();
        alert('Global defaults have been reset!');
    }
}

// Function to update provider/model display at bottom of sidebar
function updateProviderModelDisplay() {
    const provider = document.getElementById('provider')?.value || 'N/A';
    const model = document.getElementById('model')?.value || 'N/A';

    let displayElement = document.getElementById('provider-model-display');
    if (!displayElement) {
        // Create the display element if it doesn't exist
        displayElement = document.createElement('div');
        displayElement.id = 'provider-model-display';
        displayElement.className = 'provider-model-display';

        // Add to bottom of sidebar
        const sidebar = document.querySelector('.sidebar');
        if (sidebar) {
            sidebar.appendChild(displayElement);
        }
    }

    // Truncate provider and model names to prevent overflow
    const displayProvider = truncateText(provider, 12);
    const displayModel = truncateText(model, 20);

    displayElement.innerHTML = `<strong>${displayProvider} | ${displayModel}</strong>`;
    displayElement.title = `${provider} | ${model}`; // Full text on hover
}

// Persona selector logic
if (elements.persona) {
    const customTextarea = document.getElementById('custom-persona-textarea');
    elements.persona.addEventListener('change', async function () {
        // Save persona selection
        localStorage.setItem('defaultPersona', this.value);

        if (this.value === 'custom') {
            customTextarea.classList.remove('d-none');
        } else {
            customTextarea.classList.add('d-none');
        }
    });
    // Trigger initial content
    elements.persona.dispatchEvent(new Event('change'));
}

// Slider value updates
document.addEventListener('DOMContentLoaded', () => {
    // Max Tokens slider
    const maxTokensSlider = document.getElementById('max-tokens');
    const maxTokensValue = document.getElementById('max-tokens-value');
    if (maxTokensSlider && maxTokensValue) {
        maxTokensSlider.addEventListener('input', (e) => {
            maxTokensValue.textContent = e.target.value;
            updateSliderProgress(maxTokensSlider);
        });
        updateSliderProgress(maxTokensSlider);
    }

    // Temperature slider
    const temperatureSlider = document.getElementById('temperature');
    const temperatureValue = document.getElementById('temperature-value');
    if (temperatureSlider && temperatureValue) {
        temperatureSlider.addEventListener('input', (e) => {
            temperatureValue.textContent = parseFloat(e.target.value).toFixed(1);
            updateSliderProgress(temperatureSlider);
        });
        updateSliderProgress(temperatureSlider);
    }
});

function updateSliderProgress(slider) {
    const value = ((slider.value - slider.min) / (slider.max - slider.min)) * 100;
    slider.style.setProperty('--range-progress', value + '%');
}

// Copy response functionality
let lastAiResponseText = '';

function copyLastResponse() {
    if (lastAiResponseText) {
        navigator.clipboard.writeText(lastAiResponseText).then(() => {
            showNotification('Response copied to clipboard!', 'success');
        }).catch(() => {
            // Fallback for older browsers
            const textArea = document.createElement('textarea');
            textArea.value = lastAiResponseText;
            document.body.appendChild(textArea);
            textArea.select();
            document.execCommand('copy');
            document.body.removeChild(textArea);
            showNotification('Response copied to clipboard!', 'success');
        });
    }
}

// Update processing indicators
function showInputProgress() {
    const progressIndicator = document.getElementById('input-progress');
    if (progressIndicator) {
        progressIndicator.classList.remove('d-none');
    }
}

function hideInputProgress() {
    const progressIndicator = document.getElementById('input-progress');
    if (progressIndicator) {
        progressIndicator.classList.add('d-none');
    }
}

// Add request queue
const requestQueue = [];
let isProcessing = false;

async function processQueue() {
    if (isProcessing || requestQueue.length === 0) return;

    isProcessing = true;
    while (requestQueue.length > 0) {
        const request = requestQueue.shift();
        try {
            await request();
        } catch (error) {
            console.error('Request error:', error);
        }
    }
    isProcessing = false;
}

async function updateModels() {
    const provider = document.getElementById('provider').value;
    const modelSelect = document.getElementById('model');

    if (!provider) {
        modelSelect.innerHTML = '<option value="">Select Provider First</option>';
        modelSelect.disabled = true;
        return;
    }

    modelSelect.innerHTML = '<option value="">Loading models...</option>';
    modelSelect.disabled = true;

    try {
        console.log(`Fetching models for provider: ${provider}`);
        const response = await fetch(`/get_models/${provider}`);

        console.log(`Response status: ${response.status}`);
        console.log(`Response headers:`, response.headers);

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        // Check if response is JSON
        const contentType = response.headers.get('content-type');
        if (!contentType || !contentType.includes('application/json')) {
            const text = await response.text();
            console.error('Non-JSON response received:', text);
            throw new Error('Server returned non-JSON response');
        }

        const data = await response.json();
        console.log('Models data received:', data);

        if (data.error) {
            throw new Error(`Server error: ${data.error}`);
        }

        const models = data.models;
        const defaultModel = data.default;

        modelSelect.innerHTML = '<option value="">Select Model</option>';

        if (Array.isArray(models) && models.length > 0) {
            models.sort().forEach(model => {
                const option = document.createElement('option');
                option.value = model;
                option.textContent = model;
                if (model === defaultModel) {
                    option.selected = true;
                }
                modelSelect.appendChild(option);
            });
            modelSelect.disabled = false;
            console.log(`Successfully loaded ${models.length} models for ${provider}`);
        } else {
            modelSelect.innerHTML = '<option value="">No models available</option>';
            modelSelect.disabled = true;
            console.warn(`No models available for provider: ${provider}`);
        }
    } catch (error) {
        console.error('Error fetching models:', error);
        modelSelect.innerHTML = '<option value="">Error loading models</option>';
        modelSelect.disabled = true;

        // Show user-friendly error message
        showNotification(`Error updating models: ${error.message}`, 'error');
    }
}

function appendMessage(message, isUser = false, messageIndex = null) {
    const chatBox = document.getElementById('chat-box');
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${isUser ? 'user-message' : 'ai-message'}`;

    // Add message index as data attribute for editing
    if (messageIndex !== null) {
        messageDiv.setAttribute('data-message-index', messageIndex);
    }


    if (isUser) {
        // ...existing code for user messages...
        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';
        contentDiv.textContent = message;
        messageDiv.appendChild(contentDiv);

        const actionsDiv = document.createElement('div');
        actionsDiv.className = 'message-actions';

        const editBtn = document.createElement('button');
        editBtn.className = 'btn btn-sm btn-outline-secondary edit-message-btn';
        editBtn.innerHTML = '<i class="fas fa-edit"></i> Edit';
        editBtn.title = 'Edit and resubmit this message';
        editBtn.onclick = () => editMessage(messageIndex);

        actionsDiv.appendChild(editBtn);
        messageDiv.appendChild(actionsDiv);
    } else {
        // AI message: check for verification
        const content = typeof message === 'object' ? message : { text: message };
        const markdown = content.text || message;
        // Convert markdown to HTML
        const html = marked.parse(markdown, {
            gfm: true,
            breaks: true,
            headerIds: false,
            mangle: false
        });
        messageDiv.innerHTML = html;

        // Add metadata if available
        if (content.metadata) {
            const metadataDiv = document.createElement('div');
            metadataDiv.className = 'message-metadata';
            metadataDiv.innerHTML = `
                <small class="text-muted">
                    Generated by ${content.metadata.provider}/${content.metadata.model}
                    in ${content.metadata.response_time}
                </small>
            `;
            messageDiv.appendChild(metadataDiv);
        }

        // If verification is present, show badge and summary
        if (message.verification) {
            const badge = document.createElement('span');
            badge.className = 'verified-badge clickable';
            badge.innerHTML = '<i class="fas fa-shield-check"></i> Verified';
            badge.title = 'Click to show/hide verification summary';
            messageDiv.insertAdjacentElement('afterbegin', badge);

            // Create verification summary, hidden by default
            const verificationDiv = document.createElement('div');
            verificationDiv.className = 'verification-summary hidden';
            let verifierInfo = '';
            if (message.verification.metadata && message.verification.metadata.provider && message.verification.metadata.model) {
                verifierInfo = `<div class="verifier-meta"><small class="text-muted">Verified by: <b>${message.verification.metadata.provider}/${message.verification.metadata.model}</b></small></div>`;
            }
            verificationDiv.innerHTML = verifierInfo + marked.parse(message.verification.text || '');
            messageDiv.appendChild(verificationDiv);

            // Toggle summary on badge click
            badge.addEventListener('click', () => {
                verificationDiv.classList.toggle('hidden');
            });
        }
    }

    chatBox.appendChild(messageDiv);
    chatBox.scrollTop = chatBox.scrollHeight;

    // Apply syntax highlighting to code blocks
    if (!isUser) {
        messageDiv.querySelectorAll('pre code').forEach((block) => {
            hljs.highlightElement(block);
        });
    }

    if (!isUser && message.text) {
        lastAiResponse = message.text;
    }
}

function editMessage(messageIndex) {
    if (messageIndex === null || messageIndex >= chatHistory.length) {
        return;
    }

    const messageToEdit = chatHistory[messageIndex];
    if (!messageToEdit.isUser) {
        return; // Only allow editing user messages
    }

    // Create edit modal
    const modal = document.createElement('div');
    modal.className = 'modal fade show';
    modal.style.display = 'block';
    modal.innerHTML = `
        <div class="modal-dialog modal-lg">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title">Edit Message</h5>
                    <button type="button" class="btn-close" onclick="this.closest('.modal').remove()"></button>
                </div>
                <div class="modal-body">
                    <div class="mb-3">
                        <label for="edit-message-text" class="form-label">Message:</label>
                        <textarea class="form-control" id="edit-message-text" rows="4" placeholder="Enter your message...">${messageToEdit.content}</textarea>
                    </div>
                    <div class="alert alert-info">
                        <i class="fas fa-info-circle"></i>
                        Editing this message will remove all subsequent messages and regenerate the conversation from this point.
                    </div>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" onclick="this.closest('.modal').remove()">Cancel</button>
                    <button type="button" class="btn btn-primary" onclick="submitEditedMessage(${messageIndex})">Update & Resubmit</button>
                </div>
            </div>
        </div>
    `;

    document.body.appendChild(modal);

    // Focus on the textarea
    setTimeout(() => {
        document.getElementById('edit-message-text').focus();
    }, 100);
}

function submitEditedMessage(messageIndex) {
    const newMessageText = document.getElementById('edit-message-text').value.trim();

    if (!newMessageText) {
        alert('Message cannot be empty');
        return;
    }

    // Remove the modal
    document.querySelector('.modal').remove();

    // Update the message in chat history
    chatHistory[messageIndex].content = newMessageText;

    // Remove all messages after this one from chat history
    chatHistory = chatHistory.slice(0, messageIndex + 1);

    // Re-render the conversation
    reRenderConversation();

    // Resubmit the edited message
    sendMessage(newMessageText, false);
}

function reRenderConversation() {
    const chatBox = document.getElementById('chat-box');
    chatBox.innerHTML = '';

    chatHistory.forEach((msg, index) => {
        appendMessage(msg.content, msg.isUser, index);
    });
}

let chatHistory = [];
let lastMessage = null;
let lastAiResponse = '';

function showProcessing(show = true) {
    document.getElementById('processing').classList.toggle('d-none', !show);
}

function showFeedback(show = true) {
    document.getElementById('feedback').classList.toggle('d-none', !show);
}

async function saveChat() {
    try {
        const data = {
            history: chatHistory,
            timestamp: new Date().toISOString()
        };

        const response = await fetch('/documents/save_chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
        }

        const result = await response.json();
        alert(`Chat saved successfully as: ${result.filename}`);
    } catch (error) {
        console.error('Save error:', error);
        alert(`Error saving chat: ${error.message}`);
    }
}

async function loadSaved() {
    try {
        // Get list of saved chats
        const response = await fetch('/documents/list_saved_chats');
        const data = await response.json();
        const chats = data.chats || [];

        if (chats.length === 0) {
            alert('No saved chats found');
            return;
        }

        // Create modal dialog for chat selection
        const modal = document.createElement('div');
        modal.className = 'modal fade show';
        modal.style.display = 'block';
        modal.innerHTML = `
            <div class="modal-dialog">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">Load Saved Chat</h5>
                        <button type="button" class="btn-close" onclick="this.closest('.modal').remove()"></button>
                    </div>
                    <div class="modal-body">
                        <div class="list-group">
                            ${chats.map(chat => `
                                <button class="list-group-item list-group-item-action"
                                        onclick="loadChatFile('${chat.filename}')">
                                    ${chat.display_name}<br>
                                    <small class="text-muted">Modified: ${new Date(chat.modified).toLocaleString()}</small>
                                </button>
                            `).join('')}
                        </div>
                    </div>
                </div>
            </div>
        `;
        document.body.appendChild(modal);
    } catch (error) {
        alert(`Error loading chat list: ${error.message}`);
    }
}

async function loadChatFile(filename) {
    try {
        const response = await fetch(`/documents/load_chat/${filename}`);
        const data = await response.json();

        chatHistory = data.history;
        const chatBox = document.getElementById('chat-box');
        chatBox.innerHTML = '';

        // Re-render with proper indices
        chatHistory.forEach((msg, index) => {
            appendMessage(msg.content, msg.isUser, index);
        });

        // Remove modal
        document.querySelector('.modal').remove();
    } catch (error) {
        alert(`Error loading chat: ${error.message}`);
    }
}

async function exportToMd() {
    try {
        const data = {
            history: chatHistory,
            timestamp: new Date().toISOString()
        };

        const response = await fetch('/documents/export_chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
        }

        const result = await response.json();
        alert(`Chat exported successfully as: ${result.filename}`);
    } catch (error) {
        console.error('Export error:', error);
        alert(`Error exporting chat: ${error.message}`);
    }
}

async function retryLast() {
    if (!lastMessage) {
        alert('No message to retry!');
        return;
    }

    const currentProvider = document.getElementById('provider').value;
    const currentModel = document.getElementById('model').value;

    // Create modal for retry options
    const modal = document.createElement('div');
    modal.className = 'modal fade show';
    modal.style.display = 'block';
    modal.innerHTML = `
        <div class="modal-dialog">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title">Retry Options</h5>
                    <button type="button" class="btn-close" onclick="this.closest('.modal').remove()"></button>
                </div>
                <div class="modal-body">
                    <div class="form-group mb-3">
                        <label>Current Configuration:</label>
                        <button class="btn btn-primary w-100" onclick="executeRetry('${currentProvider}', '${currentModel}', this)">
                            Retry with current provider (${currentProvider}) and model (${currentModel})
                        </button>
                    </div>

                    <div class="form-group mb-3">
                        <label>Change Provider:</label>
                        <select class="form-control mb-2" id="retry-provider-select" onchange="updateRetryModels()">
                            ${document.getElementById('provider').innerHTML}
                        </select>
                    </div>

                    <div class="form-group mb-3">
                        <label>Select Model:</label>
                        <select class="form-control mb-2" id="retry-model-select">
                            <option value="">Select Provider First</option>
                        </select>
                        <button class="btn btn-secondary w-100" onclick="executeRetry(null, null, this)">
                            Retry with selected provider and model
                        </button>
                    </div>
                </div>
            </div>
        </div>
    `;
    document.body.appendChild(modal);

    // Set current provider and trigger model load
    document.getElementById('retry-provider-select').value = currentProvider;
    await updateRetryModels();
}

async function updateRetryModels() {
    const providerSelect = document.getElementById('retry-provider-select');
    const modelSelect = document.getElementById('retry-model-select');
    const provider = providerSelect.value;

    if (!provider) {
        modelSelect.innerHTML = '<option value="">Select Provider First</option>';
        modelSelect.disabled = true;
        return;
    }

    modelSelect.innerHTML = '<option value="">Loading models...</option>';
    modelSelect.disabled = true;

    try {
        console.log(`Fetching retry models for provider: ${provider}`);
        const response = await fetch(`/get_models/${provider}`);

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        // Check if response is JSON
        const contentType = response.headers.get('content-type');
        if (!contentType || !contentType.includes('application/json')) {
            const text = await response.text();
            console.error('Non-JSON response received:', text);
            throw new Error('Server returned non-JSON response');
        }

        const data = await response.json();

        if (data.error) {
            throw new Error(`Server error: ${data.error}`);
        }

        const models = data.models;
        const defaultModel = data.default;

        modelSelect.innerHTML = '<option value="">Select Model</option>';

        if (Array.isArray(models) && models.length > 0) {
            models.sort().forEach(model => {
                const option = document.createElement('option');
                option.value = model;
                option.textContent = model;
                if (model === defaultModel) {
                    option.selected = true;
                }
                modelSelect.appendChild(option);
            });
            console.log(`Successfully loaded ${models.length} retry models for ${provider}`);
        } else {
            modelSelect.innerHTML = '<option value="">No models available</option>';
            console.warn(`No retry models available for provider: ${provider}`);
        }
        modelSelect.disabled = false;
    } catch (error) {
        console.error('Error fetching retry models:', error);
        modelSelect.innerHTML = '<option value="">Error loading models</option>';
        modelSelect.disabled = true;
    }
}

async function executeRetry(provider = null, model = null, buttonElement) {
    try {
        const modal = buttonElement.closest('.modal');
        const selectedProvider = provider || document.getElementById('retry-provider-select').value;
        const selectedModel = model || document.getElementById('retry-model-select').value;

        if (!selectedProvider || !selectedModel) {
            alert('Please select both provider and model');
            return;
        }

        console.log(`Retrying with ${selectedProvider}/${selectedModel}`);

        // Update provider first
        const providerSelect = document.getElementById('provider');
        providerSelect.value = selectedProvider;

        // Wait for models to load
        await updateModels();

        // Wait for DOM update
        await new Promise(resolve => setTimeout(resolve, 300));

        // Set model selection
        const modelSelect = document.getElementById('model');
        modelSelect.value = selectedModel;

        // Verify selections
        if (!modelSelect.value) {
            console.error('Model selection failed:', {
                provider: selectedProvider,
                model: selectedModel,
                availableModels: Array.from(modelSelect.options).map(opt => opt.value)
            });
            throw new Error('Failed to set model selection');
        }

        modal.remove();

        // Add user message to chat showing retry
        appendMessage(`[Retrying previous prompt with ${selectedProvider}/${selectedModel}]`, true);

        // Rerun the message
        await sendMessage(lastMessage, true);
    } catch (error) {
        console.error('Retry error:', error);
        alert(`Error during retry: ${error.message}`);
    }
}

function provideFeedback(isPositive) {
    if (chatHistory.length > 0) {
        const lastEntry = chatHistory[chatHistory.length - 1];
        lastEntry.feedback = isPositive;
    }
    showFeedback(false);
    alert(`Thank you for your ${isPositive ? 'positive' : 'negative'} feedback!`);
}

async function updateModelsFromProvider() {
    const provider = document.getElementById('provider').value;
    const modelSelect = document.getElementById('model');

    if (!provider) {
        alert('Please select a provider first');
        return;
    }

    const updateBtn = document.getElementById('update-models-btn');
    const originalText = updateBtn.innerHTML;

    try {
        // Show loading state
        updateBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Updating...';
        updateBtn.disabled = true;

        // Also show loading in dropdown
        modelSelect.innerHTML = '<option value="">Updating models...</option>';
        modelSelect.disabled = true;

        const response = await fetch(`/update_models/${provider}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });

        if (!response.ok) {
            // Handle HTTP errors with detailed messages
            const errorData = await response.json();
            throw new Error(JSON.stringify(errorData.detail || errorData));
        }

        const data = await response.json();

        if (data.success) {
            // Directly populate the dropdown with the updated models
            const models = data.models;
            const defaultModel = data.default;

            modelSelect.innerHTML = '<option value="">Select Model</option>';

            if (Array.isArray(models) && models.length > 0) {
                models.sort().forEach(model => {
                    const option = document.createElement('option');
                    option.value = model;
                    option.textContent = model;
                    if (model === defaultModel) {
                        option.selected = true;
                    }
                    modelSelect.appendChild(option);
                });
                modelSelect.disabled = false;

                // Update the display
                updateProviderModelDisplay();

                // Enhanced success message with more details
                let successMessage = `✅ ${data.message}\n\n` +
                    `📊 Found ${data.count} total models`;

                if (data.has_preview_models) {
                    successMessage += `\n🔬 Preview models: ${data.preview_count}` +
                        `\n✅ Stable models: ${data.stable_count}`;
                }

                successMessage += `\n📡 Source: ${data.data_source}`;

                if (data.preview_models && data.preview_models.length > 0) {
                    successMessage += `\n\n🔬 Preview models include:\n${data.preview_models.slice(0, 3).join(', ')}${data.preview_models.length > 3 ? '...' : ''}`;
                }

                successMessage += `\n\n📋 First few models:\n${models.slice(0, 5).join(', ')}${models.length > 5 ? '...' : ''}`;

                alert(successMessage);
            } else {
                modelSelect.innerHTML = '<option value="">No models available</option>';
                modelSelect.disabled = true;
                alert(`⚠️ No models found for ${provider}`);
            }
        } else {
            throw new Error(data.error || 'Failed to update models');
        }
    } catch (error) {
        console.error('Model update error:', error);

        // Restore previous models if available
        try {
            await updateModels();
        } catch (restoreError) {
            modelSelect.innerHTML = '<option value="">Error loading models</option>';
            modelSelect.disabled = true;
        }

        // Extract detailed error message from backend response
        let errorMessage = 'Failed to update models';
        if (error.message) {
            // Try to parse the error message if it's JSON
            try {
                const errorDetail = JSON.parse(error.message);
                if (errorDetail.error) {
                    errorMessage = errorDetail.error;
                    if (errorDetail.solution) {
                        errorMessage += `\n\n💡 Solution: ${errorDetail.solution}`;
                    }
                } else {
                    errorMessage = error.message;
                }
            } catch {
                errorMessage = error.message;
            }
        }
        alert(`❌ Error updating models: ${errorMessage}`);
    } finally {
        // Restore button state
        updateBtn.innerHTML = originalText;
        updateBtn.disabled = false;
    }
}

async function setDefaultModel() {
    const provider = document.getElementById('provider').value;
    const model = document.getElementById('model').value;

    if (!provider) {
        alert('Please select a provider first');
        return;
    }

    if (!model) {
        alert('Please select a model first');
        return;
    }

    const setDefaultBtn = document.getElementById('set-default-btn');
    const originalText = setDefaultBtn.innerHTML;

    try {
        // Show loading state
        setDefaultBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Setting...';
        setDefaultBtn.disabled = true;

        const response = await fetch(`/set_default_model/${provider}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ model: model })
        });

        const data = await response.json();

        if (data.success) {
            alert(`✅ ${data.message}\n\nDefault model for ${provider} is now: ${model}`);
        } else {
            throw new Error(data.error || 'Failed to set default model');
        }
    } catch (error) {
        console.error('Set default model error:', error);
        alert(`❌ Error setting default model: ${error.message}`);
    } finally {
        // Restore button state
        setDefaultBtn.innerHTML = originalText;
        setDefaultBtn.disabled = false;
    }
}


const sendMessage = debounce(async (message = null, isRetry = false) => {
    try {
        const userInput = document.getElementById('user-input');

        const provider = document.getElementById('provider').value;
        const model = document.getElementById('model').value;
        let persona = document.getElementById('persona').value;
        if (persona === 'custom') {
            persona = document.getElementById('custom-persona-textarea').value.trim();
        }

        // Get slider values
        const maxTokens = document.getElementById('max-tokens')?.value || 4000;
        const temperature = document.getElementById('temperature')?.value || 0.7;

        // Get selected output language
        const languageSelect = document.getElementById('voice-language');
        const selectedLanguage = languageSelect ? languageSelect.value : 'en';

        const messageToSend = message || userInput.value.trim();

        if (!messageToSend || !provider || !model) {
            throw new Error('Please fill in all fields');
        }

        // Only clear input and add user message if not a retry
        if (!isRetry) {
            const userMessageIndex = chatHistory.length;
            appendMessage(messageToSend, true, userMessageIndex);
            userInput.value = '';

            // Add user message to chat history immediately
            chatHistory.push({
                content: messageToSend,
                isUser: true,
                timestamp: new Date().toISOString()
            });
        }

        showInputProgress();
        showFeedback(false);

        console.log('Sending message:', { provider, model, message: messageToSend, maxTokens, temperature });

        // Search for relevant context
        const contextResponse = await fetch('/search_context', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: messageToSend })
        });

        if (contextResponse.ok) {
            const contextData = await contextResponse.json();
            if (contextData.results && contextData.results.length > 0) {
                // Add visual indicator that context is being used
                appendMessage('Using context from uploaded files...', false);
            }
        }

        // Add timeout to fetch
        const controller = new AbortController();
        const timeout = setTimeout(() => controller.abort(), 65000); // 65s timeout

        const response = await fetch('/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                message: messageToSend,
                provider: provider,
                model: model,
                persona: persona,
                max_tokens: parseInt(maxTokens),
                temperature: parseFloat(temperature),
                output_language: selectedLanguage
            }),
            signal: controller.signal
        });

        clearTimeout(timeout);

        let text = await response.text();
        let data = null;
        try {
            data = JSON.parse(text);
        } catch (jsonErr) {
            // Not valid JSON, show as error
            appendMessage(`Error: ${text || 'Unknown error from server.'}`, false);
            hideInputProgress();
            return;
        }

        if (!response.ok) {
            throw new Error(data.error || `HTTP error! status: ${response.status}`);
        }

        if (data && data.response) {
            const aiMessageIndex = chatHistory.length;
            // Merge verification into response for badge logic
            let aiMessage = data.response;
            if (data.verification) {
                aiMessage = { ...aiMessage, verification: data.verification };
            }
            appendMessage(aiMessage, false, aiMessageIndex);
            if (aiMessage.text) {
                lastAiResponse = aiMessage.text;
                lastAiResponseText = aiMessage.text; // Store for copy function
                // Show copy button
                document.getElementById('copy-response-btn')?.classList.remove('d-none');

                // Auto-speak if enabled
                const autoSpeak = document.getElementById('auto-speak');
                if (autoSpeak && autoSpeak.checked) {
                    // Small delay to ensure message is displayed first
                    setTimeout(() => {
                        speakText(aiMessage.text);
                    }, 500);
                }
            }
            lastMessage = messageToSend;

            // Add AI response to chat history
            chatHistory.push({
                content: aiMessage.text || aiMessage, // Store only the text content
                isUser: false,
                timestamp: new Date().toISOString()
            });

            showFeedback(true);
        } else {
            throw new Error('Invalid response from server');
        }
    } catch (error) {
        console.error('Send message error:', error);
        const errorMessage = error.name === 'AbortError'
            ? 'Request timed out. The server is taking too long to respond.'
            : `Error: ${error.message}`;
        appendMessage(errorMessage, false);
    } finally {
        hideInputProgress();
    }
}, 250);

// Add enter key listener for input
document.getElementById('user-input').addEventListener('keypress', function (event) {
    if (event.key === 'Enter') {
        sendMessage();
    }
});

// Initialize by triggering model load for default provider
document.addEventListener('DOMContentLoaded', function () {
    // Set CEREBRAS as default provider
    const providerSelect = document.getElementById('provider');
    providerSelect.value = 'cerebras';

    // Initialize audio and trigger model load
    initializeAudio();
    providerSelect.dispatchEvent(new Event('change'));
});

// Audio recording variables
let mediaRecorder = null;
let audioChunks = [];
let isRecording = false;

// Speech recognition (browser-based)
let speechRecognition = null;
let isListening = false;

// Speech synthesis
const speechSynthesis = window.speechSynthesis;
let isSpeaking = false;

// Update speech synthesis variables
let selectedVoice = null;
let voiceRate = 1.0;
let voicePitch = 1.0;

async function initializeAudio() {
    try {
        // Initialize browser-based speech recognition
        if ('webkitSpeechRecognition' in window) {
            speechRecognition = new webkitSpeechRecognition();
        } else if ('SpeechRecognition' in window) {
            speechRecognition = new SpeechRecognition();
        }

        if (speechRecognition) {
            speechRecognition.continuous = false;
            speechRecognition.interimResults = false;
            speechRecognition.lang = 'en-US';

            speechRecognition.onresult = (event) => {
                const transcript = event.results[0][0].transcript;
                document.getElementById('user-input').value = transcript;
                console.log('Speech recognition result:', transcript);
                // Visual feedback
                const input = document.getElementById('user-input');
                input.style.backgroundColor = '#e8f5e8';
                setTimeout(() => {
                    input.style.backgroundColor = '';
                }, 1000);
            };

            speechRecognition.onerror = (event) => {
                console.error('Speech recognition error:', event.error);
                let errorMessage = 'Speech recognition error. Please try again.';
                if (event.error === 'not-allowed') {
                    errorMessage = 'Microphone access denied. Please enable microphone permissions.';
                } else if (event.error === 'no-speech') {
                    errorMessage = 'No speech detected. Please try speaking again.';
                } else if (event.error === 'network') {
                    errorMessage = 'Network error. Please check your internet connection.';
                }
                alert(errorMessage);
                isListening = false;
                updateRecordButton();
            };

            speechRecognition.onstart = () => {
                console.log('Speech recognition started');
                const input = document.getElementById('user-input');
                input.placeholder = 'Listening... Speak now';
                input.style.borderColor = '#007bff';
            };

            speechRecognition.onend = () => {
                isListening = false;
                updateRecordButton();
                const input = document.getElementById('user-input');
                input.placeholder = 'Type your message...';
                input.style.borderColor = '';
            };

            console.log('Browser speech recognition initialized');
        }

        // Try to initialize media recorder as fallback
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            mediaRecorder = new MediaRecorder(stream);

            mediaRecorder.ondataavailable = (event) => {
                audioChunks.push(event.data);
            };

            mediaRecorder.onstop = async () => {
                const audioBlob = new Blob(audioChunks, { type: 'audio/wav' });
                try {
                    await transcribeAudio(audioBlob);
                } catch (error) {
                    console.error('Error transcribing audio:', error);
                    alert('Error transcribing audio. Please try again.');
                } finally {
                    audioChunks = [];
                }
            };

            console.log('Media recorder initialized as fallback');
        } catch (error) {
            console.warn('Media recorder initialization failed:', error);
        }

        // If neither method is available, hide the button
        if (!speechRecognition && !mediaRecorder) {
            document.getElementById('record-button').style.display = 'none';
            console.warn('No speech recognition methods available');
        }

    } catch (error) {
        console.error('Error initializing audio:', error);
        document.getElementById('record-button').style.display = 'none';
        alert('Failed to initialize audio. Please check your microphone permissions.');
    }
}

function toggleRecording() {
    // Try browser-based speech recognition first
    if (speechRecognition && !isListening) {
        isListening = true;
        updateRecordButton();
        try {
            speechRecognition.start();
            console.log('Started browser speech recognition');
        } catch (error) {
            console.error('Failed to start speech recognition:', error);
            isListening = false;
            updateRecordButton();
            // Fallback to media recorder
            if (mediaRecorder) {
                startMediaRecording();
            } else {
                alert('Speech recognition not available');
            }
        }
        return;
    }

    // Stop listening if currently active
    if (isListening) {
        speechRecognition?.stop();
        isListening = false;
        updateRecordButton();
        return;
    }

    // Fallback to media recorder
    if (mediaRecorder) {
        startMediaRecording();
    } else {
        alert('Microphone access not initialized');
    }
}

function startMediaRecording() {
    if (!mediaRecorder) {
        alert('Media recorder not available');
        return;
    }

    if (isRecording) {
        mediaRecorder.stop();
        isRecording = false;
    } else {
        audioChunks = [];
        mediaRecorder.start();
        isRecording = true;
    }
    updateRecordButton();
}

function updateRecordButton() {
    const recordButton = document.getElementById('record-button');
    if (isListening || isRecording) {
        recordButton.innerHTML = '<i class="fas fa-stop"></i>';
        recordButton.classList.remove('btn-primary');
        recordButton.classList.add('btn-danger');
        recordButton.title = 'Stop recording';
    } else {
        recordButton.innerHTML = '<i class="fas fa-microphone"></i>';
        recordButton.classList.remove('btn-danger');
        recordButton.classList.add('btn-primary');
        recordButton.title = 'Start voice input';
    }
}

async function transcribeAudio(audioBlob) {
    const formData = new FormData();
    formData.append('audio', audioBlob);

    try {
        const response = await fetch('/transcribe', {
            method: 'POST',
            body: formData
        });
        const data = await response.json();

        if (response.ok) {
            if (data.text) {
                document.getElementById('user-input').value = data.text;
            } else {
                throw new Error('No text received from transcription');
            }
        } else {
            throw new Error(data.error || 'Transcription failed');
        }
    } catch (error) {
        console.error('Error transcribing audio:', error);
        alert(`Error transcribing audio: ${error.message}`);
    }
}

function updateVoiceList() {
    const voiceSelect = document.getElementById('voice-select');
    const genderSelect = document.getElementById('voice-gender');
    const voices = speechSynthesis.getVoices();
    console.log('Available voices from browser:', voices); // Log all available voices
    const selectedGender = genderSelect.value;

    // Get selected output language
    const languageSelect = document.getElementById('voice-language');
    const selectedLanguage = languageSelect ? languageSelect.value : 'en';

    // Filter voices by language and gender
    const filteredVoices = voices.filter(voice => {
        // US English voices
        const isUSEnglish = voice.lang === 'en-US';
        // All English voices
        const isEnglish = voice.lang.startsWith('en-') || voice.lang === 'en';
        // Tamil/Hindi voices
        const isTamil = voice.lang.startsWith('ta') || voice.lang === 'ta';
        const isHindi = voice.lang.startsWith('hi') || voice.lang === 'hi';

        let langMatch = false;
        if (selectedLanguage === 'en') langMatch = isEnglish;
        else if (selectedLanguage === 'ta') langMatch = isTamil;
        else if (selectedLanguage === 'hi') langMatch = isHindi;
        else langMatch = voice.lang.startsWith(selectedLanguage);

        if (selectedGender === 'all') return langMatch || isUSEnglish;
        // Simple gender detection based on voice name
        const isFemale = voice.name.toLowerCase().includes('female') ||
            voice.name.toLowerCase().includes('woman');
        const isMale = voice.name.toLowerCase().includes('male') ||
            voice.name.toLowerCase().includes('man');
        return (langMatch || isUSEnglish) && (
            (selectedGender === 'female' && isFemale) ||
            (selectedGender === 'male' && isMale)
        );
    });

    voiceSelect.innerHTML = '';
    filteredVoices.forEach(voice => {
        const option = document.createElement('option');
        option.value = voice.name;
        option.textContent = `${voice.name} (${voice.lang})`;
        if (voice.default) {
            option.selected = true;
            selectedVoice = voice;
        }
        voiceSelect.appendChild(option);
    });

    // Sort by name
    const options = Array.from(voiceSelect.options);
    options.sort((a, b) => a.text.localeCompare(b.text));
    voiceSelect.innerHTML = '';
    options.forEach(option => voiceSelect.appendChild(option));
}

function toggleVoiceSettings() {
    const content = document.getElementById('voice-settings');
    const icon = document.querySelector('.settings-header i');

    content.classList.toggle('collapsed');
    icon.classList.toggle('rotated');
}

// Initialize voice controls with state persistence
function initializeVoiceControls() {
    const voiceSelect = document.getElementById('voice-select');
    const genderSelect = document.getElementById('voice-gender');
    const rateInput = document.getElementById('voice-rate');
    const pitchInput = document.getElementById('voice-pitch');
    const rateValue = document.getElementById('voice-rate-value');
    const pitchValue = document.getElementById('voice-pitch-value');
    const autoSpeakCheckbox = document.getElementById('auto-speak');

    // Load saved settings
    const savedSettings = JSON.parse(localStorage.getItem('voiceSettings') || '{}');
    voiceRate = savedSettings.rate || 1.0;
    voicePitch = savedSettings.pitch || 1.0;
    const savedGender = savedSettings.gender || 'all';
    const autoSpeakEnabled = savedSettings.autoSpeak !== false; // Default to true

    // Update UI with saved settings
    rateInput.value = voiceRate;
    pitchInput.value = voicePitch;
    rateValue.textContent = `${voiceRate.toFixed(1)}x`;
    pitchValue.textContent = `${voicePitch.toFixed(1)}x`;
    genderSelect.value = savedGender;
    autoSpeakCheckbox.checked = autoSpeakEnabled;

    // Event listeners
    autoSpeakCheckbox.addEventListener('change', (e) => {
        const updatedSettings = JSON.parse(localStorage.getItem('voiceSettings') || '{}');
        updatedSettings.autoSpeak = e.target.checked;
        localStorage.setItem('voiceSettings', JSON.stringify(updatedSettings));
    });
    genderSelect.addEventListener('change', (e) => {
        const gender = e.target.value;
        localStorage.setItem('voiceSettings', JSON.stringify({
            ...savedSettings,
            gender: gender
        }));
        updateVoiceList(); // Refresh voice list with gender filter
    });

    voiceSelect.addEventListener('change', (e) => {
        const voices = speechSynthesis.getVoices();
        selectedVoice = voices.find(voice => voice.name === e.target.value);
        localStorage.setItem('voiceSettings', JSON.stringify({
            ...savedSettings,
            voice: selectedVoice?.name
        }));
    });

    rateInput.addEventListener('input', (e) => {
        voiceRate = parseFloat(e.target.value);
        rateValue.textContent = `${voiceRate.toFixed(1)}x`;
        localStorage.setItem('voiceSettings', JSON.stringify({
            ...savedSettings,
            rate: voiceRate
        }));
    });

    pitchInput.addEventListener('input', (e) => {
        voicePitch = parseFloat(e.target.value);
        pitchValue.textContent = `${voicePitch.toFixed(1)}x`;
        localStorage.setItem('voiceSettings', JSON.stringify({
            ...savedSettings,
            pitch: voicePitch
        }));
    });

    updateVoiceList();
    speechSynthesis.onvoiceschanged = updateVoiceList;
}

function cleanTextForSpeech(text) {
    return text
        // Remove code blocks
        .replace(/```[\s\S]*?```/g, 'code block omitted')
        // Remove inline code
        .replace(/`.*?`/g, '')
        // Remove URLs
        .replace(/https?:\/\/\S+/g, 'URL omitted')
        // Remove markdown links
        .replace(/\[([^\]]+)\]\([^\)]+\)/g, '$1')
        // Remove headers
        .replace(/#+\s/g, '')
        // Remove bold/italic markers
        .replace(/[\*_]{1,2}([^\*_]+)[\*_]{1,2}/g, '$1')
        // Remove list markers
        .replace(/^[-*+]\s/gm, '')
        // Remove numbered lists
        .replace(/^\d+\.\s/gm, '')
        // Add pauses at punctuation
        .replace(/([.!?])\s+/g, '$1, ')
        // Clean up multiple spaces
        .replace(/\s+/g, ' ')
        .trim();
}

function speakText(text) {
    // If no text provided, use the last AI response
    if (!text && lastAiResponseText) {
        text = lastAiResponseText;
    }

    if (!text) {
        alert('No text to speak. Please send a message first.');
        return;
    }

    if (isSpeaking) {
        speechSynthesis.cancel();
        isSpeaking = false;
        updateSpeakButton();
        return;
    }

    const cleanText = cleanTextForSpeech(text);

    if (!cleanText || cleanText.trim().length === 0) {
        alert('No readable text found.');
        return;
    }

    // Get selected output language
    const languageSelect = document.getElementById('voice-language');
    const selectedLanguage = languageSelect ? languageSelect.value : 'en';

    // Split text into sentences for better handling
    const sentences = cleanText.match(/[^.!?]+[.!?]+/g) || [cleanText];
    let currentSentence = 0;

    function speakNextSentence() {
        if (currentSentence >= sentences.length || !isSpeaking) {
            isSpeaking = false;
            updateSpeakButton();
            return;
        }

        const utterance = new SpeechSynthesisUtterance(sentences[currentSentence]);

        // Apply voice settings
        if (selectedVoice) utterance.voice = selectedVoice;
        utterance.rate = voiceRate;
        utterance.pitch = voicePitch;
        utterance.volume = 1.0;
        utterance.lang = selectedLanguage;

        utterance.onend = () => {
            currentSentence++;
            speakNextSentence();
        };

        utterance.onerror = (event) => {
            console.error('Speech synthesis error:', event);
            isSpeaking = false;
            updateSpeakButton();
            alert('Text-to-speech error. Please try again.');
        };

        try {
            speechSynthesis.speak(utterance);
        } catch (error) {
            console.error('Speech synthesis failed:', error);
            alert('Text-to-speech failed. Please check your browser settings.');
            isSpeaking = false;
            updateSpeakButton();
        }
    }

    try {
        isSpeaking = true;
        updateSpeakButton();
        speakNextSentence();
    } catch (error) {
        console.error('Speech synthesis initialization failed:', error);
        alert('Text-to-speech initialization failed. Please check your browser settings.');
        isSpeaking = false;
        updateSpeakButton();
    }
}

// Add speech synthesis resume functionality
setInterval(() => {
    if (isSpeaking && !speechSynthesis.speaking) {
        speechSynthesis.resume();
    }
}, 250);

function updateSpeakButton() {
    const speakButton = document.getElementById('speak-button');
    if (isSpeaking) {
        speakButton.innerHTML = '<i class="fas fa-volume-mute"></i>';
        speakButton.classList.remove('btn-primary');
        speakButton.classList.add('btn-danger');
        speakButton.title = 'Stop speaking';
    } else {
        speakButton.innerHTML = '<i class="fas fa-volume-up"></i>';
        speakButton.classList.remove('btn-danger');
        speakButton.classList.add('btn-primary');
        speakButton.title = 'Speak response';
    }
}

// Ensure voices are loaded
speechSynthesis.onvoiceschanged = () => {
    console.log('Voices loaded:', speechSynthesis.getVoices().length);
};

// Initialize audio on page load
document.addEventListener('DOMContentLoaded', function () {
    initializeAudio();
    initializeVoiceControls();
    document.getElementById('provider').dispatchEvent(new Event('change'));
});

// Use IntersectionObserver for chat scroll
const scrollObserver = new IntersectionObserver(
    (entries) => {
        entries.forEach(entry => {
            if (!entry.isIntersecting) {
                entry.target.scrollIntoView({ behavior: 'smooth' });
            }
        });
    },
    { threshold: 0.1 }
);

function initializeSidebar() {
    const headers = document.querySelectorAll('.settings-header');

    headers.forEach(header => {
        const content = header.nextElementSibling;
        const icon = header.querySelector('.fa-chevron-down');
        const isActions = header.getAttribute('data-section') === 'actions';

        // Set initial state - expanded for actions, collapsed for others
        if (isActions) {
            content.style.display = 'block';
            content.classList.add('expanded');
            header.classList.add('active');
            icon.style.transform = 'rotate(180deg)';
        } else {
            content.style.display = 'none';
            content.classList.remove('expanded');
            header.classList.remove('active');
        }

        header.addEventListener('click', () => {
            // Close all other sections
            headers.forEach(h => {
                if (h !== header) {
                    const c = h.nextElementSibling;
                    h.classList.remove('active');
                    c.classList.remove('expanded');
                    // Smooth collapse
                    c.style.display = 'none';
                }
            });

            // Toggle current section
            const isExpanding = !content.classList.contains('expanded');

            if (isExpanding) {
                content.style.display = 'block';
                // Force reflow for animation
                content.offsetHeight;
                content.classList.add('expanded');
                header.classList.add('active');
            } else {
                content.classList.remove('expanded');
                header.classList.remove('active');
                // Wait for animation before hiding
                setTimeout(() => {
                    if (!content.classList.contains('expanded')) {
                        content.style.display = 'none';
                    }
                }, 300);
            }

            // Update icon rotation
            icon.style.transform = isExpanding ? 'rotate(180deg)' : 'rotate(0deg)';
        });
    });
}

// Initialize with smooth transitions
document.addEventListener('DOMContentLoaded', () => {
    // Remove old event listeners
    document.querySelectorAll('.settings-header').forEach(header => {
        const clone = header.cloneNode(true);
        header.parentNode.replaceChild(clone, header);
    });

    initializeSidebar();

    // Add initial transition delay for staggered animation
    document.querySelectorAll('.settings-group').forEach((group, index) => {
        group.style.transitionDelay = `${index * 50}ms`;
    });
});

function handleDragOver(event) {
    event.preventDefault();
    event.stopPropagation();
    event.currentTarget.classList.add('drag-over');
}

function handleDragLeave(event) {
    event.preventDefault();
    event.stopPropagation();
    event.currentTarget.classList.remove('drag-over');
}

function handleFileDrop(event) {
    event.preventDefault();
    event.stopPropagation();

    const dropzone = event.currentTarget;
    dropzone.classList.remove('drag-over');

    const files = event.dataTransfer.files;
    if (files.length > 0) {
        updateFileInput(files);
    }
}

function updateFileInput(files) {
    const fileInput = document.getElementById('file-input');
    // Update file input
    const dt = new DataTransfer();
    Array.from(files).forEach(file => {
        dt.items.add(file);
    });
    fileInput.files = dt.files;
}

// Listen for file input changes
document.getElementById('file-input').addEventListener('change', function () {
    if (this.files.length > 0) {
        uploadFiles();
    }
});

async function uploadFiles() {
    const fileInput = document.getElementById('file-input');
    if (!fileInput.files.length) return;

    try {
        const formData = new FormData();
        Array.from(fileInput.files).forEach(file => {
            formData.append('files[]', file);
            appendMessage(`Uploading file: ${file.name}...`, false);
        });

        const xhr = new XMLHttpRequest();

        // Track upload progress (optional: implement a progress bar if desired)
        // xhr.upload.onprogress = (event) => { ... };

        // Handle completion
        xhr.onload = async () => {
            if (xhr.status === 200) {
                const result = JSON.parse(xhr.responseText);
                if (result.results && Array.isArray(result.results)) {
                    for (const f of result.results) {
                        if (f.status === 'success') {
                            appendMessage(`File uploaded: ${f.filename}`, false);
                            // Fetch and display a snippet of the extracted text
                            try {
                                const resp = await fetch(`/documents/view/${encodeURIComponent(f.filename)}`);
                                if (resp.ok) {
                                    const doc = await resp.json();
                                    if (doc.preview) {
                                        const maxPreview = 1000;
                                        const isLong = doc.preview.length > maxPreview;
                                        const shortText = doc.preview.substring(0, maxPreview);
                                        const fullText = doc.preview;
                                        const msgId = `doc-preview-${Date.now()}-${Math.floor(Math.random() * 10000)}`;
                                        let html = `<div id="${msgId}">`;
                                        html += `<strong>Extracted text from ${f.filename}:</strong><br><pre style='white-space:pre-wrap;word-break:break-word;max-height:320px;overflow:auto;'>`;
                                        html += isLong ? shortText + '...' : shortText;
                                        html += '</pre>';
                                        if (isLong) {
                                            html += `<button class='btn btn-link btn-sm' style='padding:0;margin-top:-0.5em;' onclick="toggleDocPreview('${msgId}', this, \`${fullText.replace(/`/g, '\`').replace(/\\/g, '\\\\').replace(/'/g, "\\'").replace(/\n/g, '\\n')}\`, \`${shortText.replace(/`/g, '\`').replace(/\\/g, '\\\\').replace(/'/g, "\\'").replace(/\n/g, '\\n')}\`)">Show more</button>`;
                                        }
                                        html += '</div>';
                                        appendMessage(html, false, true);
                                    }
                                    // Toggle function for document preview expansion
                                    function toggleDocPreview(msgId, btn, fullText, shortText) {
                                        const container = document.getElementById(msgId);
                                        if (!container) return;
                                        const pre = container.querySelector('pre');
                                        if (!pre) return;
                                        if (btn.textContent === 'Show more') {
                                            pre.textContent = fullText;
                                            btn.textContent = 'Show less';
                                        } else {
                                            pre.textContent = shortText + '...';
                                            btn.textContent = 'Show more';
                                        }
                                    }
                                }
                            } catch (e) {
                                appendMessage(`(Could not fetch extracted text for ${f.filename})`, false);
                            }
                        } else {
                            appendMessage(`Upload failed: ${f.filename} (${f.error || 'Unknown error'})`, false);
                        }
                    }
                }
                if (result.results?.some(f => f.status === 'success')) {
                    showNotification('Files uploaded successfully', 'success');
                    // Show audio settings section below upload
                    const voiceSettings = document.getElementById('voice-settings');
                    if (voiceSettings) {
                        voiceSettings.parentElement.classList.add('expanded');
                        voiceSettings.style.maxHeight = '500px';
                        voiceSettings.style.opacity = '1';
                        voiceSettings.scrollIntoView({ behavior: 'smooth', block: 'center' });
                    }
                }
            } else {
                appendMessage('Upload failed: Server error', false);
                throw new Error(xhr.status === 413 ? 'Files too large' : 'Upload failed');
            }

            // Reset UI
            fileInput.value = '';
        };

        // Handle errors
        xhr.onerror = () => {
            appendMessage('Upload failed: Network error', false);
            showNotification('Upload failed', 'error');
        };

        // Send request
        xhr.open('POST', '/upload', true);
        xhr.send(formData);

    } catch (error) {
        appendMessage(`Upload failed: ${error.message}`, false);
        console.error('Upload error:', error);
        showNotification(error.message, 'error');
    }
}

function showNotification(message, type = 'info') {
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `alert alert-${type === 'error' ? 'danger' : type === 'success' ? 'success' : 'info'} notification-toast`;
    notification.innerHTML = `
        <div class="d-flex align-items-center">
            <i class="fas fa-${type === 'error' ? 'exclamation-circle' : type === 'success' ? 'check-circle' : 'info-circle'} me-2"></i>
            <span>${message}</span>
            <button type="button" class="btn-close ms-auto" onclick="this.parentElement.parentElement.remove()"></button>
        </div>
    `;

    // Add to page
    document.body.appendChild(notification);

    // Auto-remove after 5 seconds
    setTimeout(() => {
        if (notification.parentElement) {
            notification.remove();
        }
    }, 5000);
}

function createFileUploadItem(file) {
    const size = formatBytes(file.size);
    const ext = file.name.split('.').pop().toLowerCase();

    const item = document.createElement('div');
    item.className = 'file-upload-item mb-3';
    item.dataset.filename = file.name;

    item.innerHTML = `
        <div class="d-flex align-items-center">
            <i class="${getFileIcon(ext)} me-2"></i>
            <div class="flex-grow-1">
                <div class="d-flex justify-content-between align-items-center">
                    <span class="filename">${file.name}</span>
                    <span class="file-size text-muted">${size}</span>
                </div>
                <div class="progress mt-2" style="height: 3px;">
                    <div class="progress-bar progress-bar-striped progress-bar-animated"
                         role="progressbar" style="width: 0%"></div>
                </div>
                <div class="upload-status small text-muted mt-1">
                    <i class="fas fa-circle-notch fa-spin me-1"></i>
                    Preparing upload...
                </div>
            </div>
        </div>
    `;
    return item;
}

function updateUploadProgress(filename, progress) {
    const item = document.querySelector(`.file-upload-item[data-filename="${filename}"]`);
    if (!item) return;

    const progressBar = item.querySelector('.progress-bar');
    const statusText = item.querySelector('.upload-status');

    progressBar.style.width = `${progress}%`;
    statusText.innerHTML = `
        <i class="fas fa-circle-notch fa-spin me-1"></i>
        Uploading... ${progress}%
    `;
}

function updateUploadStatus(filename, status, message = '') {
    const item = document.querySelector(`.file-upload-item[data-filename="${filename}"]`);
    if (!item) return;

    const progressBar = item.querySelector('.progress-bar');
    const statusText = item.querySelector('.upload-status');

    progressBar.classList.remove('progress-bar-striped', 'progress-bar-animated');

    if (status === 'success') {
        progressBar.style.width = '100%';
        progressBar.className = 'progress-bar bg-success';
        statusText.className = 'upload-status small text-success mt-1';
        statusText.innerHTML = '<i class="fas fa-check-circle me-1"></i>Upload complete';
    } else {
        progressBar.style.width = '100%';
        progressBar.className = 'progress-bar bg-danger';
        statusText.className = 'upload-status small text-danger mt-1';
        statusText.innerHTML = `<i class="fas fa-exclamation-circle me-1"></i>${message}`;
    }
}

async function monitorFileProcessing(file, fileItem, isRetry = false) {
    const maxAttempts = 100;
    let attempts = 0;

    while (attempts < maxAttempts) {
        try {
            const response = await fetch(`/upload/status/${file.name}`);
            const data = await response.json();

            if (response.ok) {
                updateFileItemProgress(fileItem, data.progress);
                updateFileItemStatus(fileItem, data.status);

                if (data.status === 'Complete' || (!data.recoverable && data.error)) {
                    if (data.error) {
                        throw new Error(data.error);
                    }
                    break;
                }
            } else {
                throw new Error('Status check failed');
            }

            await new Promise(resolve => setTimeout(resolve, 500));
            attempts++;

        } catch (error) {
            if (!isRetry && fileItem.querySelector('.retry-button')) {
                break;
            }
            throw error;
        }
    }
}

function openFileList() {
    const modal = document.getElementById('fileListModal');
    modal.style.display = 'block';
    startFileListUpdates();
}

function closeFileList() {
    const modal = document.getElementById('fileListModal');
    modal.style.display = 'none';
    stopFileListUpdates();
}

async function updateDocumentsList() {
    try {
        const response = await fetch('/documents/list');
        if (!response.ok) {
            throw new Error(`Server returned ${response.status}`);
        }

        const data = await response.json();

        const fileList = document.getElementById('fileList');
        const filesCounter = document.querySelector('.files-counter');

        if (!fileList || !filesCounter) {
            console.error('File list elements not found');
            return;
        }

        // Update counter with better formatting
        const stats = data.stats || { total_documents: 0, total_size: 0 };
        filesCounter.textContent = `${stats.total_documents} files (${formatBytes(stats.total_size)})`;

        // Clear and update list
        fileList.innerHTML = '';

        if (data.documents && Array.isArray(data.documents)) {
            if (data.documents.length === 0) {
                fileList.innerHTML = '<div class="text-muted text-center p-3">No files uploaded yet</div>';
                return;
            }

            data.documents.forEach(doc => {
                const ext = doc.filename.split('.').pop().toLowerCase();
                const card = document.createElement('div');
                card.className = 'file-card';
                card.innerHTML = `
                    <div class="file-header">
                        <i class="${getFileIcon(ext)} file-icon"></i>
                        <div class="file-name">${doc.filename}</div>
                    </div>
                    <div class="file-meta">
                        ${formatBytes(doc.size)} •
                        ${new Date(doc.timestamp).toLocaleString()}
                    </div>
                    <div class="file-preview text-muted small mb-3">
                        ${doc.preview ? (doc.preview.substring(0, 100) + '...') : 'No preview available'}
                    </div>
                    <div class="file-actions">
                        <button class="btn btn-outline-primary btn-sm" onclick="viewFile('${doc.filename}')">
                            <i class="fas fa-eye me-1"></i>View
                        </button>
                        <button class="btn btn-outline-secondary btn-sm" onclick="useInChat('${doc.filename}')">
                            <i class="fas fa-paper-plane me-1"></i>Use
                        </button>
                    </div>
                `;
                fileList.appendChild(card);
            });
        } else {
            fileList.innerHTML = '<div class="text-muted text-center p-3">Error loading files</div>';
        }
    } catch (error) {
        console.error('Error updating documents list:', error);
        const fileList = document.getElementById('fileList');
        if (fileList) {
            fileList.innerHTML = `
                <div class="alert alert-danger m-3">
                    Error loading file list: ${error.message}
                </div>
            `;
        }
    }
}

// Update getFileIcon helper function
function getFileIcon(ext) {
    const icons = {
        pdf: 'fas fa-file-pdf',
        doc: 'fas fa-file-word',
        docx: 'fas fa-file-word',
        xls: 'fas fa-file-excel',
        xlsx: 'fas fa-file-excel',
        txt: 'fas fa-file-alt',
        md: 'fas fa-file-code',
        jpg: 'fas fa-file-image',
        jpeg: 'fas fa-file-image',
        png: 'fas fa-file-image',
        csv: 'fas fa-file-csv'
    };
    return icons[ext.toLowerCase()] || 'fas fa-file';
}

// Auto-update file list periodically
let fileListUpdateInterval;

function startFileListUpdates() {
    // Update initially
    updateDocumentsList();

    // Then update every 5 seconds
    fileListUpdateInterval = setInterval(updateDocumentsList, 5000);
}

function stopFileListUpdates() {
    if (fileListUpdateInterval) {
        clearInterval(fileListUpdateInterval);
    }
}

// Initialize document list on page load
document.addEventListener('DOMContentLoaded', () => {
    // ...existing init code...
    updateDocumentsList();

    // Add modal close handler
    window.onclick = function (event) {
        const modal = document.getElementById('fileListModal');
        if (event.target === modal) {
            closeFileList();
        }
    };
});

// Update viewFile function to work with modal
async function viewFile(filename) {
    try {
        const response = await fetch(`/documents/view/${filename}`);
        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || 'Failed to load file');
        }

        // Create preview modal
        const modal = document.createElement('div');
        modal.className = 'modal fade show';
        modal.style.display = 'block';
        modal.innerHTML = `
            <div class="modal-dialog modal-lg">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">
                            <i class="${getFileIcon(filename.split('.').pop())} me-2"></i>
                            ${filename}
                        </h5>
                        <button type="button" class="btn-close" onclick="this.closest('.modal').remove()"></button>
                    </div>
                    <div class="modal-body">
                        <div class="file-preview">
                            ${marked.parse(data.content)}
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button class="btn btn-secondary" onclick="this.closest('.modal').remove()">
                            Close
                        </button>
                        <button class="btn btn-primary" onclick="useInChat('${filename}')">
                            <i class="fas fa-paper-plane me-2"></i>Use in Chat
                        </button>
                    </div>
                </div>
            </div>
        `;
        document.body.appendChild(modal);

    } catch (error) {
        console.error('Error viewing file:', error);
        showNotification('Error viewing file: ' + error.message, 'error');
    }
}

async function useInChat(filename) {
    const userInput = document.getElementById('user-input');
    userInput.value = `Please analyze the content of the file "${filename}" and provide your insights.`;
    // Close modal if open
    document.querySelector('.modal')?.remove();
    // Send message
    await sendMessage();
}

function formatBytes(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

// Initialize document list on page load
document.addEventListener('DOMContentLoaded', () => {
    // ...existing init code...
    updateDocumentsList();
});

function handleFiles(files) {
    const preview = document.querySelector('.upload-preview');
    preview.innerHTML = '';

    Array.from(files).forEach(file => {
        const item = document.createElement('div');
        item.className = 'preview-item';

        if (file.type.startsWith('image/')) {
            const img = document.createElement('img');
            img.file = file;
            item.appendChild(img);

            const reader = new FileReader();
            reader.onload = (e) => { img.src = e.target.result; };
            reader.readAsDataURL(file);
        } else {
            const icon = document.createElement('i');
            icon.className = getFileIcon(file.name.split('.').pop());
            item.appendChild(icon);
        }

        const removeBtn = document.createElement('button');
        removeBtn.className = 'remove-file';
        removeBtn.innerHTML = '<i class="fas fa-times"></i>';
        removeBtn.onclick = (e) => {
            e.stopPropagation();
            item.remove();
            updateFileList();
        };

        item.appendChild(removeBtn);
        preview.appendChild(item);
    });
}

function updateFileList() {
    const preview = document.querySelector('.upload-preview');
    const input = document.getElementById('file-input');
    const newFiles = new DataTransfer();

    preview.querySelectorAll('.preview-item').forEach((item, index) => {
        if (input.files[index]) {
            newFiles.items.add(input.files[index]);
        }
    });

    input.files = newFiles.files;
}

function showUploadProgress(filename, progress) {
    const item = document.querySelector(`.file-upload-item[data-filename="${filename}"]`);
    if (!item) return;

    const progressBar = item.querySelector('.progress-bar');
    const status = item.querySelector('.upload-status');

    progressBar.style.width = `${progress}%`;
    if (progress === 100) {
        progressBar.classList.remove('progress-bar-animated');
        status.innerHTML = '<i class="fas fa-check text-success"></i> Complete';

        // Add to file list modal
        updateFileListModal(filename);
    }
}

function updateFileListModal(newFile) {
    const modal = document.getElementById('fileListModal');
    if (!modal.style.display === 'block') return;

    // Refresh file list
    updateDocumentsList();
}

// Enhanced drag and drop handling
document.querySelector('.upload-dropzone').addEventListener('dragover', (e) => {
    e.preventDefault();
    e.currentTarget.classList.add('drag-over');
});

document.querySelector('.upload-dropzone').addEventListener('dragleave', (e) => {
    e.preventDefault();
    e.currentTarget.classList.remove('drag-over');
});

document.querySelector('.upload-dropzone').addEventListener('drop', (e) => {
    e.preventDefault();
    e.currentTarget.classList.remove('drag-over');

    const files = e.dataTransfer.files;
    document.getElementById('file-input').files = files;
    handleFiles(files);
});

document.getElementById('file-input').addEventListener('change', function () {
    handleFiles(this.files);
});
