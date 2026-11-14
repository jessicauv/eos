import { loadExhibits, setOnExhibitOpened, setOnExhibitPlay, setOnExhibitStop, openExhibit, closeExhibit, isDialogOpen, getExhibits, getCurrentExhibitIndex } from './exhibits.js';
import * as player from './player.js';
import * as tour from './tour.js';
import * as led from './led.js';
import { announce } from './announcer.js';

const introScreen = document.getElementById('intro-screen');
const museumScreen = document.getElementById('museum-screen');
const enterBtn = document.getElementById('enter-museum-btn');
const dialogPlayBtn = document.getElementById('dialog-play-btn');

function showMuseum() {
  introScreen.classList.remove('active');
  introScreen.hidden = true;
  museumScreen.hidden = false;
  museumScreen.classList.add('active');
  document.getElementById('museum-heading').focus();
}

enterBtn.addEventListener('click', showMuseum);

function isTyping(e) {
  const tag = e.target.tagName;
  return tag === 'INPUT' || tag === 'TEXTAREA' || e.target.isContentEditable;
}

function handleKeydown(e) {
  if (isTyping(e)) return;
  if (museumScreen.hidden) return;

  switch (e.key) {
    case '1':
    case '2':
    case '3':
    case '4': {
      e.preventDefault();
      const id = parseInt(e.key, 10);
      openExhibit(id);
      break;
    }

    case ' ': {
      if (e.target === dialogPlayBtn) return;
      e.preventDefault();
      if (tour.isRunning()) {
        tour.pauseResume();
      } else if (player.isPlaying()) {
        player.pause();
        announce('Paused');
      } else {
        player.resume();
      }
      break;
    }

    case 't':
    case 'T': {
      e.preventDefault();
      if (tour.isRunning()) {
        tour.stop();
      } else {
        tour.start();
      }
      break;
    }

    case 'n':
    case 'N': {
      e.preventDefault();
      if (tour.isRunning()) {
        tour.skip();
      } else if (isDialogOpen()) {
        const exhibits = getExhibits();
        const idx = getCurrentExhibitIndex();
        if (idx < exhibits.length - 1) {
          openExhibit(exhibits[idx + 1].id);
        }
      }
      break;
    }

    case 'p':
    case 'P': {
      e.preventDefault();
      if (isDialogOpen()) {
        const exhibits = getExhibits();
        const idx = getCurrentExhibitIndex();
        if (idx > 0) {
          openExhibit(exhibits[idx - 1].id);
        }
      }
      break;
    }

    case 'Escape': {
      if (isDialogOpen()) {
        e.preventDefault();
        closeExhibit();
      }
      break;
    }

    case '?': {
      e.preventDefault();
      const shortcuts = document.getElementById('shortcuts');
      if (shortcuts) {
        shortcuts.focus();
        shortcuts.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }
      break;
    }
  }
}

document.addEventListener('keydown', handleKeydown);

async function init() {
  await loadExhibits();
  tour.init(announce, (id) => led.setActiveExhibit(id), () => led.clearActiveExhibit());
  await led.init();
  setOnExhibitOpened(() => tour.handleExhibitOpened());
  setOnExhibitPlay((id) => led.setActiveExhibit(id));
  setOnExhibitStop(() => led.clearActiveExhibit());
  enterBtn.focus();
}

init();
