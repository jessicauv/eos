const audio = new Audio();
const listeners = new Map();

function emit(event, detail) {
  const fns = listeners.get(event);
  if (fns) fns.forEach((fn) => fn(detail));
}

audio.addEventListener('play', () => emit('started'));
audio.addEventListener('pause', () => {
  if (!audio.ended) emit('paused');
});
audio.addEventListener('ended', () => emit('ended'));
audio.addEventListener('timeupdate', () => {
  emit('timeupdate', {
    current: audio.currentTime,
    duration: audio.duration || 0,
  });
});

export function play(src) {
  if (audio.src !== new URL(src, location.href).href) {
    audio.src = src;
  }
  audio.currentTime = 0;
  audio.play().catch(() => {
    emit('ended');
  });
}

export function pause() {
  if (!audio.paused) audio.pause();
}

export function resume() {
  if (audio.paused && audio.src) audio.play().catch(() => {});
}

export function stop() {
  audio.pause();
  audio.currentTime = 0;
  audio.removeAttribute('src');
  audio.load();
}

export function isPlaying() {
  return !audio.paused && !audio.ended;
}

export function getCurrentSrc() {
  return audio.src;
}

export function on(event, fn) {
  if (!listeners.has(event)) listeners.set(event, new Set());
  listeners.get(event).add(fn);
}

export function off(event, fn) {
  const fns = listeners.get(event);
  if (fns) fns.delete(fn);
}

function formatTime(seconds) {
  const s = Math.floor(seconds);
  const m = Math.floor(s / 60);
  const sec = s % 60;
  return `${m}:${sec.toString().padStart(2, '0')}`;
}

export { formatTime };
