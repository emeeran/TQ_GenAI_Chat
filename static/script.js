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

// Persona loading functionality
let personaContents = {};

async function loadPersonas() {
    const personaSelect = document.getElementById('persona');
    const statusDiv = document.getElementById('persona-status');
    
    if (!personaSelect) {
        console.error('Persona select element not found!');
        if (statusDiv) statusDiv.textContent = 'Error: Persona select element not found!';
        return;
    }
    
    if (statusDiv) statusDiv.textContent = 'Fetching personas from server...';
    
    try {
        const resp = await fetch('/personas');
        if (!resp.ok) throw new Error(`Failed to fetch personas: ${resp.status} ${resp.statusText}`);
        personaContents = await resp.json();
        
        if (statusDiv) statusDiv.textContent = 'Loading persona options...';
        
        // Clear existing options
        personaSelect.innerHTML = '';
        
        // Add each persona as an option
        let optionsAdded = 0;
        Object.entries(personaContents).forEach(([key, desc]) => {
            const opt = document.createElement('option');
            opt.value = key;
            opt.textContent = key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
            if (key === 'helpful_assistant') opt.selected = true;
            personaSelect.appendChild(opt);
            optionsAdded++;
        });
        
        // Add custom option
        const customOpt = document.createElement('option');
        customOpt.value = 'custom';
        customOpt.textContent = 'Custom Persona...';
        personaSelect.appendChild(customOpt);
        
        if (statusDiv) statusDiv.textContent = `Loaded ${optionsAdded + 1} personas successfully`;
        
        updatePersonaContent();
        console.log(`Successfully loaded ${optionsAdded} personas`);
    } catch (e) {
        console.error('Error loading personas:', e);
        
        const statusDiv = document.getElementById('persona-status');
        if (statusDiv) statusDiv.textContent = `Error: ${e.message}`;
        
        if (!personaSelect) {
            console.error('Cannot set fallback personas - personaSelect is null');
            return;
        }
        
        // Provide a more comprehensive fallback
        personaSelect.innerHTML = `
            <option value="helpful_assistant">Helpful Assistant</option>
            <option value="code_expert">Code Expert</option>
            <option value="medical_doctor">Medical Doctor</option>
            <option value="research_scientist">Research Scientist</option>
            <option value="business_analyst">Business Analyst</option>
            <option value="legal_advisor">Legal Advisor</option>
            <option value="custom">Custom Persona...</option>
        `;
        
        if (statusDiv) statusDiv.textContent = 'Using fallback personas due to server error';
        console.warn('Using fallback personas due to server error');
    }
}

function updatePersonaContent() {
    const personaSelect = document.getElementById('persona');
    const customInput = document.getElementById('custom-persona-textarea');
    const contentDiv = document.getElementById('persona-content');
    
    if (!personaSelect) return;
    
    let persona = personaSelect.value;
    if (persona === 'custom') {
        if (customInput) customInput.classList.remove('d-none');
        if (contentDiv) contentDiv.textContent = customInput?.value || 'Describe your custom persona above.';
    } else {
        if (customInput) {
            customInput.classList.add('d-none');
            customInput.value = '';
        }
        if (contentDiv) contentDiv.textContent = personaContents[persona] || '';
    }
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
    
    // Load personas after a short delay to ensure all elements are ready
    setTimeout(() => {
        loadPersonas().then(() => {
            // Set up persona event listeners after loading
            const personaSelect = document.getElementById('persona');
            const customInput = document.getElementById('custom-persona-textarea');
            
            if (personaSelect) {
                personaSelect.addEventListener('change', updatePersonaContent);
            }
            if (customInput) {
                customInput.addEventListener('input', updatePersonaContent);
            }
        }).catch(err => {
            console.error('Error setting up personas:', err);
        });
    }, 300);
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

// Cache DOM queries - Note: elements might be null if called before DOM is ready
const elements = {
    chatBox: document.getElementById('chat-box'),
    userInput: document.getElementById('user-input'),
    provider: document.getElementById('provider'),
    model: document.getElementById('model'),
    // persona: document.getElementById('persona'), // Removed - will be handled dynamically
    // customPersonaInput: document.getElementById('custom-persona-textarea'), // Removed - will be handled dynamically
    // personaContent: document.getElementById('persona-content') // Removed - will be handled dynamically
};

// Always refresh models on provider change
if (elements.provider) {
    elements.provider.addEventListener('change', () => {
        updateModels();
        // Save provider selection
        localStorage.setItem('defaultProvider', elements.provider.value);
        // Update display immediately
        updateProviderModelDisplay();
    });
}

// Save model selection when changed
if (elements.model) {
    elements.model.addEventListener('change', () => {
        localStorage.setItem('defaultModel', elements.model.value);
        // Update display immediately
        updateProviderModelDisplay();
    });
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
    
    // Add animation for updates
    displayElement.style.transition = 'all 0.3s ease';
    displayElement.style.transform = 'scale(1.05)';
    
    // Update content
    displayElement.innerHTML = `<strong>${provider} | ${model}</strong>`;
    
    // Reset scale after animation
    setTimeout(() => {
        displayElement.style.transform = 'scale(1)';
    }, 150);
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
    
    // Set up real-time provider/model display updates
    setupProviderModelDisplayUpdates();
});

