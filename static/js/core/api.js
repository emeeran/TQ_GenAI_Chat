// API interaction logic for TQ GenAI Chat
import { debounce } from '../utils/helpers.js';

export async function fetchModels(provider) {
  const res = await fetch(`/get_models/${provider}`);
  return res.json();
}

export async function sendChatMessage(data) {
  const res = await fetch('/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
  });
  return res.json();
}
