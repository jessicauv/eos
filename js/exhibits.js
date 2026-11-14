let exhibits = [];
let welcomeData = null;
let closingData = null;
let currentExhibitIndex = -1;

const cardsContainer = document.getElementById('exhibit-cards');
const dialog = document.getElementById('exhibit-dialog');
const dialogImg = document.getElementById('dialog-img');
const dialogTitle = document.getElementById('dialog-title');
const dialogWhat = document.getElementById('dialog-what');
const dialogSoundRules = document.getElementById('dialog-sound-rules');
const dialogData = document.getElementById('dialog-data');
const dialogTranscript = document.getElementById('dialog-transcript');
const dialogLongDesc = document.getElementById('dialog-long-desc');
const dialogPlayBtn = document.getElementById('dialog-play-btn');
const dialogProgress = document.getElementById('dialog-progress');
const dialogPrevBtn = document.getElementById('dialog-prev-btn');
const dialogNextBtn = document.getElementById('dialog-next-btn');
const dialogCloseBtn = document.getElementById('dialog-close-btn');

let lastOpenButton = null;

export async function loadExhibits() {
  const res = await fetch('data/exhibits.json');
  const data = await res.json();
  exhibits = data.exhibits;
  welcomeData = data.welcome;
  closingData = data.closing;
  renderCards();
  initDialog();
}

function renderCards() {
  cardsContainer.innerHTML = '';
  exhibits.forEach((ex) => {
    const card = document.createElement('article');
    card.className = 'card';
    card.dataset.exhibit = ex.id;
    card.style.setProperty('--glow-color', ex.glowColor);

    card.innerHTML = `
      <h3>Exhibit ${ex.id}: ${ex.title}</h3>
      <img
        src="${ex.thumb}"
        alt="${ex.alt}"
        width="600"
        height="375"
        loading="lazy"
      >
      <p>${ex.summary}</p>
      <button class="btn btn-open" type="button" data-exhibit="${ex.id}">Open exhibit</button>
    `;

    const btn = card.querySelector('.btn-open');
    btn.addEventListener('click', () => openExhibit(ex.id));

    cardsContainer.appendChild(card);
  });
}

function initDialog() {
  dialogCloseBtn.addEventListener('click', closeExhibit);
  dialogPrevBtn.addEventListener('click', () => navigateExhibit(-1));
  dialogNextBtn.addEventListener('click', () => navigateExhibit(1));

  dialog.addEventListener('close', () => {
    if (lastOpenButton) {
      lastOpenButton.focus();
      lastOpenButton = null;
    }
  });
}

export function openExhibit(id) {
  const index = exhibits.findIndex((ex) => ex.id === id);
  if (index === -1) return;

  lastOpenButton = document.querySelector(`.btn-open[data-exhibit="${id}"]`);
  currentExhibitIndex = index;
  populateDialog(exhibits[index]);
  dialog.showModal();
  dialogPlayBtn.focus();
}

function populateDialog(ex) {
  dialogImg.src = ex.image;
  dialogImg.alt = ex.alt;
  dialogTitle.textContent = `Exhibit ${ex.id}: ${ex.title}`;
  dialogWhat.textContent = ex.whatItShows;

  dialogSoundRules.innerHTML = '';
  ex.soundRules.forEach((rule) => {
    const li = document.createElement('li');
    li.textContent = rule;
    dialogSoundRules.appendChild(li);
  });

  dialogData.innerHTML = '';
  const dataText = document.createTextNode(ex.data + ' ');
  dialogData.appendChild(dataText);
  if (ex.sourceUrl) {
    const link = document.createElement('a');
    link.href = ex.sourceUrl;
    link.target = '_blank';
    link.rel = 'noopener';
    link.textContent = 'View source';
    dialogData.appendChild(link);
  }

  dialogTranscript.textContent = ex.transcript;
  dialogLongDesc.textContent = ex.longDescription;

  dialogProgress.textContent = '0:00 of 0:00';
  dialogPlayBtn.textContent = 'Play';
  dialogPlayBtn.setAttribute('aria-pressed', 'false');

  updateNavButtons();
}

function updateNavButtons() {
  dialogPrevBtn.disabled = currentExhibitIndex <= 0;
  dialogNextBtn.disabled = currentExhibitIndex >= exhibits.length - 1;
}

function navigateExhibit(direction) {
  const newIndex = currentExhibitIndex + direction;
  if (newIndex < 0 || newIndex >= exhibits.length) return;
  currentExhibitIndex = newIndex;
  populateDialog(exhibits[newIndex]);
  dialogTitle.focus();
}

export function closeExhibit() {
  dialog.close();
}

export function getExhibits() {
  return exhibits;
}

export function getWelcomeData() {
  return welcomeData;
}

export function getClosingData() {
  return closingData;
}

export function getCurrentExhibitIndex() {
  return currentExhibitIndex;
}

export function getCardByExhibitId(id) {
  return cardsContainer.querySelector(`.card[data-exhibit="${id}"]`);
}

export function isDialogOpen() {
  return dialog.open;
}