// Function to set up real-time updates for provider/model display
function setupProviderModelDisplayUpdates() {
    // Update display initially
    updateProviderModelDisplay();
    
    // Set up a periodic update to catch any missed changes
    setInterval(updateProviderModelDisplay, 1000);
    
    // Also update when window regains focus (in case updates were missed)
    window.addEventListener('focus', updateProviderModelDisplay);
}

function updateSliderProgress(slider) {
    const value = ((slider.value - slider.min) / (slider.max - slider.min)) * 100;
    slider.style.setProperty('--range-progress', value + '%');
}

// Function to remove thinking tags from AI responses
function removeThinkingTags(text) {
    if (!text) return text;
    
    // Remove <thinking>...</thinking> blocks (case insensitive, multiline)
    return text.replace(/<thinking[\s\S]*?<\/thinking>/gi, '').trim();
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
            // Update display after models are loaded and default is selected
            updateProviderModelDisplay();
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
        let markdown = content.text || message;
        
        // Remove thinking tags from response display
        markdown = removeThinkingTags(markdown);
        
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
        lastAiResponse = removeThinkingTags(message.text);
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
        alert(`Chat saved successfully as: ${result.filename}`);
    } catch (error) {
        console.error('Save error:', error);
        alert(`Error saving chat: ${error.message}`);
    }
}

