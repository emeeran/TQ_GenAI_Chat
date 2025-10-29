// UI logic for TQ GenAI Chat
export function updateProviderDropdown(providers) {
  const select = document.getElementById('provider-select');
  select.innerHTML = '';
  providers.forEach(p => {
    const option = document.createElement('option');
    option.value = p;
    option.textContent = p;
    select.appendChild(option);
  });
}

export function updateModelDropdown(models) {
  const select = document.getElementById('model-select');
  select.innerHTML = '';
  models.forEach(m => {
    const option = document.createElement('option');
    option.value = m;
    option.textContent = m;
    select.appendChild(option);
  });
}
