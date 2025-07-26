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

// On load, set theme
document.addEventListener('DOMContentLoaded', () => {
    setTheme(localStorage.getItem('theme') || 'light');
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
    customPersonaInput: document.getElementById('custom-persona-input'),
    personaContent: document.getElementById('persona-content')
};

// Persona selector logic
if (elements.persona) {
    elements.persona.addEventListener('change', async function () {
        if (this.value === 'custom') {
            elements.customPersonaInput.classList.remove('d-none');
            elements.personaContent.textContent = '';
        } else {
            elements.customPersonaInput.classList.add('d-none');
            // Fetch persona content from backend
            try {
                const res = await fetch(`/get_persona_content/${this.value}`);
                const data = await res.json();
                elements.personaContent.textContent = data.content || '';
            } catch (e) {
                elements.personaContent.textContent = '';
            }
        }
    });
    // Trigger initial content
    elements.persona.dispatchEvent(new Event('change'));
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
    modelSelect.innerHTML = '<option value="">Loading models...</option>';
    modelSelect.disabled = true;

    try {
        const response = await fetch(`/get_models/${provider}`);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();
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
        } else {
            modelSelect.innerHTML = '<option value="">No models available</option>';
            modelSelect.disabled = true;
        }
    } catch (error) {
        console.error('Error fetching models:', error);
        modelSelect.innerHTML = '<option value="">Error loading models</option>';
        modelSelect.disabled = true;
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
        // Create message content container
        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';
        contentDiv.textContent = message;
        messageDiv.appendChild(contentDiv);
        
        // Add edit button for user messages
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
        // Handle formatted response
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

    modelSelect.innerHTML = '<option value="">Loading models...</option>';
    modelSelect.disabled = true;

    try {
        const response = await fetch(`/get_models/${provider}`);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();
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
        }
        modelSelect.disabled = false;
    } catch (error) {
        console.error('Error fetching retry models:', error);
        modelSelect.innerHTML = '<option value="">Error loading models</option>';
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
            persona = document.getElementById('custom-persona-input').value.trim();
        }

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

        showProcessing(true);
        showFeedback(false);

        console.log('Sending message:', { provider, model, message: messageToSend });

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
                persona: persona
            }),
            signal: controller.signal
        });

        clearTimeout(timeout);

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || `HTTP error! status: ${response.status}`);
        }

        if (data && data.response) {
            const aiMessageIndex = chatHistory.length;
            appendMessage(data.response, false, aiMessageIndex);
            if (data.response.text) {
                lastAiResponse = data.response.text;
            }
            lastMessage = messageToSend;

            // Add AI response to chat history
            chatHistory.push({
                content: data.response,
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
        showProcessing(false);
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

// Speech synthesis
const speechSynthesis = window.speechSynthesis;
let isSpeaking = false;

// Update speech synthesis variables
let selectedVoice = null;
let voiceRate = 1.0;
let voicePitch = 1.0;

async function initializeAudio() {
    try {
        // Check if audio transcription is available
        const response = await fetch('/transcribe', { method: 'POST' });
        const data = await response.json();

        if (response.status === 503) {
            console.warn('Audio support not available:', data.error);
            document.getElementById('record-button').style.display = 'none';
            return;
        }

        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        mediaRecorder = new MediaRecorder(stream);

        mediaRecorder.ondataavailable = (event) => {
            audioChunks.push(event.data);
        };

        mediaRecorder.onstop = async () => {
            const audioBlob = new Blob(audioChunks, { type: 'audio/wav' });
            const audioUrl = URL.createObjectURL(audioBlob);
            try {
                await transcribeAudio(audioBlob);
            } catch (error) {
                console.error('Error transcribing audio:', error);
                alert('Error transcribing audio. Please try again.');
            } finally {
                audioChunks = [];
            }
        };
    } catch (error) {
        console.error('Error initializing audio:', error);
        document.getElementById('record-button').style.display = 'none';
        alert('Failed to initialize audio. Please check your microphone permissions.');
    }
}

function toggleRecording() {
    if (!mediaRecorder) {
        alert('Microphone access not initialized');
        return;
    }

    const recordButton = document.getElementById('record-button');
    if (isRecording) {
        mediaRecorder.stop();
        recordButton.innerHTML = '<i class="fas fa-microphone"></i>';
        recordButton.classList.remove('btn-danger');
        recordButton.classList.add('btn-primary');
    } else {
        audioChunks = [];
        mediaRecorder.start();
        recordButton.innerHTML = '<i class="fas fa-stop"></i>';
        recordButton.classList.remove('btn-primary');
        recordButton.classList.add('btn-danger');
    }
    isRecording = !isRecording;
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

    // Filter voices by language and gender
    const filteredVoices = voices.filter(voice => {
        const isEnglish = voice.lang.startsWith('en-') || voice.lang === 'en';
        if (selectedGender === 'all') return isEnglish;
        // Simple gender detection based on voice name
        const isFemale = voice.name.toLowerCase().includes('female') ||
            voice.name.toLowerCase().includes('woman');
        const isMale = voice.name.toLowerCase().includes('male') ||
            voice.name.toLowerCase().includes('man');
        return isEnglish && (
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

    // Load saved settings
    const savedSettings = JSON.parse(localStorage.getItem('voiceSettings') || '{}');
    voiceRate = savedSettings.rate || 1.0;
    voicePitch = savedSettings.pitch || 1.0;
    const savedGender = savedSettings.gender || 'all';

    // Update UI with saved settings
    rateInput.value = voiceRate;
    pitchInput.value = voicePitch;
    rateValue.textContent = `${voiceRate.toFixed(1)}x`;
    pitchValue.textContent = `${voicePitch.toFixed(1)}x`;
    genderSelect.value = savedGender;

    // Event listeners
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
    if (isSpeaking) {
        speechSynthesis.cancel();
        isSpeaking = false;
        updateSpeakButton();
        return;
    }

    const cleanText = cleanTextForSpeech(text);

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
        speakButton.classList.add('btn-danger');
    } else {
        speakButton.innerHTML = '<i class="fas fa-volume-up"></i>';
        speakButton.classList.remove('btn-danger');
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
    const uploadBtn = document.getElementById('upload-button');

    // Update file input
    const dt = new DataTransfer();
    Array.from(files).forEach(file => {
        dt.items.add(file);
    });
    fileInput.files = dt.files;

    // Enable upload button
    uploadBtn.disabled = false;
}

// Listen for file input changes
document.getElementById('file-input').addEventListener('change', function () {
    document.getElementById('upload-button').disabled = this.files.length === 0;
});

async function uploadFiles() {
    const fileInput = document.getElementById('file-input');
    const uploadBtn = document.getElementById('upload-button');
    const progressOverlay = document.querySelector('.upload-progress-overlay');
    const progressBar = progressOverlay.querySelector('.progress-bar');
    const currentFilename = progressOverlay.querySelector('.current-filename');

    if (!fileInput.files.length) return;

    try {
        uploadBtn.disabled = true;
        progressOverlay.classList.remove('d-none');

        const formData = new FormData();
        Array.from(fileInput.files).forEach(file => {
            formData.append('files[]', file);
            currentFilename.textContent = file.name;
        });

        const xhr = new XMLHttpRequest();

        // Track upload progress
        xhr.upload.onprogress = (event) => {
            if (event.lengthComputable) {
                const percentComplete = (event.loaded / event.total) * 100;
                progressBar.style.width = percentComplete + '%';
            }
        };

        // Handle completion
        xhr.onload = async () => {
            if (xhr.status === 200) {
                const result = JSON.parse(xhr.responseText);
                if (result.results?.some(f => f.status === 'success')) {
                    await updateDocumentsList();
                    showNotification('Files uploaded successfully', 'success');
                }
            } else {
                throw new Error(xhr.status === 413 ? 'Files too large' : 'Upload failed');
            }

            // Reset UI
            fileInput.value = '';
            uploadBtn.disabled = true;
            progressBar.style.width = '0%';
            progressOverlay.classList.add('d-none');
        };

        // Handle errors
        xhr.onerror = () => {
            showNotification('Upload failed', 'error');
            progressOverlay.classList.add('d-none');
            uploadBtn.disabled = true;
        };

        // Send request
        xhr.open('POST', '/upload', true);
        xhr.send(formData);

    } catch (error) {
        console.error('Upload error:', error);
        showNotification(error.message, 'error');
        progressOverlay.classList.add('d-none');
        uploadBtn.disabled = true;
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
