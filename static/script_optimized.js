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
    const newTheme = current === 'dark' ? 'light' : 'dark';
    setTheme(newTheme);
    saveSetting('theme', newTheme);
}

// Enhanced settings persistence system
const DEFAULT_SETTINGS = {
    provider: 'cerebras',
    model: '',
    persona: 'helpful_assistant',
    maxTokens: 4000,
    temperature: 0.7,
    theme: 'light'
};

// Load all settings from localStorage with defaults
function loadSettings() {
    const settings = {};
    for (const [key, defaultValue] of Object.entries(DEFAULT_SETTINGS)) {
        settings[key] = localStorage.getItem(`default${key.charAt(0).toUpperCase() + key.slice(1)}`) || defaultValue;
    }
    return settings;
}

// Save individual setting to localStorage
function saveSetting(key, value) {
    const storageKey = `default${key.charAt(0).toUpperCase() + key.slice(1)}`;
    localStorage.setItem(storageKey, value);
    console.log(`Saved setting: ${storageKey} = ${value}`);
}

// Reset all settings to defaults
function resetAllSettings() {
    if (confirm('Reset all settings to defaults? This will reload the page.')) {
        // Clear all default settings from localStorage
        Object.keys(DEFAULT_SETTINGS).forEach(key => {
            const storageKey = `default${key.charAt(0).toUpperCase() + key.slice(1)}`;
            localStorage.removeItem(storageKey);
        });

        // Show notification and reload
        showNotification('All settings reset to defaults!', 'success');
        setTimeout(() => location.reload(), 1000);
    }
}

// Apply settings to UI elements
function applySettings(settings) {
    // Set provider
    if (document.getElementById('provider')) {
        document.getElementById('provider').value = settings.provider;
    }

    // Set persona
    if (document.getElementById('persona')) {
        document.getElementById('persona').value = settings.persona;
    }

    // Set max tokens
    if (document.getElementById('max-tokens')) {
        document.getElementById('max-tokens').value = settings.maxTokens;
        const valueElement = document.getElementById('max-tokens-value');
        if (valueElement) valueElement.textContent = settings.maxTokens;
        updateSliderProgress(document.getElementById('max-tokens'));
    }

    // Set temperature
    if (document.getElementById('temperature')) {
        document.getElementById('temperature').value = settings.temperature;
        const valueElement = document.getElementById('temperature-value');
        if (valueElement) valueElement.textContent = parseFloat(settings.temperature).toFixed(1);
        updateSliderProgress(document.getElementById('temperature'));
    }

    // Set theme
    setTheme(settings.theme);
}

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

    // Truncate long model names for better display
    const truncateText = (text, maxLength = 15) => {
        return text.length > maxLength ? text.substring(0, maxLength) + '...' : text;
    };

    const displayProvider = truncateText(provider, 10);
    const displayModel = truncateText(model, 20);

    displayElement.innerHTML = `<strong>${displayProvider} | ${displayModel}</strong>`;
    displayElement.title = `${provider} | ${model}`; // Full text on hover
}

function updateSliderProgress(slider) {
    if (!slider) return;
    const value = ((slider.value - slider.min) / (slider.max - slider.min)) * 100;
    slider.style.setProperty('--range-progress', value + '%');
}

// Load personas from server
async function loadPersonas() {
    try {
        const response = await fetch('/get_personas');
        const data = await response.json();

        const personaSelect = document.getElementById('persona');
        if (personaSelect && data.personas) {
            // Clear existing options
            personaSelect.innerHTML = '';

            // Add personas
            data.personas.forEach(persona => {
                const option = document.createElement('option');
                option.value = persona.id;
                option.textContent = persona.name;
                personaSelect.appendChild(option);
            });

            // Add custom option
            const customOption = document.createElement('option');
            customOption.value = 'custom';
            customOption.textContent = 'Custom';
            personaSelect.appendChild(customOption);

            console.log(`Loaded ${data.personas.length} personas`);
        }
    } catch (error) {
        console.error('Error loading personas:', error);
    }
}

