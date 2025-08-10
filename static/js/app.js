// Main app entry for TQ GenAI Chat
import { updateProviderDropdown, updateModelDropdown } from './core/ui.js';
import { fetchModels } from './core/api.js';

window.addEventListener('DOMContentLoaded', async () => {
  // Fetch providers and models on load
  const providers = ['openai', 'anthropic', 'groq', 'xai', 'mistral', 'openrouter', 'alibaba', 'huggingface', 'moonshot', 'perplexity'];
  updateProviderDropdown(providers);

  const providerSelect = document.getElementById('provider-select');
  providerSelect.addEventListener('change', async (e) => {
    const models = await fetchModels(e.target.value);
    updateModelDropdown(models);
  });

  // Initial model load
  const models = await fetchModels(providers[0]);
  updateModelDropdown(models);
});
