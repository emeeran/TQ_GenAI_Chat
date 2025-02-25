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

function saveChat() {
    const data = {
        history: chatHistory,
        timestamp: new Date().toISOString()
    };
    localStorage.setItem('chatHistory', JSON.stringify(data));
    alert('Chat saved successfully!');
}

function loadSaved() {
    const saved = localStorage.getItem('chatHistory');
    if (saved) {
        const data = JSON.parse(saved);
        const chatBox = document.getElementById('chat-box');
        chatBox.innerHTML = '';
        chatHistory = data.history;
        chatHistory.forEach(msg => appendMessage(msg.content, msg.isUser));
        alert('Chat loaded successfully!');
    } else {
        alert('No saved chat found');
    }
}

function exportToMd() {
    let markdown = '# Chat Export\n\n';
    chatHistory.forEach(msg => {
        markdown += `## ${msg.isUser ? 'User' : 'Assistant'}\n\n${msg.content}\n\n---\n\n`;
    });

    const blob = new Blob([markdown], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `chat-export-${new Date().toISOString().slice(0, 10)}.md`;
    a.click();
    URL.revokeObjectURL(url);
}

async function retryLast() {
    if (!lastMessage) {
        alert('No message to retry!');
        return;
    }
    await sendMessage(lastMessage);
}

function provideFeedback(isPositive) {
    if (chatHistory.length > 0) {
        const lastEntry = chatHistory[chatHistory.length - 1];
        lastEntry.feedback = isPositive;
    }
    showFeedback(false);
    alert(`Thank you for your ${isPositive ? 'positive' : 'negative'} feedback!`);
}

async function sendMessage() {
    const userInput = document.getElementById('user-input');
    const message = userInput.value.trim();
    const provider = document.getElementById('provider').value;
    const model = document.getElementById('model').value;

    if (!message || !provider || !model) {
        alert('Please fill in all fields');
        return;
    }

    // Add user message to chat
    appendMessage(message, true);
    userInput.value = '';

    showProcessing(true);
    showFeedback(false);

    try {
        const response = await fetch('/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                message: message,
                provider: provider,
                model: model
            })
        });

        const data = await response.json();
        if (data.error) {
            appendMessage(`Error: ${data.error}`, false);
        } else {
            appendMessage(data.response, false);
            lastMessage = message;
            chatHistory.push({
                content: message,
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
