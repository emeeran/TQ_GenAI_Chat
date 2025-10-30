// User settings management for TQ GenAI Chat
export function saveSettings(settings) {
  localStorage.setItem('userSettings', JSON.stringify(settings));
}

export function loadSettings() {
  const data = localStorage.getItem('userSettings');
  return data ? JSON.parse(data) : {};
}
