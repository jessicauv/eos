import os, wave
import numpy as np

sr, dur = 44100, 1.5
t = np.linspace(0, dur, int(sr * dur), endpoint=False)
tone = sum(np.sin(2 * np.pi * f * t) * a for f, a in [(880, 1.0), (1320, 0.4), (1760, 0.2)])
tone *= np.exp(-3 * t) * 0.3
samples = (tone / np.max(np.abs(tone)) * 0.5 * 32767).astype(np.int16)

os.makedirs("assets", exist_ok=True)
with wave.open("assets/chime.wav", "w") as wf:
    wf.setnchannels(1)
    wf.setsampwidth(2)
    wf.setframerate(sr)
    wf.writeframes(samples.tobytes())
print("Saved assets/chime.wav")