// Notification system
function showNotification(message, type = 'info', duration = 3000) {
    // Remove existing notifications
    const existingNotifications = document.querySelectorAll('.notification');
    existingNotifications.forEach(n => n.remove());

    // Create notification element
    const notification = document.createElement('div');
    notification.className = `notification alert alert-${type === 'error' ? 'danger' : type === 'success' ? 'success' : 'info'} alert-dismissible fade show`;
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        z-index: 9999;
        min-width: 300px;
        max-width: 500px;
    `;

    notification.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;

    document.body.appendChild(notification);

    // Auto-remove after duration
    setTimeout(() => {
        if (notification.parentNode) {
            notification.remove();
        }
    }, duration);
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

// SINGLE DOMContentLoaded event listener - consolidates all initialization
document.addEventListener('DOMContentLoaded', () => {
    console.log('Initializing TQ GenAI Chat...');

    // Load all settings
    const settings = loadSettings();

    // Load personas first
    loadPersonas().then(() => {
        // Apply settings to UI after personas are loaded
        applySettings(settings);

        // Handle persona change for custom textarea
        const personaSelect = document.getElementById('persona');
        if (personaSelect) {
            const handlePersonaChange = () => {
                saveSetting('persona', personaSelect.value);

                const customTextarea = document.getElementById('custom-persona-textarea');
                if (personaSelect.value === 'custom') {
                    customTextarea.classList.remove('d-none');
                } else {
                    customTextarea.classList.add('d-none');
                }
            };

            personaSelect.addEventListener('change', handlePersonaChange);
            // Trigger initial state
            handlePersonaChange();
        }
    });

    // Always refresh models on page load, then set saved model
    updateModels().then(() => {
        const savedModel = localStorage.getItem('defaultModel');
        if (savedModel && document.getElementById('model')) {
            document.getElementById('model').value = savedModel;
        }
        updateProviderModelDisplay();
    });

    // Set up event listeners for all form elements

    // Provider change
    const providerSelect = document.getElementById('provider');
    if (providerSelect) {
        providerSelect.addEventListener('change', () => {
            updateModels();
            saveSetting('provider', providerSelect.value);
            updateProviderModelDisplay();
        });
    }

    // Model change
    const modelSelect = document.getElementById('model');
    if (modelSelect) {
        modelSelect.addEventListener('change', () => {
            saveSetting('model', modelSelect.value);
            updateProviderModelDisplay();
        });
    }

    // Max tokens slider
    const maxTokensSlider = document.getElementById('max-tokens');
    if (maxTokensSlider) {
        maxTokensSlider.addEventListener('input', (e) => {
            const value = e.target.value;
            const valueElement = document.getElementById('max-tokens-value');
            if (valueElement) valueElement.textContent = value;
            updateSliderProgress(maxTokensSlider);
            saveSetting('maxTokens', value);
        });
        // Initialize slider progress
        updateSliderProgress(maxTokensSlider);
    }

    // Temperature slider
    const temperatureSlider = document.getElementById('temperature');
    if (temperatureSlider) {
        temperatureSlider.addEventListener('input', (e) => {
            const value = parseFloat(e.target.value).toFixed(1);
            const valueElement = document.getElementById('temperature-value');
            if (valueElement) valueElement.textContent = value;
            updateSliderProgress(temperatureSlider);
            saveSetting('temperature', value);
        });
        // Initialize slider progress
        updateSliderProgress(temperatureSlider);
    }

    // Update provider/model display initially
    updateProviderModelDisplay();

    console.log('TQ GenAI Chat initialized successfully');
});

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
}/
    / Chat functionality
let chatHistory = [];
let lastMessage = null;
let lastAiResponse = '';

function appendMessage(message, isUser = false, messageIndex = null) {
    const chatBox = document.getElementById('chat-box');
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${isUser ? 'user-message' : 'ai-message'}`;

    // Add message index as data attribute for editing
    if (messageIndex !== null) {
        messageDiv.setAttribute('data-message-index', messageIndex);
    }

    if (isUser) {
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
        lastAiResponseText = message.text;
    }
}

