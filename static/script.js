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
            models.sort().forEach(model => {
                const option = document.createElement('option');
                option.value = model;
                option.textContent = model;
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
        }
    } catch (error) {
        appendMessage(`Error: ${error.message}`, false);
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
