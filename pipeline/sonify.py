import json, sys, os
import pretty_midi
from pretty_midi import Note, ControlChange

ROOT = 62                                  # D
PENTA = {0, 2, 4, 7, 9}
SCALE = [n for n in range(48, 80) if (n - ROOT) % 12 in PENTA]
MAJOR = [[50, 57, 62, 66], [43, 55, 59, 62], [47, 54, 59, 62], [45, 52, 57, 61]]  # D G Bm A
TENSE = [[47, 54, 59, 62], [40, 52, 55, 59], [43, 55, 59, 62], [45, 52, 57, 61]]  # Bm Em G A

def build(data):
    cfg, feats = data["config"], data["features"]
    step = cfg["step_seconds"]
    pm = pretty_midi.PrettyMIDI(initial_tempo=60)
    lead = pretty_midi.Instrument(program=52, name="Choir lead")   # GM Choir Aahs
    pad = pretty_midi.Instrument(program=53, name="Choir pad")     # GM Voice Oohs
    bells = pretty_midi.Instrument(program=8, name="Bells")        # GM Celesta

    for i, f in enumerate(feats):
        t = i * step

        if i % 4 == 0:
            section = feats[i:i + 4]
            tension = sum(s["tension"] for s in section) / len(section)
            chords = TENSE if tension > 0.5 else MAJOR
            for p in chords[(i // 4) % 4]:
                pad.notes.append(Note(38, p, t, t + 4 * step))

        pan = int(127 * i / max(len(feats) - 1, 1))
        lead.control_changes.append(ControlChange(10, pan, t))

        if f["coverage"] == 0:
            continue

        top = int(f["norm"] * (len(SCALE) - 1))
        voices = 1 + round(min(f["coverage"], 1.0) * 3)
        velocity = 45 + int(30 * f["norm"])
        for k in range(voices):
            p = SCALE[max(0, top - 2 * k)]
            lead.notes.append(Note(velocity, p, t, t + step * 1.5))

        if cfg.get("events") and f["norm"] >= cfg["event_threshold"]:
            for j in range(3):
                bt = t + j * step / 3
                bells.notes.append(Note(50, SCALE[-1 - j], bt, bt + 0.6))

    pm.instruments += [pad, lead, bells]
    return pm

if __name__ == "__main__":
    data = json.load(open(sys.argv[1]))
    pm = build(data)
    os.makedirs("build", exist_ok=True)
    out = f"build/exhibit-{data['config']['id']}.mid"
    pm.write(out)
    print(f"Saved {out} ({pm.get_end_time():.0f} s)")