function showProcessing(show = true) {
    const processingElement = document.getElementById('processing');
    if (processingElement) {
        processingElement.classList.toggle('d-none', !show);
    }
}

function showFeedback(show = true) {
    const feedbackElement = document.getElementById('feedback');
    if (feedbackElement) {
        feedbackElement.classList.toggle('d-none', !show);
    }
}

async function sendMessage(message, isRetry = false) {
    if (!message.trim()) return;

    const provider = document.getElementById('provider').value;
    const model = document.getElementById('model').value;
    const persona = document.getElementById('persona').value;
    const customPersona = document.getElementById('custom-persona-textarea').value;
    const maxTokens = parseInt(document.getElementById('max-tokens').value);
    const temperature = parseFloat(document.getElementById('temperature').value);

    if (!provider || !model) {
        showNotification('Please select both provider and model', 'error');
        return;
    }

    // Store last message for retry functionality
    lastMessage = message;

    // Add user message to chat
    if (!isRetry) {
        appendMessage(message, true, chatHistory.length);
        chatHistory.push({ content: message, isUser: true });
    }

    // Show processing indicator
    showInputProgress();
    showProcessing(true);

    try {
        const requestData = {
            provider: provider,
            model: model,
            message: message,
            persona: persona === 'custom' ? customPersona : persona,
            temperature: temperature,
            max_tokens: maxTokens
        };

        const response = await fetch('/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(requestData)
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
        }

        const data = await response.json();

        if (data.error) {
            throw new Error(data.error);
        }

        // Add AI response to chat
        appendMessage(data, false, chatHistory.length);
        chatHistory.push({ content: data, isUser: false });

        // Show feedback buttons
        showFeedback(true);

    } catch (error) {
        console.error('Chat error:', error);
        appendMessage(`Error: ${error.message}`, false);
        showNotification(`Chat error: ${error.message}`, 'error');
    } finally {
        hideInputProgress();
        showProcessing(false);
    }
}

async function saveChat() {
    try {
        const data = {
            history: chatHistory,
            timestamp: new Date().toISOString()
        };

        const response = await fetch('/save_chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
        }

        const result = await response.json();
        showNotification(`Chat saved successfully as: ${result.filename}`, 'success');
    } catch (error) {
        console.error('Save error:', error);
        showNotification(`Error saving chat: ${error.message}`, 'error');
    }
}

async function loadSaved() {
    try {
        // Get list of saved chats
        const response = await fetch('/list_saved_chats');
        const data = await response.json();
        const chats = data.chats || [];

        if (chats.length === 0) {
            showNotification('No saved chats found', 'info');
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
        showNotification(`Error loading chat list: ${error.message}`, 'error');
    }
}

async function loadChatFile(filename) {
    try {
        const response = await fetch(`/load_chat/${filename}`);
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
        showNotification('Chat loaded successfully', 'success');
    } catch (error) {
        showNotification(`Error loading chat: ${error.message}`, 'error');
    }
}

// Handle Enter key in chat input
document.addEventListener('DOMContentLoaded', () => {
    const userInput = document.getElementById('user-input');
    if (userInput) {
        userInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                const message = userInput.value.trim();
                if (message) {
                    sendMessage(message);
                    userInput.value = '';
                }
            }
        });
    }

    // Send button
    const sendButton = document.getElementById('send-btn');
    if (sendButton) {
        sendButton.addEventListener('click', () => {
            const message = userInput.value.trim();
            if (message) {
                sendMessage(message);
                userInput.value = '';
            }
        });
    }
});