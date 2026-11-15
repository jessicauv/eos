"""
mix.py — Assemble final exhibit audio and LED timelines.

Uses numpy + wave + ffmpeg instead of pydub (broken on Python 3.13).

Structure per exhibit:
  chime → intro → [music alone 15s] → [explanation over ducked music] →
  [music returns 5s, fades] → directions

Usage: python mix.py
"""
import json, os, wave, subprocess, struct
import numpy as np

SR = 44100
MUSIC_SOLO_S = 15.0
TAIL_S = 5.0
DUCK_DB = 0
RAMP_S = 0.6
FADE_OUT_S = 3.0
TARGET_DBFS = -20


def read_wav(path):
    """Read a WAV file, return float64 stereo array (N, 2) at 44100 Hz."""
    with wave.open(path, "r") as wf:
        ch = wf.getnchannels()
        sw = wf.getsampwidth()
        fr = wf.getframerate()
        raw = wf.readframes(wf.getnframes())

    if sw == 2:
        samples = np.frombuffer(raw, dtype=np.int16).astype(np.float64)
    elif sw == 4:
        samples = np.frombuffer(raw, dtype=np.int32).astype(np.float64) / 65536
    else:
        raise ValueError(f"Unsupported sample width {sw} in {path}")

    if ch == 1:
        samples = np.column_stack([samples, samples])
    else:
        samples = samples.reshape(-1, ch)[:, :2]

    if fr != SR:
        n_out = int(len(samples) * SR / fr)
        indices = np.linspace(0, len(samples) - 1, n_out).astype(int)
        samples = samples[indices]

    return samples


def write_wav(path, data):
    """Write float64 stereo array to 16-bit WAV."""
    peak = np.max(np.abs(data))
    if peak > 32767:
        data = data * (32767 / peak)
    int_data = np.clip(data, -32768, 32767).astype(np.int16)
    with wave.open(path, "w") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(SR)
        wf.writeframes(int_data.tobytes())


def silence(seconds):
    return np.zeros((int(seconds * SR), 2), dtype=np.float64)


def fade_out(data, dur_s):
    n = int(dur_s * SR)
    if n > len(data):
        n = len(data)
    env = np.linspace(1.0, 0.0, n)
    data[-n:] *= env[:, None]
    return data


def duck(data, start_s, end_s, db=DUCK_DB, ramp_s=RAMP_S):
    """Lower volume between start_s and end_s with smooth ramps."""
    gain = 10 ** (db / 20)
    env = np.ones(len(data), dtype=np.float64)
    s = int(start_s * SR)
    e = int(end_s * SR)
    r = int(ramp_s * SR)
    env[s:e] = gain
    ramp_start = max(s - r, 0)
    env[ramp_start:s] = np.linspace(1.0, gain, s - ramp_start)
    ramp_end = min(e + r, len(env))
    env[e:ramp_end] = np.linspace(gain, 1.0, ramp_end - e)
    data *= env[:, None]
    return data


def normalize(data, target_dbfs=TARGET_DBFS):
    rms = np.sqrt(np.mean(data ** 2))
    if rms < 1e-10:
        return data
    current_dbfs = 20 * np.log10(rms / 32767)
    gain = 10 ** ((target_dbfs - current_dbfs) / 20)
    return data * gain


def trim_leading_silence(data, threshold=50, min_samples=4410):
    """Remove leading near-silence from audio. Keeps 0.1s before first sound."""
    amplitude = np.max(np.abs(data), axis=1)
    loud = np.where(amplitude > threshold)[0]
    if len(loud) == 0:
        return data
    start = max(0, loud[0] - min_samples)
    return data[start:]


def concat(*arrays):
    return np.concatenate(arrays, axis=0)


def overlay(base, top, offset_samples):
    """Mix top onto base starting at offset_samples."""
    end = offset_samples + len(top)
    if end > len(base):
        base = np.concatenate([base, np.zeros((end - len(base), 2))], axis=0)
    base[offset_samples:offset_samples + len(top)] += top
    return base


def to_mp3(wav_path, mp3_path):
    subprocess.run([
        "ffmpeg", "-y", "-i", wav_path,
        "-codec:a", "libmp3lame", "-b:a", "160k",
        "-loglevel", "quiet", mp3_path,
    ], check=True)
    os.remove(wav_path)


def led_timeline(data, music_start_s, end_s):
    cfg, feats = data["config"], data["features"]
    color = cfg["base_color"]
    step = cfg["step_seconds"]
    frames = [{"t": 0.0, "color": color, "brightness": 0.1}]
    for i, f in enumerate(feats):
        frames.append({
            "t": round(music_start_s + i * step, 2),
            "color": color,
            "brightness": round(0.15 + 0.85 * f["norm"], 2),
        })
    frames.append({"t": round(end_s, 2), "color": color, "brightness": 0.1})
    return {"frames": frames}


def build_exhibit(n, chime, is_last):
    data = json.load(open(f"build/features-{n}.json"))
    intro = read_wav(f"narration/intro-{n}.wav")
    explain = read_wav(f"narration/explain-{n}.wav")
    music = read_wav(f"rendered/music-{n}.wav")

    head = concat(chime, silence(0.3), intro, silence(0.5))
    music_start_s = len(head) / SR

    music = trim_leading_silence(music)

    solo_samples = int(MUSIC_SOLO_S * SR)
    explain_samples = len(explain)
    tail_samples = int(TAIL_S * SR)
    needed = solo_samples + explain_samples + tail_samples

    if len(music) < needed:
        pad = needed - len(music)
        music = np.concatenate([music, silence(pad / SR)], axis=0)
    music = music[:needed].copy()

    fade_out(music, FADE_OUT_S)
    duck(music, MUSIC_SOLO_S, MUSIC_SOLO_S + len(explain) / SR)

    # Lower narration so music stays prominent
    explain = explain * 0.25

    body = overlay(music.copy(), explain, solo_samples)
    out = concat(head, body)

    music_end_s = len(out) / SR

    if not is_last:
        directions = read_wav(f"narration/directions-{n}.wav")
        out = concat(out, silence(0.5), directions)

    out = normalize(out)
    tmp_wav = f"output/audio/exhibit-{n}.wav"
    write_wav(tmp_wav, out)
    to_mp3(tmp_wav, f"output/audio/exhibit-{n}.mp3")

    json.dump(
        led_timeline(data, music_start_s, music_end_s),
        open(f"output/data/led-timeline-{n}.json", "w"),
        indent=1,
    )
    print(f"Exhibit {n}: {len(out)/SR:.0f}s, music at {music_start_s:.1f}s")


def build_simple(name, chime, chime_first=True):
    voice = read_wav(f"narration/{name}.wav")
    if chime_first:
        out = concat(chime, silence(0.3), voice)
    else:
        out = concat(voice, silence(0.5), chime)
    out = normalize(out)
    tmp_wav = f"output/audio/{name}.wav"
    write_wav(tmp_wav, out)
    to_mp3(tmp_wav, f"output/audio/{name}.mp3")
    print(f"{name}: {len(out)/SR:.0f}s")


if __name__ == "__main__":
    os.makedirs("output/audio", exist_ok=True)
    os.makedirs("output/data", exist_ok=True)

    chime = read_wav("assets/chime.wav") * 0.5  # -6dB

    build_simple("welcome", chime, chime_first=True)
    for n in range(1, 5):
        build_exhibit(n, chime, is_last=(n == 4))
    build_simple("closing", chime, chime_first=False)

    print("\nAll files written to output/")
