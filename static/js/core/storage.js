// Local storage utilities for TQ GenAI Chat
export function saveChatHistory(history) {
  localStorage.setItem('chatHistory', JSON.stringify(history));
}

export function loadChatHistory() {
  const data = localStorage.getItem('chatHistory');
  return data ? JSON.parse(data) : [];
}
