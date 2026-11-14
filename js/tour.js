import * as player from './player.js';
import { getExhibits, getWelcomeData, getClosingData, getCardByExhibitId, openExhibit, closeExhibit, isDialogOpen } from './exhibits.js';

let running = false;
let paused = false;
let queue = [];
let currentStep = -1;
let pauseTimer = null;
let onAnnounce = null;

const startBtn = document.getElementById('start-tour-btn');
const welcomeBtn = document.getElementById('play-welcome-btn');
const activeControls = document.getElementById('tour-active-controls');
const tourStatus = document.getElementById('tour-status');
const tourPauseBtn = document.getElementById('tour-pause-btn');
const tourSkipBtn = document.getElementById('tour-skip-btn');
const tourStopBtn = document.getElementById('tour-stop-btn');

export function init(announceFn) {
  onAnnounce = announceFn;
  startBtn.addEventListener('click', start);
  welcomeBtn.addEventListener('click', playWelcome);
  tourPauseBtn.addEventListener('click', pauseResume);
  tourSkipBtn.addEventListener('click', skip);
  tourStopBtn.addEventListener('click', stop);
  player.on('ended', onTrackEnded);
}

function buildQueue() {
  const exhibits = getExhibits();
  const welcome = getWelcomeData();
  const closing = getClosingData();
  queue = [];
  queue.push({ type: 'welcome', audio: welcome.audio, label: 'Welcome' });
  exhibits.forEach((ex, i) => {
    queue.push({ type: 'exhibit', audio: ex.audio, exhibitId: ex.id, label: `Exhibit ${i + 1} of ${exhibits.length} — ${ex.title}` });
  });
  queue.push({ type: 'closing', audio: closing.audio, label: 'Closing' });
}

export function start() {
  if (isDialogOpen()) closeExhibit();
  buildQueue();
  running = true;
  paused = false;
  currentStep = -1;
  showControls(true);
  announce('Tour started');
  playNext();
}

function playWelcome() {
  const welcome = getWelcomeData();
  if (!welcome) return;
  player.play(welcome.audio);
}

export function pauseResume() {
  if (!running) return;

  if (pauseTimer) {
    clearTimeout(pauseTimer);
    pauseTimer = null;
  }

  if (paused) {
    paused = false;
    tourPauseBtn.textContent = 'Pause';
    announce('Tour resumed');
    if (player.isPlaying()) return;
    player.resume();
    if (!player.isPlaying()) playNext();
  } else {
    paused = true;
    tourPauseBtn.textContent = 'Resume';
    player.pause();
    announce('Paused');
  }
}

export function skip() {
  if (!running) return;
  if (pauseTimer) {
    clearTimeout(pauseTimer);
    pauseTimer = null;
  }
  player.stop();
  paused = false;
  tourPauseBtn.textContent = 'Pause';
  playNext();
}

export function stop() {
  if (!running) return;
  if (pauseTimer) {
    clearTimeout(pauseTimer);
    pauseTimer = null;
  }
  player.stop();
  running = false;
  paused = false;
  currentStep = -1;
  clearHighlights();
  showControls(false);
  announce('Tour stopped');
}

function playNext() {
  clearHighlights();
  currentStep++;
  if (currentStep >= queue.length) {
    running = false;
    currentStep = -1;
    showControls(false);
    announce('Tour finished');
    return;
  }

  const step = queue[currentStep];
  tourStatus.textContent = `Now playing: ${step.label}`;
  announce(`Now playing ${step.label}`);

  if (step.type === 'exhibit') {
    highlightCard(step.exhibitId);
  }

  player.play(step.audio);
}

function onTrackEnded() {
  if (!running || paused) return;

  clearHighlights();

  if (currentStep >= queue.length - 1) {
    running = false;
    currentStep = -1;
    showControls(false);
    announce('Tour finished');
    return;
  }

  pauseTimer = setTimeout(() => {
    pauseTimer = null;
    if (running && !paused) playNext();
  }, 3000);
}

function highlightCard(exhibitId) {
  const card = getCardByExhibitId(exhibitId);
  if (card) card.classList.add('playing');
}

function clearHighlights() {
  document.querySelectorAll('.card.playing').forEach((c) => c.classList.remove('playing'));
}

function showControls(visible) {
  activeControls.hidden = !visible;
  if (visible) {
    startBtn.hidden = true;
    welcomeBtn.hidden = true;
  } else {
    startBtn.hidden = false;
    welcomeBtn.hidden = false;
    tourStatus.textContent = '';
    tourPauseBtn.textContent = 'Pause';
  }
}

function announce(msg) {
  if (onAnnounce) onAnnounce(msg);
}

export function isRunning() {
  return running;
}

export function handleExhibitOpened() {
  if (running) stop();
}
