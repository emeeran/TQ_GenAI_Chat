// Utility helper functions for TQ GenAI Chat
export function formatDate(date) {
  return new Date(date).toLocaleString();
}

export function debounce(fn, delay) {
  let timer;
  return function(...args) {
    clearTimeout(timer);
    timer = setTimeout(() => fn.apply(this, args), delay);
  };
}
