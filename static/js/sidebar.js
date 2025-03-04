/**
 * Sidebar initialization and management for TQ GenAI Chat
 */

document.addEventListener('DOMContentLoaded', function () {
    console.log("Sidebar script loaded");

    // Initialize provider and model selectors
    initializeProviderSelector();

    // Setup other sidebar elements
    setupSidebarToggles();
    setupChatHistory();
});

async function initializeProviderSelector() {
    console.log("Initializing provider selector");
    const providerSelect = document.getElementById('provider-select');
    const modelSelect = document.getElementById('model-select');

    if (!providerSelect) {
        console.error("Provider select element not found in the DOM");
        return;
    }

    try {
        // Add loading state
        providerSelect.innerHTML = '<option value="">Loading providers...</option>';
        providerSelect.disabled = true;

        console.log("Fetching providers from /get_providers");
        // Fetch providers from backend
        const response = await fetch('/get_providers');
        console.log("Provider fetch response status:", response.status);

        if (!response.ok) throw new Error(`Failed to fetch providers: ${response.status}`);

        const providers = await response.json();
        console.log("Received providers:", providers);

        // Build options
        if (!Array.isArray(providers)) {
            throw new Error(`Expected array of providers, got: ${typeof providers}`);
        }

        let options = '';
        providers.forEach(provider => {
            const displayName = formatProviderName(provider);
            options += `<option value="${provider}">${displayName}</option>`;
        });

        console.log("Generated provider options HTML");
        providerSelect.innerHTML = options;
        providerSelect.disabled = false;

        // Set default provider
        const defaultProvider = 'groq';
        if (providerSelect.querySelector(`option[value="${defaultProvider}"]`)) {
            providerSelect.value = defaultProvider;
            console.log("Set default provider to:", defaultProvider);
        } else if (providers.length > 0) {
            providerSelect.value = providers[0];
            console.log("Set default provider to first option:", providers[0]);
        }

        // Trigger change event to load models
        providerSelect.dispatchEvent(new Event('change'));

        // Setup change event handler for provider select
        setupProviderChangeHandler(providerSelect, modelSelect);

    } catch (error) {
        console.error("Error initializing provider selector:", error);
        providerSelect.innerHTML = '<option value="">Error loading providers</option>';
        providerSelect.disabled = false;
    }
}

function formatProviderName(id) {
    const nameMap = {
        'openai': 'OpenAI',
        'anthropic': 'Anthropic (Claude)',
        'xai': 'xAI (Grok)',
        'groq': 'Groq',
        'mistral': 'Mistral AI',
        'cohere': 'Cohere',
        'deepseek': 'DeepSeek AI'
    };

    return nameMap[id] || id.charAt(0).toUpperCase() + id.slice(1);
}

function setupProviderChangeHandler(providerSelect, modelSelect) {
    if (!modelSelect) {
        console.error("Model select element not found");
        return;
    }

    providerSelect.addEventListener('change', async () => {
        const selectedProvider = providerSelect.value;

        if (!selectedProvider) return;

        try {
            console.log("Loading models for provider:", selectedProvider);
            modelSelect.innerHTML = '<option value="">Loading models...</option>';
            modelSelect.disabled = true;

            const response = await fetch(`/get_models/${selectedProvider}`);
            if (!response.ok) throw new Error(`Failed to load models: ${response.status}`);

            const data = await response.json();
            console.log("Received models:", data);

            if (!data.models || !Array.isArray(data.models)) {
                throw new Error('Invalid model data received');
            }

            let options = '';
            data.models.forEach(model => {
                const selected = model === data.default ? 'selected' : '';
                options += `<option value="${model}" ${selected}>${model}</option>`;
            });

            modelSelect.innerHTML = options;
            modelSelect.disabled = false;

            // Notify any listeners that the model has changed
            document.dispatchEvent(new CustomEvent('modelChanged', {
                detail: {
                    provider: selectedProvider,
                    model: modelSelect.value
                }
            }));

        } catch (error) {
            console.error(`Error loading models for ${selectedProvider}:`, error);
            modelSelect.innerHTML = '<option value="">Error loading models</option>';
            modelSelect.disabled = false;
        }
    });
}

function setupSidebarToggles() {
    // Implement sidebar collapsible sections
    const toggleButtons = document.querySelectorAll('.sidebar-section h3');

    toggleButtons.forEach(button => {
        button.addEventListener('click', () => {
            const section = button.parentElement;
            section.classList.toggle('collapsed');

            // Save state to localStorage
            const sectionId = section.id || button.textContent.toLowerCase().replace(/\s+/g, '-');
            const isCollapsed = section.classList.contains('collapsed');
            localStorage.setItem(`sidebar-${sectionId}-collapsed`, isCollapsed);
        });

        // Restore state from localStorage
        const sectionId = button.parentElement.id || button.textContent.toLowerCase().replace(/\s+/g, '-');
        const isCollapsed = localStorage.getItem(`sidebar-${sectionId}-collapsed`) === 'true';
        if (isCollapsed) {
            button.parentElement.classList.add('collapsed');
        }
    });
}

function setupChatHistory() {
    // This would be implemented to load and display chat history
    console.log("Chat history feature not yet implemented");
}
