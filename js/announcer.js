const region = document.getElementById('announcer');

export function announce(message) {
  region.textContent = '';
  setTimeout(() => { region.textContent = message; }, 100);
}
