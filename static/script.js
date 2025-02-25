async function updateModels() {
    const provider = document.getElementById('provider').value;
    const modelSelect = document.getElementById('model');
    modelSelect.innerHTML = '<option value="">Loading models...</option>';
    modelSelect.disabled = true;

    try {
        const response = await fetch(`/get_models/${provider}`);
        const models = await response.json();

        modelSelect.innerHTML = '<option value="">Select Model</option>';
        if (Array.isArray(models)) {
            // Get default model from the data-default attribute
            const defaultModel = document.getElementById('provider')
                .querySelector(`option[value="${provider}"]`)
                .dataset.default;

            models.sort().forEach(model => {
                const option = document.createElement('option');
                option.value = model;
                option.textContent = model;
                // Select the default model
                if (model === defaultModel) {
                    option.selected = true;
                }
                modelSelect.appendChild(option);
            });
            modelSelect.disabled = false;
        } else {
            modelSelect.innerHTML = '<option value="">No models available</option>';
        }
    } catch (error) {
        console.error('Error fetching models:', error);
        modelSelect.innerHTML = '<option value="">Error loading models</option>';
    }
}

function appendMessage(message, isUser = false) {
    const chatBox = document.getElementById('chat-box');
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${isUser ? 'user-message' : 'ai-message'}`;

    if (isUser) {
        messageDiv.textContent = message;
    } else {
        // Handle formatted response
        const content = typeof message === 'object' ? message : { text: message };
        if (content.html) {
            messageDiv.innerHTML = content.html;
        } else {
            messageDiv.textContent = content.text || message;
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
}

let chatHistory = [];
let lastMessage = null;

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
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const result = await response.json();
        if (result.error) {
            throw new Error(result.error);
        }

        alert(`Chat saved as ${result.filename}`);
    } catch (error) {
        console.error('Save error:', error);
        alert(`Error saving chat: ${error.message}`);
    }
}

async function loadSaved() {
    try {
        // Get list of saved chats
        const response = await fetch('/list_saved_chats');
        const chats = await response.json();

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
                                    ${new Date(chat.timestamp).toLocaleString()}<br>
                                    <small class="text-muted">${chat.preview}...</small>
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
        chatHistory.forEach(msg => appendMessage(msg.content, msg.isUser));

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

        const result = await response.json();
        if (result.error) throw new Error(result.error);
        alert(`Chat exported as ${result.filename}`);
    } catch (error) {
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

    modelSelect.innerHTML = '<option value="">Loading models...</option>';
    modelSelect.disabled = true;

    try {
        const response = await fetch(`/get_models/${provider}`);
        const models = await response.json();

        modelSelect.innerHTML = '<option value="">Select Model</option>';
        if (Array.isArray(models)) {
            const defaultModel = providerSelect.querySelector(`option[value="${provider}"]`).dataset.default;
            models.sort().forEach(model => {
                const option = document.createElement('option');
                option.value = model;
                option.textContent = model;
                if (model === defaultModel) {
                    option.selected = true;
                }
                modelSelect.appendChild(option);
            });
        }
        modelSelect.disabled = false;
    } catch (error) {
        modelSelect.innerHTML = '<option value="">Error loading models</option>';
    }
}

async function executeRetry(provider = null, model = null, buttonElement) {
    const modal = buttonElement.closest('.modal');
    const selectedProvider = provider || document.getElementById('retry-provider-select').value;
    const selectedModel = model || document.getElementById('retry-model-select').value;

    if (!selectedProvider || !selectedModel) {
        alert('Please select both provider and model');
        return;
    }

    // Update main interface selections
    document.getElementById('provider').value = selectedProvider;
    await updateModels();  // This will load models for the new provider
    document.getElementById('model').value = selectedModel;

    modal.remove();

    // Add user message to chat showing retry
    appendMessage(`[Retrying previous prompt with ${selectedProvider} / ${selectedModel}]`, true);

    // Rerun the message
    await sendMessage(lastMessage, true);
}

function provideFeedback(isPositive) {
    if (chatHistory.length > 0) {
        const lastEntry = chatHistory[chatHistory.length - 1];
        lastEntry.feedback = isPositive;
    }
    showFeedback(false);
    alert(`Thank you for your ${isPositive ? 'positive' : 'negative'} feedback!`);
}

async function sendMessage(message = null, isRetry = false) {
    const userInput = document.getElementById('user-input');
    const provider = document.getElementById('provider').value;
    const model = document.getElementById('model').value;

    // Use provided message for retry, otherwise get from input
    const messageToSend = message || userInput.value.trim();

    if (!messageToSend || !provider || !model) {
        alert('Please fill in all fields');
        return;
    }

    // Only clear input and add user message if not a retry
    if (!isRetry) {
        appendMessage(messageToSend, true);
        userInput.value = '';
    }

    showProcessing(true);
    showFeedback(false);

    try {
        const response = await fetch('/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                message: messageToSend,
                provider: provider,
                model: model
            })
        });

        const data = await response.json();
        if (data.error) {
            appendMessage(`Error: ${data.error}`, false);
        } else {
            appendMessage(data.response, false);
            lastMessage = messageToSend;
            chatHistory.push({
                content: messageToSend,
                isUser: true,
                timestamp: new Date().toISOString()
            });
            chatHistory.push({
                content: data.response,
                isUser: false,
                timestamp: new Date().toISOString()
            });
            showFeedback(true);
        }
    } catch (error) {
        appendMessage(`Error: ${error.message}`, false);
    } finally {
        showProcessing(false);
    }
}

// Add enter key listener for input
document.getElementById('user-input').addEventListener('keypress', function (event) {
    if (event.key === 'Enter') {
        sendMessage();
    }
});

// Initialize by triggering model load for default provider
document.addEventListener('DOMContentLoaded', function () {
    document.getElementById('provider').dispatchEvent(new Event('change'));
});
