// Eos — main.js: view switching and init (keyboard shortcuts added in step 5)

const introScreen = document.getElementById('intro-screen');
const museumScreen = document.getElementById('museum-screen');
const enterBtn = document.getElementById('enter-museum-btn');

function showMuseum() {
  introScreen.classList.remove('active');
  introScreen.hidden = true;
  museumScreen.hidden = false;
  museumScreen.classList.add('active');
  document.getElementById('museum-heading').focus();
}

enterBtn.addEventListener('click', showMuseum);

// Give the enter button focus on load
enterBtn.focus();