async function loadSaved() {
    try {
        // Get list of saved chats
        const response = await fetch('/list_saved_chats');
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

        const response = await fetch('/export_chat', {
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

        const response = await fetch(`/update_models/${provider}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });

        const data = await response.json();

        if (data.success) {
            // Refresh the model dropdown
            await updateModels();
            // Update display after models refresh
            updateProviderModelDisplay();
            
            alert(`✅ ${data.message}\n\nFound ${data.models.length} models:\n${data.models.slice(0, 5).join(', ')}${data.models.length > 5 ? '...' : ''}`);
        } else {
            throw new Error(data.error || 'Failed to update models');
        }
    } catch (error) {
        console.error('Model update error:', error);
        alert(`❌ Error updating models: ${error.message}`);
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

        const messageToSend = message || userInput.value.trim();

        if (!messageToSend || !provider || !model) {
            throw new Error('Please fill in all fields');
        }

        // Only clear input and add user message if not a retry
        if (!isRetry) {
            const userMessageIndex = chatHistory.length;
            appendMessage(messageToSend, true, userMessageIndex);
            userInput.value = '';
            
            // Reset the input container to default state
            resetInputContainer();
            
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
                temperature: parseFloat(temperature)
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
                // Remove thinking tags from stored text for copy/speak functions
                const cleanText = removeThinkingTags(aiMessage.text);
                lastAiResponse = cleanText;
                lastAiResponseText = cleanText; // Store for copy function
                // Show copy button
                document.getElementById('copy-response-btn')?.classList.remove('d-none');
                
                // Auto-speak if enabled
                const autoSpeak = document.getElementById('auto-speak');
                if (autoSpeak && autoSpeak.checked) {
                    // Small delay to ensure message is displayed first
                    setTimeout(() => {
                        speakText(cleanText);
                    }, 500);
                }
            }
            lastMessage = messageToSend;

            // Add AI response to chat history (with thinking tags removed)
            const cleanedAiMessage = { ...aiMessage };
            if (cleanedAiMessage.text) {
                cleanedAiMessage.text = removeThinkingTags(cleanedAiMessage.text);
            }
            chatHistory.push({
                content: cleanedAiMessage,
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
    if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        sendMessage();
    }
});

// Auto-resize textarea functionality with dynamic container
function autoResizeTextarea(textarea) {
    // Reset height to auto to get the correct scrollHeight
    textarea.style.height = 'auto';
    
    const minHeight = 40; // Minimum height
    const maxHeight = 200; // Maximum height
    const scrollHeight = textarea.scrollHeight;
    
    // Set the new height
    const newHeight = Math.max(minHeight, Math.min(scrollHeight, maxHeight));
    textarea.style.height = newHeight + 'px';
    
    // Handle overflow
    textarea.style.overflowY = scrollHeight > maxHeight ? 'auto' : 'hidden';
    
    // Dynamically resize the container based on content
    resizeInputContainer(textarea);
}

// Function to dynamically resize the input container
function resizeInputContainer(textarea) {
    const container = textarea.closest('.input-container');
    if (!container) return;
    
    const textLength = textarea.value.length;
    const lineCount = textarea.value.split('\n').length;
    const hasContent = textLength > 0;
    
    // Add classes based on content
    if (textLength > 100 || lineCount > 2) {
        container.classList.add('expanded');
        container.classList.remove('compact');
    } else if (hasContent) {
        container.classList.remove('expanded');
        container.classList.add('compact');
    } else {
        container.classList.remove('expanded', 'compact');
    }
    
    // Animate the container changes
    container.style.transition = 'all 0.3s ease';
}

// Function to reset input container to default state
function resetInputContainer() {
    const userInput = document.getElementById('user-input');
    const container = userInput?.closest('.input-container');
    
    if (container) {
        container.classList.remove('expanded', 'compact');
        container.style.transform = '';
        container.style.boxShadow = '';
    }
    
    if (userInput) {
        // Reset textarea height
        autoResizeTextarea(userInput);
    }
}

// Set up auto-resize for user input
document.addEventListener('DOMContentLoaded', function() {
    const userInput = document.getElementById('user-input');
    if (userInput) {
        // Handle input events
        userInput.addEventListener('input', function() {
            autoResizeTextarea(this);
        });
        
        // Handle pasted content
        userInput.addEventListener('paste', function() {
            setTimeout(() => autoResizeTextarea(this), 0);
        });
        
        // Handle focus/blur for container animation
        userInput.addEventListener('focus', function() {
            const container = this.closest('.input-container');
            if (container) {
                container.style.boxShadow = '0 4px 12px rgba(0, 0, 0, 0.15)';
                container.style.transform = 'translateY(-1px)';
            }
        });
        
        userInput.addEventListener('blur', function() {
            const container = this.closest('.input-container');
            if (container) {
                container.style.boxShadow = '0 2px 4px rgba(0, 0, 0, 0.1)';
                container.style.transform = 'translateY(0)';
            }
        });
        
        // Handle backspace and delete for dynamic resizing
        userInput.addEventListener('keydown', function(e) {
            if (e.key === 'Backspace' || e.key === 'Delete') {
                setTimeout(() => autoResizeTextarea(this), 0);
            }
        });
        
        // Initialize the container state
        autoResizeTextarea(userInput);
    }
});

// Initialize by triggering model load for default provider
document.addEventListener('DOMContentLoaded', function () {
    // Set Groq as default provider
    const providerSelect = document.getElementById('provider');
    providerSelect.value = 'groq';

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
let voiceVolume = 1.0;

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
    const languageSelect = document.getElementById('voice-language');
    const voiceCount = document.getElementById('voice-count');
    const voiceInfo = document.getElementById('voice-info');
    
    const voices = speechSynthesis.getVoices();
    console.log('Available voices from browser:', voices); // Log all available voices
    const selectedGender = genderSelect.value;
    const selectedLanguage = languageSelect.value;

    // Filter voices by language and gender only (no search)
    const filteredVoices = voices.filter(voice => {
        // Language filtering
        let languageMatch = true;
        if (selectedLanguage !== 'all') {
            languageMatch = voice.lang.startsWith(selectedLanguage + '-') || voice.lang === selectedLanguage;
        }
        
        // Gender filtering
        let genderMatch = true;
        if (selectedGender !== 'all') {
            // Enhanced gender detection based on voice name patterns
            const isFemale = voice.name.toLowerCase().includes('female') ||
                voice.name.toLowerCase().includes('woman') ||
                voice.name.toLowerCase().includes('zira') ||
                voice.name.toLowerCase().includes('susan') ||
                voice.name.toLowerCase().includes('helen') ||
                voice.name.toLowerCase().includes('cortana') ||
                voice.name.toLowerCase().includes('samantha') ||
                voice.name.toLowerCase().includes('victoria') ||
                voice.name.toLowerCase().includes('karen') ||
                voice.name.toLowerCase().includes('moira');
                
            const isMale = voice.name.toLowerCase().includes('male') ||
                voice.name.toLowerCase().includes('man') ||
                // Common US Male Voice Names
                voice.name.toLowerCase().includes('david') ||
                voice.name.toLowerCase().includes('mark') ||
                voice.name.toLowerCase().includes('richard') ||
                voice.name.toLowerCase().includes('alex') ||
                voice.name.toLowerCase().includes('daniel') ||
                voice.name.toLowerCase().includes('fred') ||
                voice.name.toLowerCase().includes('tom') ||
                voice.name.toLowerCase().includes('ralph') ||
                voice.name.toLowerCase().includes('bruce') ||
                voice.name.toLowerCase().includes('reed') ||
                voice.name.toLowerCase().includes('junior') ||
                // Additional US Male Voices
                voice.name.toLowerCase().includes('aaron') ||
                voice.name.toLowerCase().includes('adam') ||
                voice.name.toLowerCase().includes('andrew') ||
                voice.name.toLowerCase().includes('anthony') ||
                voice.name.toLowerCase().includes('arthur') ||
                voice.name.toLowerCase().includes('austin') ||
                voice.name.toLowerCase().includes('benjamin') ||
                voice.name.toLowerCase().includes('brian') ||
                voice.name.toLowerCase().includes('calvin') ||
                voice.name.toLowerCase().includes('carlos') ||
                voice.name.toLowerCase().includes('chad') ||
                voice.name.toLowerCase().includes('charles') ||
                voice.name.toLowerCase().includes('christopher') ||
                voice.name.toLowerCase().includes('craig') ||
                voice.name.toLowerCase().includes('derek') ||
                voice.name.toLowerCase().includes('edward') ||
                voice.name.toLowerCase().includes('eric') ||
                voice.name.toLowerCase().includes('evan') ||
                voice.name.toLowerCase().includes('frank') ||
                voice.name.toLowerCase().includes('gary') ||
                voice.name.toLowerCase().includes('george') ||
                voice.name.toLowerCase().includes('gregory') ||
                voice.name.toLowerCase().includes('harrison') ||
                voice.name.toLowerCase().includes('henry') ||
                voice.name.toLowerCase().includes('jacob') ||
                voice.name.toLowerCase().includes('james') ||
                voice.name.toLowerCase().includes('jason') ||
                voice.name.toLowerCase().includes('jeffrey') ||
                voice.name.toLowerCase().includes('jeremy') ||
                voice.name.toLowerCase().includes('john') ||
                voice.name.toLowerCase().includes('jonathan') ||
                voice.name.toLowerCase().includes('joseph') ||
                voice.name.toLowerCase().includes('joshua') ||
                voice.name.toLowerCase().includes('justin') ||
                voice.name.toLowerCase().includes('keith') ||
                voice.name.toLowerCase().includes('kevin') ||
                voice.name.toLowerCase().includes('lance') ||
                voice.name.toLowerCase().includes('larry') ||
                voice.name.toLowerCase().includes('lawrence') ||
                voice.name.toLowerCase().includes('louis') ||
                voice.name.toLowerCase().includes('marcus') ||
                voice.name.toLowerCase().includes('matthew') ||
                voice.name.toLowerCase().includes('michael') ||
                voice.name.toLowerCase().includes('nathan') ||
                voice.name.toLowerCase().includes('nicholas') ||
                voice.name.toLowerCase().includes('patrick') ||
                voice.name.toLowerCase().includes('paul') ||
                voice.name.toLowerCase().includes('peter') ||
                voice.name.toLowerCase().includes('phillip') ||
                voice.name.toLowerCase().includes('robert') ||
                voice.name.toLowerCase().includes('ronald') ||
                voice.name.toLowerCase().includes('ryan') ||
                voice.name.toLowerCase().includes('samuel') ||
                voice.name.toLowerCase().includes('scott') ||
                voice.name.toLowerCase().includes('sean') ||
                voice.name.toLowerCase().includes('stephen') ||
                voice.name.toLowerCase().includes('steven') ||
                voice.name.toLowerCase().includes('thomas') ||
                voice.name.toLowerCase().includes('timothy') ||
                voice.name.toLowerCase().includes('tyler') ||
                voice.name.toLowerCase().includes('victor') ||
                voice.name.toLowerCase().includes('vincent') ||
                voice.name.toLowerCase().includes('walter') ||
                voice.name.toLowerCase().includes('wayne') ||
                voice.name.toLowerCase().includes('william') ||
                voice.name.toLowerCase().includes('zachary') ||
                // System/Platform specific US male voices
                voice.name.toLowerCase().includes('cortana') && voice.name.toLowerCase().includes('male') ||
                voice.name.toLowerCase().includes('siri') && voice.name.toLowerCase().includes('male') ||
                voice.name.toLowerCase().includes('narrator') ||
                voice.name.toLowerCase().includes('steve') ||
                voice.name.toLowerCase().includes('mike') ||
                voice.name.toLowerCase().includes('jim') ||
                voice.name.toLowerCase().includes('bob') ||
                voice.name.toLowerCase().includes('joe') ||
                voice.name.toLowerCase().includes('tony') ||
                voice.name.toLowerCase().includes('mike') ||
                voice.name.toLowerCase().includes('dave') ||
                voice.name.toLowerCase().includes('chris') ||
                voice.name.toLowerCase().includes('matt') ||
                // Windows voices
                voice.name.toLowerCase().includes('ben') ||
                voice.name.toLowerCase().includes('callie') && voice.name.toLowerCase().includes('male') ||
                // macOS voices  
                voice.name.toLowerCase().includes('albert') ||
                voice.name.toLowerCase().includes('bad news') ||
                voice.name.toLowerCase().includes('bahh') ||
                voice.name.toLowerCase().includes('bells') ||
                voice.name.toLowerCase().includes('boing') ||
                voice.name.toLowerCase().includes('bruce') ||
                voice.name.toLowerCase().includes('bubbles') ||
                voice.name.toLowerCase().includes('deranged') ||
                voice.name.toLowerCase().includes('good news') ||
                voice.name.toLowerCase().includes('hysterical') ||
                voice.name.toLowerCase().includes('junior') ||
                voice.name.toLowerCase().includes('pipe organ') ||
                voice.name.toLowerCase().includes('ralph') ||
                voice.name.toLowerCase().includes('trinoids') ||
                voice.name.toLowerCase().includes('whisper') ||
                voice.name.toLowerCase().includes('zarvox');
            
            genderMatch = (selectedGender === 'female' && isFemale) ||
                         (selectedGender === 'male' && isMale);
        }
        
        return languageMatch && genderMatch;
    });

    // Update voice count
    if (voiceCount) {
        voiceCount.textContent = `${filteredVoices.length} voice${filteredVoices.length !== 1 ? 's' : ''}`;
    }

    voiceSelect.innerHTML = '';
    if (filteredVoices.length === 0) {
        const option = document.createElement('option');
        option.value = '';
        option.textContent = 'No voices available for selected filters';
        voiceSelect.appendChild(option);
        
        if (voiceInfo) {
            voiceInfo.className = 'voice-info empty mt-2';
            voiceInfo.innerHTML = '<small class="text-muted">No voices available</small>';
        }
        return;
    }

    // Sort voices by name for better UX
    filteredVoices.sort((a, b) => a.name.localeCompare(b.name));

    filteredVoices.forEach(voice => {
        const option = document.createElement('option');
        option.value = voice.name;
        option.textContent = `${voice.name}`;
        option.dataset.lang = voice.lang;
        option.dataset.default = voice.default;
        
        if (voice.default) {
            option.selected = true;
            selectedVoice = voice;
            updateVoiceInfo(voice);
        }
        voiceSelect.appendChild(option);
    });

    // Add voice selection change handler for info display
    voiceSelect.addEventListener('change', function() {
        const selectedVoiceName = this.value;
        const voice = voices.find(v => v.name === selectedVoiceName);
        if (voice) {
            updateVoiceInfo(voice);
        }
    });
}

function updateVoiceInfo(voice) {
    const voiceInfo = document.getElementById('voice-info');
    if (!voiceInfo || !voice) return;
    
    voiceInfo.className = 'voice-info mt-2';
    voiceInfo.innerHTML = `
        <div class="voice-details">
            <strong>${voice.name}</strong>
            <span class="voice-lang-badge">${voice.lang}</span>
            ${voice.default ? '<span class="voice-default-badge">Default</span>' : ''}
            <br>
            <small class="text-muted">
                ${voice.localService ? 'Local voice' : 'Online voice'} • 
                ${voice.voiceURI || 'System voice'}
            </small>
        </div>
    `;
}

function previewVoice() {
    const voiceSelect = document.getElementById('voice-select');
    const previewBtn = document.getElementById('voice-preview-btn');
    const selectedVoiceName = voiceSelect.value;
    
    if (!selectedVoiceName) {
        alert('Please select a voice first');
        return;
    }
    
    const voices = speechSynthesis.getVoices();
    const voice = voices.find(v => v.name === selectedVoiceName);
    
    if (!voice) {
        alert('Selected voice not found');
        return;
    }
    
    // Stop any ongoing speech
    speechSynthesis.cancel();
    
    // Update button state
    previewBtn.classList.add('playing');
    previewBtn.innerHTML = '<i class="fas fa-stop"></i>';
    previewBtn.title = 'Stop preview';
    
    // Create test utterance
    const testText = `Hello! This is a preview of the ${voice.name} voice. How do you like the way I sound?`;
    const utterance = new SpeechSynthesisUtterance(testText);
    utterance.voice = voice;
    utterance.rate = voiceRate;
    utterance.pitch = voicePitch;
    utterance.volume = voiceVolume;
    
    // Reset button when finished
    utterance.onend = () => {
        previewBtn.classList.remove('playing');
        previewBtn.innerHTML = '<i class="fas fa-play"></i>';
        previewBtn.title = 'Preview selected voice';
    };
    
    utterance.onerror = () => {
        previewBtn.classList.remove('playing');
        previewBtn.innerHTML = '<i class="fas fa-play"></i>';
        previewBtn.title = 'Preview selected voice';
        alert('Error playing voice preview');
    };
    
    speechSynthesis.speak(utterance);
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
    const languageSelect = document.getElementById('voice-language');
    const previewBtn = document.getElementById('voice-preview-btn');
    const rateInput = document.getElementById('voice-rate');
    const pitchInput = document.getElementById('voice-pitch');
    const rateValue = document.getElementById('voice-rate-value');
    const pitchValue = document.getElementById('voice-pitch-value');
    const autoSpeakCheckbox = document.getElementById('auto-speak');

    // Load saved settings
    const savedSettings = JSON.parse(localStorage.getItem('voiceSettings') || '{}');
    voiceRate = savedSettings.rate || 1.0;
    voicePitch = savedSettings.pitch || 1.0;
    voiceVolume = savedSettings.volume || 1.0;
    const savedGender = savedSettings.gender || 'all';
    const savedLanguage = savedSettings.language || 'all';
    const autoSpeakEnabled = savedSettings.autoSpeak !== false; // Default to true

    // Update UI with saved settings
    const volumeInput = document.getElementById('voice-volume');
    const volumeValue = document.getElementById('voice-volume-value');
    rateInput.value = voiceRate;
    pitchInput.value = voicePitch;
    if (volumeInput) volumeInput.value = voiceVolume;
    rateValue.textContent = `${voiceRate.toFixed(1)}x`;
    pitchValue.textContent = `${voicePitch.toFixed(1)}x`;
    if (volumeValue) volumeValue.textContent = Math.round(voiceVolume * 100) + '%';
    genderSelect.value = savedGender;
    languageSelect.value = savedLanguage;
    autoSpeakCheckbox.checked = autoSpeakEnabled;

    // Event listeners
    autoSpeakCheckbox.addEventListener('change', (e) => {
        const updatedSettings = JSON.parse(localStorage.getItem('voiceSettings') || '{}');
        updatedSettings.autoSpeak = e.target.checked;
        localStorage.setItem('voiceSettings', JSON.stringify(updatedSettings));
    });

    genderSelect.addEventListener('change', (e) => {
        const gender = e.target.value;
        const currentSettings = JSON.parse(localStorage.getItem('voiceSettings') || '{}');
        currentSettings.gender = gender;
        localStorage.setItem('voiceSettings', JSON.stringify(currentSettings));
        updateVoiceList(); // Refresh voice list with gender filter
    });

    languageSelect.addEventListener('change', (e) => {
        const language = e.target.value;
        const currentSettings = JSON.parse(localStorage.getItem('voiceSettings') || '{}');
        currentSettings.language = language;
        localStorage.setItem('voiceSettings', JSON.stringify(currentSettings));
        updateVoiceList(); // Refresh voice list with language filter
    });

    // Enhanced keyboard navigation for voice select dropdown
    if (voiceSelect) {
        voiceSelect.addEventListener('keydown', (e) => {
            // Space bar to preview selected voice
            if (e.code === 'Space') {
                e.preventDefault();
                previewVoice();
            }
            // P key to preview
            if (e.key.toLowerCase() === 'p' && !e.ctrlKey && !e.altKey) {
                e.preventDefault();
                previewVoice();
            }
        });
    }

    // Voice preview functionality
    if (previewBtn) {
        previewBtn.addEventListener('click', (e) => {
            e.preventDefault();
            if (previewBtn.classList.contains('playing')) {
                // Stop current speech
                speechSynthesis.cancel();
                previewBtn.classList.remove('playing');
                previewBtn.innerHTML = '<i class="fas fa-play"></i>';
                previewBtn.title = 'Preview selected voice';
            } else {
                previewVoice();
            }
        });
    }

    voiceSelect.addEventListener('change', (e) => {
        const voices = speechSynthesis.getVoices();
        selectedVoice = voices.find(voice => voice.name === e.target.value);
        const currentSettings = JSON.parse(localStorage.getItem('voiceSettings') || '{}');
        currentSettings.voice = selectedVoice?.name;
        localStorage.setItem('voiceSettings', JSON.stringify(currentSettings));
        
        // Update voice info display
        if (selectedVoice) {
            updateVoiceInfo(selectedVoice);
        }
    });

    rateInput.addEventListener('input', (e) => {
        voiceRate = parseFloat(e.target.value);
        rateValue.textContent = `${voiceRate.toFixed(1)}x`;
        
        // Update slider progress visual
        updateSliderProgress(rateInput, voiceRate, 0.5, 2);
        
        const currentSettings = JSON.parse(localStorage.getItem('voiceSettings') || '{}');
        currentSettings.rate = voiceRate;
        localStorage.setItem('voiceSettings', JSON.stringify(currentSettings));
    });

    pitchInput.addEventListener('input', (e) => {
        voicePitch = parseFloat(e.target.value);
        pitchValue.textContent = `${voicePitch.toFixed(1)}x`;
        
        // Update slider progress visual
        updateSliderProgress(pitchInput, voicePitch, 0.5, 2);
        
        const currentSettings = JSON.parse(localStorage.getItem('voiceSettings') || '{}');
        currentSettings.pitch = voicePitch;
        localStorage.setItem('voiceSettings', JSON.stringify(currentSettings));
    });

    // Volume control event listener
    if (volumeInput) {
        volumeInput.addEventListener('input', (e) => {
            voiceVolume = parseFloat(e.target.value);
            volumeValue.textContent = Math.round(voiceVolume * 100) + '%';
            
            // Update slider progress visual
            updateSliderProgress(volumeInput, voiceVolume, 0, 1);
            
            const currentSettings = JSON.parse(localStorage.getItem('voiceSettings') || '{}');
            currentSettings.volume = voiceVolume;
            localStorage.setItem('voiceSettings', JSON.stringify(currentSettings));
        });
    }

    // Initialize slider progress visuals
    updateSliderProgress(rateInput, voiceRate, 0.5, 2);
    updateSliderProgress(pitchInput, voicePitch, 0.5, 2);
    if (volumeInput) {
        updateSliderProgress(volumeInput, voiceVolume, 0, 1);
    }

    updateVoiceList();
    speechSynthesis.onvoiceschanged = updateVoiceList;
}

// Function to update slider progress visual
function updateSliderProgress(slider, value, min, max) {
    if (!slider) return;
    
    const progress = ((value - min) / (max - min)) * 100;
    slider.style.setProperty('--progress', `${progress}%`);
}

// Voice preset functions
function applyVoicePreset(presetName) {
    const rateInput = document.getElementById('voice-rate');
    const pitchInput = document.getElementById('voice-pitch');
    const volumeInput = document.getElementById('voice-volume');
    const rateValue = document.getElementById('voice-rate-value');
    const pitchValue = document.getElementById('voice-pitch-value');
    const volumeValue = document.getElementById('voice-volume-value');
    
    let rate, pitch, volume;
    
    switch(presetName) {
        case 'normal':
            rate = 1.0;
            pitch = 1.0;
            volume = 1.0;
            break;
        case 'slow':
            rate = 0.7;
            pitch = 1.0;
            volume = 1.0;
            break;
        case 'fast':
            rate = 1.4;
            pitch = 1.0;
            volume = 1.0;
            break;
        case 'deep':
            rate = 0.9;
            pitch = 0.7;
            volume = 1.0;
            break;
        default:
            return;
    }
    
    // Update sliders and values
    if (rateInput) {
        rateInput.value = rate;
        voiceRate = rate;
        rateValue.textContent = `${rate.toFixed(1)}x`;
        updateSliderProgress(rateInput, rate, 0.5, 2);
    }
    
    if (pitchInput) {
        pitchInput.value = pitch;
        voicePitch = pitch;
        pitchValue.textContent = `${pitch.toFixed(1)}x`;
        updateSliderProgress(pitchInput, pitch, 0.5, 2);
    }
    
    if (volumeInput) {
        volumeInput.value = volume;
        voiceVolume = volume;
        volumeValue.textContent = Math.round(volume * 100) + '%';
        updateSliderProgress(volumeInput, volume, 0, 1);
    }
    
    // Save settings
    const currentSettings = JSON.parse(localStorage.getItem('voiceSettings') || '{}');
    currentSettings.rate = rate;
    currentSettings.pitch = pitch;
    currentSettings.volume = volume;
    localStorage.setItem('voiceSettings', JSON.stringify(currentSettings));
    
    // Provide audio feedback
    setTimeout(() => {
        const testText = `Voice preset "${presetName}" applied successfully.`;
        const utterance = new SpeechSynthesisUtterance(testText);
        if (selectedVoice) utterance.voice = selectedVoice;
        utterance.rate = rate;
        utterance.pitch = pitch;
        utterance.volume = volume;
        speechSynthesis.speak(utterance);
    }, 100);
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
        showNotification('No text to speak. Please send a message first.', 'warning');
        return;
    }

    if (isSpeaking) {
        speechSynthesis.cancel();
        isSpeaking = false;
        updateSpeakButton();
        showNotification('Speech stopped', 'info');
        return;
    }

    const cleanText = cleanTextForSpeech(text);

    if (!cleanText || cleanText.trim().length === 0) {
        showNotification('No readable text found.', 'warning');
        return;
    }

    // Enhanced speech with better error handling
    try {
        // Split text into sentences for better handling
        const sentences = cleanText.match(/[^.!?]+[.!?]+/g) || [cleanText];
        let currentSentence = 0;

        function speakNextSentence() {
            if (currentSentence >= sentences.length || !isSpeaking) {
                isSpeaking = false;
                updateSpeakButton();
                showNotification('Speech completed', 'success');
                return;
            }

            const utterance = new SpeechSynthesisUtterance(sentences[currentSentence]);

            // Apply voice settings
            if (selectedVoice) utterance.voice = selectedVoice;
            utterance.rate = voiceRate;
            utterance.pitch = voicePitch;
            utterance.volume = voiceVolume;

            utterance.onend = () => {
                currentSentence++;
                speakNextSentence();
            };

            utterance.onerror = (event) => {
                console.error('Speech synthesis error:', event);
                isSpeaking = false;
                updateSpeakButton();
                showNotification('Text-to-speech error. Please try again.', 'error');
            };

            try {
                speechSynthesis.speak(utterance);
            } catch (error) {
                console.error('Speech synthesis failed:', error);
                showNotification('Text-to-speech failed. Please check your browser settings.', 'error');
                isSpeaking = false;
                updateSpeakButton();
            }
        }

        isSpeaking = true;
        updateSpeakButton();
        speakNextSentence();
        
    } catch (error) {
        console.error('Speech synthesis initialization failed:', error);
        showNotification('Text-to-speech initialization failed. Please check your browser settings.', 'error');
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

// Voice preview function
function previewVoice() {
    const previewText = "Hello! This is a preview of the selected voice with current settings.";
    speakText(previewText);
}

// Enhanced stop speech function
function stopSpeech() {
    if (speechSynthesis.speaking || isSpeaking) {
        speechSynthesis.cancel();
        isSpeaking = false;
        updateSpeakButton();
        showNotification('Speech stopped', 'info');
    }
}

// Enhanced voice volume control
function updateVoiceVolume() {
    const volumeSlider = document.getElementById('voice-volume');
    const volumeValue = document.getElementById('voice-volume-value');
    if (volumeSlider && volumeValue) {
        voiceVolume = parseFloat(volumeSlider.value);
        volumeValue.textContent = Math.round(voiceVolume * 100) + '%';
        
        // Save to localStorage
        const savedSettings = JSON.parse(localStorage.getItem('voiceSettings') || '{}');
        savedSettings.volume = voiceVolume;
        localStorage.setItem('voiceSettings', JSON.stringify(savedSettings));
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
                                        const msgId = `doc-preview-${Date.now()}-${Math.floor(Math.random()*10000)}`;
                                        let html = `<div id="${msgId}">`;
                                        html += `<strong>Extracted text from ${f.filename}:</strong><br><pre style='white-space:pre-wrap;word-break:break-word;max-height:320px;overflow:auto;'>`;
                                        html += isLong ? shortText + '...' : shortText;
                                        html += '</pre>';
                                        if (isLong) {
                                            html += `<button class='btn btn-link btn-sm' style='padding:0;margin-top:-0.5em;' onclick="toggleDocPreview('${msgId}', this, \`${fullText.replace(/`/g, '\`').replace(/\\/g, '\\\\').replace(/'/g, "\\'").replace(/\n/g, '\\n') }\`, \`${shortText.replace(/`/g, '\`').replace(/\\/g, '\\\\').replace(/'/g, "\\'").replace(/\n/g, '\\n') }\`)">Show more</button>`;
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
    // Simple notification display
    alert(`${type.toUpperCase()}: ${message}`);
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
