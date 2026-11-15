import * as player from './player.js';

let exhibits = [];
let welcomeData = null;
let closingData = null;
let currentExhibitIndex = -1;
let currentAudioSrc = null;

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
let onExhibitOpened = null;
let onExhibitPlay = null;
let onExhibitStop = null;

export function setOnExhibitOpened(fn) {
  onExhibitOpened = fn;
}

export function setOnExhibitPlay(fn) {
  onExhibitPlay = fn;
}

export function setOnExhibitStop(fn) {
  onExhibitStop = fn;
}

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
      <h3>
        <span class="card-num" aria-hidden="true">${String(ex.id).padStart(2, '0')}</span>
        <span>Exhibit ${ex.id}: ${ex.title}</span>
      </h3>
      <div class="frame">
        <img
          src="${ex.thumb}"
          alt="${ex.alt}"
          width="600"
          height="375"
          loading="lazy"
        >
      </div>
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

  dialogPlayBtn.addEventListener('click', togglePlay);

  player.on('timeupdate', ({ current, duration }) => {
    dialogProgress.textContent = `${player.formatTime(current)} of ${player.formatTime(duration)}`;
  });

  player.on('started', () => {
    dialogPlayBtn.textContent = 'Pause';
    dialogPlayBtn.setAttribute('aria-pressed', 'true');
  });

  player.on('paused', () => {
    dialogPlayBtn.textContent = 'Play';
    dialogPlayBtn.setAttribute('aria-pressed', 'false');
  });

  player.on('ended', () => {
    dialogPlayBtn.textContent = 'Play';
    dialogPlayBtn.setAttribute('aria-pressed', 'false');
    dialogProgress.textContent = '0:00 of 0:00';
    currentAudioSrc = null;
  });

  dialog.addEventListener('close', () => {
    player.stop();
    currentAudioSrc = null;
    if (onExhibitStop) onExhibitStop();
    if (lastOpenButton) {
      lastOpenButton.focus();
      lastOpenButton = null;
    }
  });
}

function togglePlay() {
  const ex = exhibits[currentExhibitIndex];
  if (!ex) return;

  if (player.isPlaying() && currentAudioSrc === ex.audio) {
    player.pause();
  } else if (currentAudioSrc === ex.audio) {
    player.resume();
  } else {
    currentAudioSrc = ex.audio;
    if (onExhibitPlay) onExhibitPlay(ex.id);
    player.play(ex.audio);
  }
}

export function openExhibit(id) {
  const index = exhibits.findIndex((ex) => ex.id === id);
  if (index === -1) return;

  if (onExhibitOpened) onExhibitOpened();

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
  player.stop();
  currentAudioSrc = null;
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
