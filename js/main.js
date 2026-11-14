import { loadExhibits } from './exhibits.js';

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

async function init() {
  await loadExhibits();
  enterBtn.focus();
}

init();
