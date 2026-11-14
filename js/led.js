import * as player from './player.js';
import { getExhibits, getCardByExhibitId } from './exhibits.js';

const timelineCache = new Map();
let activeExhibitId = null;
let reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

window.matchMedia('(prefers-reduced-motion: reduce)').addEventListener('change', (e) => {
  reducedMotion = e.matches;
});

export async function init() {
  const exhibits = getExhibits();
  for (const ex of exhibits) {
    if (ex.ledTimeline) {
      try {
        const res = await fetch(ex.ledTimeline);
        if (res.ok) {
          const data = await res.json();
          timelineCache.set(ex.id, data.frames);
        }
      } catch {
        // Timeline not available, glow falls back to static color
      }
    }
  }

  player.on('timeupdate', onTimeUpdate);
  player.on('ended', onEnded);
}

function onTimeUpdate({ current }) {
  if (reducedMotion || activeExhibitId === null) return;

  const frames = timelineCache.get(activeExhibitId);
  if (!frames || frames.length === 0) return;

  const frame = getFrame(frames, current);
  if (!frame) return;

  const card = getCardByExhibitId(activeExhibitId);
  if (!card) return;

  const [r, g, b] = frame.color;
  const brightness = frame.brightness;
  card.classList.add('led-active');
  card.style.setProperty('--glow-color', `rgb(${r}, ${g}, ${b})`);
  card.style.setProperty('--glow-brightness', brightness);
}

function onEnded() {
  resetGlow();
  activeExhibitId = null;
}

function getFrame(frames, time) {
  if (time <= frames[0].t) return frames[0];
  if (time >= frames[frames.length - 1].t) return frames[frames.length - 1];

  for (let i = 0; i < frames.length - 1; i++) {
    if (time >= frames[i].t && time < frames[i + 1].t) {
      const a = frames[i];
      const b = frames[i + 1];
      const progress = (time - a.t) / (b.t - a.t);
      return {
        color: [
          Math.round(a.color[0] + (b.color[0] - a.color[0]) * progress),
          Math.round(a.color[1] + (b.color[1] - a.color[1]) * progress),
          Math.round(a.color[2] + (b.color[2] - a.color[2]) * progress),
        ],
        brightness: a.brightness + (b.brightness - a.brightness) * progress,
      };
    }
  }
  return frames[frames.length - 1];
}

function resetGlow() {
  if (activeExhibitId === null) return;
  const card = getCardByExhibitId(activeExhibitId);
  if (!card) return;
  card.classList.remove('led-active');
  const exhibits = getExhibits();
  const ex = exhibits.find((e) => e.id === activeExhibitId);
  if (ex) {
    card.style.setProperty('--glow-color', ex.glowColor);
  }
  card.style.removeProperty('--glow-brightness');
}

export function setActiveExhibit(id) {
  if (activeExhibitId !== null && activeExhibitId !== id) {
    resetGlow();
  }
  activeExhibitId = id;
}

export function clearActiveExhibit() {
  resetGlow();
  activeExhibitId = null;
}
