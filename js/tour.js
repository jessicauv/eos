import * as player from './player.js';
import {
  getExhibits,
  openExhibit,
  closeExhibit,
  isDialogOpen,
  getCurrentExhibitIndex,
  setTourMode,
  setOnTourExit,
} from './exhibits.js';

let running = false;
let advanceTimer = null;
let onAnnounce = null;

const startBtn = document.getElementById('start-tour-btn');

export function init(announceFn) {
  onAnnounce = announceFn;
  startBtn.addEventListener('click', toggle);
  // Closing the dialog (via the X, or Escape) ends the tour.
  setOnTourExit(() => stop({ keepDialog: true }));
  player.on('ended', onTrackEnded);
  // A newly started track (e.g. manual Next/Previous) cancels a pending auto-advance.
  player.on('started', clearAdvanceTimer);
}

function toggle() {
  if (running) stop();
  else start();
}

export function start() {
  const exhibits = getExhibits();
  if (!exhibits.length) return;
  running = true;
  startBtn.setAttribute('aria-pressed', 'true');
  startBtn.textContent = 'Stop guided tour';
  setTourMode(true);
  announce('Guided tour started');
  // Opening the exhibit auto-plays its audio (tour mode).
  openExhibit(exhibits[0].id);
}

export function stop(opts = {}) {
  if (!running) return;
  running = false;
  clearAdvanceTimer();
  startBtn.setAttribute('aria-pressed', 'false');
  startBtn.textContent = 'Start guided tour';
  setTourMode(false);
  announce('Guided tour stopped');
  if (!opts.keepDialog && isDialogOpen()) closeExhibit();
}

function onTrackEnded() {
  if (!running) return;
  const exhibits = getExhibits();
  const idx = getCurrentExhibitIndex();
  if (idx < exhibits.length - 1) {
    // Pause on this exhibit, then move to the next one.
    clearAdvanceTimer();
    advanceTimer = setTimeout(() => {
      advanceTimer = null;
      if (running) openExhibit(exhibits[idx + 1].id);
    }, 2500);
  } else {
    // Last exhibit finished — leave the dialog open so the visitor can read on.
    stop({ keepDialog: true });
  }
}

function clearAdvanceTimer() {
  if (advanceTimer) {
    clearTimeout(advanceTimer);
    advanceTimer = null;
  }
}

function announce(msg) {
  if (onAnnounce) onAnnounce(msg);
}

export function isRunning() {
  return running;
}
