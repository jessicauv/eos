import json, sys, os, random, math
import pretty_midi
from pretty_midi import Note, ControlChange

random.seed(42)

ROOT = 62  # D4
PENTA = {0, 2, 4, 7, 9}
SCALE = [n for n in range(48, 80) if (n - ROOT) % 12 in PENTA]
LOW_SCALE = [n for n in range(36, 56) if (n - ROOT) % 12 in PENTA]
DEEP_SCALE = [n for n in range(24, 44) if (n - ROOT) % 12 in PENTA]

MAJOR = [[50, 57, 62, 66], [43, 55, 59, 62], [47, 54, 59, 62], [45, 52, 57, 61]]
TENSE = [[47, 54, 59, 62], [40, 52, 55, 59], [43, 55, 59, 62], [45, 52, 57, 61]]


def h(t, spread=0.06):
    return max(0, t + random.uniform(-spread, spread))


def hv(v, spread=8):
    return max(1, min(127, v + random.randint(-spread, spread)))


def constrain_pitch(target_idx, prev_pitch, scale=SCALE, max_leap=2):
    if prev_pitch is None:
        return max(0, min(len(scale) - 1, target_idx))
    prev_idx = min(range(len(scale)), key=lambda k: abs(scale[k] - prev_pitch))
    clamped = max(prev_idx - max_leap, min(prev_idx + max_leap, target_idx))
    return max(0, min(len(scale) - 1, clamped))


def pitch_bend_glide(inst, t_start, t_end, steps=20):
    """Add pitch bend events that glide from current to next note."""
    for i in range(steps):
        t = t_start + (t_end - t_start) * i / steps
        bend = int(8192 * math.sin(math.pi * i / steps) * 0.3)
        inst.pitch_bends.append(pretty_midi.PitchBend(bend, t))
    inst.pitch_bends.append(pretty_midi.PitchBend(0, t_end))


# ═══════════════════════════════════════════════════════════════
# EXHIBIT 1 — "LULLABY OF CIVILIZATION"
# Solo voice emerges, civilization grows, lights go dark
# ═══════════════════════════════════════════════════════════════

def build_choral(cfg, feats):
    step = cfg["step_seconds"]
    n = len(feats)
    pm = pretty_midi.PrettyMIDI(initial_tempo=60)

    soprano = pretty_midi.Instrument(program=52, name="Soprano")
    alto = pretty_midi.Instrument(program=52, name="Alto")
    tenor = pretty_midi.Instrument(program=53, name="Tenor")
    bass_voice = pretty_midi.Instrument(program=53, name="Bass")
    pad = pretty_midi.Instrument(program=52, name="Choir pad")

    # Expression: start from near-silence, build with the data
    max_coverage = max(f["coverage"] for f in feats) or 1.0
    for i, f in enumerate(feats):
        t = i * step
        global_expr = int(40 + 80 * (f["coverage"] / max_coverage))
        soprano.control_changes.append(ControlChange(11, min(120, max(25, global_expr)), t))
        alto.control_changes.append(ControlChange(11, min(110, max(20, global_expr - 10)), t))
        tenor.control_changes.append(ControlChange(11, min(100, max(20, global_expr - 15)), t))

    prev_pitch = None
    for i, f in enumerate(feats):
        t = i * step
        pan = int(127 * i / max(n - 1, 1))
        soprano.control_changes.append(ControlChange(10, pan, t))
        alto.control_changes.append(ControlChange(10, max(0, pan - 12), t))
        tenor.control_changes.append(ControlChange(10, min(127, pan + 12), t))

        # ── Empty bands (ocean): held breath, single quiet bass note ──
        if f["coverage"] == 0:
            bass_voice.notes.append(Note(hv(20), 38, h(t, 0.03), t + step * 1.8))
            prev_pitch = None
            continue

        idx = constrain_pitch(int(f["norm"] * (len(SCALE) - 1)), prev_pitch)
        pitch = SCALE[idx]
        prev_pitch = pitch
        coverage = f["coverage"]
        tension = f["tension"]
        base_vel = 35 + int(30 * f["norm"])

        # ── Voice count grows with coverage: solo → duet → trio → full ──
        voice_count = max(1, min(4, int(coverage / (max_coverage / 4)) + 1))
        dur = step * 2.8 if i % 4 != 3 else step * 1.8  # breath gap

        # ── Tension drives character ──
        # High tension (purple/decrease): thin, trembling, minor
        # Low tension (orange/growth): warm, full, major
        if tension > 0.5:
            # Vigil mode: single voice, quieter, minor feel
            soprano.notes.append(Note(hv(max(25, base_vel - 15)), pitch, h(t), t + dur))
            # Tremolo via rapid velocity oscillation (slight pitch wobble)
            if tension > 0.7:
                for wobble in range(4):
                    wt = t + wobble * 0.3
                    bend = int(800 * math.sin(wobble * 2.5))
                    soprano.pitch_bends.append(pretty_midi.PitchBend(bend, wt))
                soprano.pitch_bends.append(pretty_midi.PitchBend(0, t + dur))
        else:
            # Growing light: voices enter one by one
            soprano.notes.append(Note(hv(base_vel + 8), pitch, h(t), t + dur))

            if voice_count >= 2:
                alto_idx = max(0, idx - 2)
                alto.notes.append(Note(
                    hv(base_vel), SCALE[alto_idx],
                    h(t + 0.1), t + dur - 0.1
                ))

            if voice_count >= 3:
                tenor_idx = max(0, idx - 4)
                tenor.notes.append(Note(
                    hv(base_vel - 5), SCALE[tenor_idx],
                    h(t + 0.2), t + dur - 0.15
                ))

            if voice_count >= 4:
                bass_voice.notes.append(Note(
                    hv(base_vel - 10), LOW_SCALE[min(len(LOW_SCALE) - 1, max(0, idx // 2))],
                    h(t + 0.25), t + dur - 0.2
                ))

        # ── Background chord (quieter, shifts with tension) ──
        if i % 4 == 0:
            section = feats[i:i + 4]
            avg_tension = sum(s["tension"] for s in section) / len(section)
            chords = TENSE if avg_tension > 0.4 else MAJOR
            chord = chords[(i // 4) % 4]
            ct0 = i * step
            ct1 = min((i + 4) * step, n * step)
            chord_vel = 18 + int(15 * (1 - avg_tension))
            for j, p in enumerate(chord):
                pad.notes.append(Note(hv(chord_vel), p, h(ct0 + j * 0.1, 0.04), ct1 + 0.4))

    # ── Ending: don't resolve — hold the last tension ──
    last_tension = feats[-1]["tension"] if feats[-1]["coverage"] > 0 else 0.5
    ft = n * step
    if last_tension > 0.4:
        # Unresolved: minor cluster, fading
        for p in TENSE[0]:
            pad.notes.append(Note(20, p, ft, ft + 5.0))
    else:
        # Warm but still open (no perfect cadence)
        for p in [50, 57, 64]:  # D sus — no third, unresolved
            pad.notes.append(Note(22, p, ft, ft + 5.0))

    pm.instruments += [bass_voice, pad, tenor, alto, soprano]
    return pm


# ═══════════════════════════════════════════════════════════════
# EXHIBIT 2 — "BREATH OF THE DEEP"
# Flowing, gliding, vast — warmth as beauty and warning
# ═══════════════════════════════════════════════════════════════

def build_fluid(cfg, feats):
    step = cfg["step_seconds"]
    n = len(feats)
    pm = pretty_midi.PrettyMIDI(initial_tempo=60)

    sweep = pretty_midi.Instrument(program=95, name="Deep current")    # Pad: Sweep
    warm_voice = pretty_midi.Instrument(program=52, name="Warm voice") # Choir Aahs
    detune = pretty_midi.Instrument(program=52, name="Detune voice")   # Choir Aahs (detuned)
    deep = pretty_midi.Instrument(program=53, name="Deep bass")        # Voice Oohs
    sparkle = pretty_midi.Instrument(program=10, name="Sparkle")       # Music Box
    strings = pretty_midi.Instrument(program=49, name="Strings")       # String Ensemble

    # ── Deep ocean rumble: barely audible low D, constant presence ──
    for chunk in range(0, n, 8):
        t0 = chunk * step
        t1 = min((chunk + 8) * step, n * step)
        deep.notes.append(Note(hv(18), 26, h(t0, 0.03), t1 + 1.0))  # D1
        deep.notes.append(Note(hv(14), 33, h(t0 + 0.2, 0.03), t1 + 0.8))  # A1

    # ── Breathing expression: ocean swells ──
    for i in range(n):
        t = i * step
        # Slow inhale-exhale over 8-beat cycles
        breath_phase = (i % 8) / 8.0
        if breath_phase < 0.45:
            expr = int(35 + 55 * (breath_phase / 0.45))
        elif breath_phase < 0.55:
            expr = 90  # hold at peak
        else:
            expr = int(90 - 50 * ((breath_phase - 0.55) / 0.45))
        sweep.control_changes.append(ControlChange(11, max(25, min(100, expr)), t))
        warm_voice.control_changes.append(ControlChange(11, max(20, min(90, expr - 5)), t))

    # ── Strings: slow harmonic foundation ──
    for i in range(0, n, 6):
        t0 = i * step
        t1 = min((i + 6) * step, n * step)
        section = feats[i:min(i + 6, n)]
        avg_norm = sum(s["norm"] for s in section) / len(section)
        chord = MAJOR[(i // 6) % 4]
        vel = 20 + int(15 * avg_norm)
        for j, p in enumerate(chord):
            strings.notes.append(Note(hv(vel), p, h(t0 + j * 0.15, 0.05), t1 + 1.2))

    # ── Main voices: flowing, gliding, with call-and-response ──
    prev_pitch = None
    prev_t = 0
    for i, f in enumerate(feats):
        t = i * step
        pan = int(127 * i / max(n - 1, 1))
        sweep.control_changes.append(ControlChange(10, pan, t))
        warm_voice.control_changes.append(ControlChange(10, min(127, pan + 20), t))

        if f["coverage"] == 0:
            prev_pitch = None
            continue

        # Very smooth: max 1 step leap
        idx = constrain_pitch(int(f["norm"] * (len(SCALE) - 1)), prev_pitch, max_leap=1)
        pitch = SCALE[idx]
        base_vel = 35 + int(25 * f["norm"])

        # ── Pitch bend glide from previous note ──
        if prev_pitch is not None and prev_pitch != pitch:
            pitch_bend_glide(sweep, prev_t + step * 0.8, t + 0.1)

        prev_pitch = pitch
        prev_t = t

        # Main sweep voice: very long, overlapping
        sweep.notes.append(Note(hv(base_vel), pitch, h(t, 0.04), t + step * 4.0))

        # ── Call and response: low voice answers high ──
        low_idx = max(0, idx - 4)
        warm_voice.notes.append(Note(
            hv(base_vel - 8), SCALE[low_idx],
            h(t + step * 0.6, 0.05),  # delayed answer
            t + step * 3.5
        ))

        # ── Detuned voice on warm temperatures: beauty with unease ──
        if f["norm"] > 0.55:
            detune.notes.append(Note(
                hv(base_vel - 12), pitch,
                h(t + 0.05, 0.03), t + step * 3.0
            ))
            # Detune by ~20 cents sharp via pitch bend
            cents_20 = int(8192 * 20 / 200)
            detune.pitch_bends.append(pretty_midi.PitchBend(cents_20, t))

        # ── Sparkle on warm peaks ──
        if f["norm"] > 0.65:
            sp_idx = min(len(SCALE) - 1, idx + 5)
            sparkle.notes.append(Note(hv(30), SCALE[sp_idx], h(t + 0.8, 0.1), t + 2.0))
            # Second sparkle echo
            if f["norm"] > 0.75:
                sparkle.notes.append(Note(hv(22), SCALE[min(len(SCALE) - 1, sp_idx + 2)],
                                          h(t + 1.5, 0.1), t + 2.8))

    # ── Ending: the ocean continues, we just stop listening ──
    ft = n * step
    sweep.notes.append(Note(20, SCALE[3], ft, ft + 7.0))
    deep.notes.append(Note(15, 26, ft, ft + 8.0))
    warm_voice.notes.append(Note(18, SCALE[0], ft + 0.5, ft + 6.0))

    pm.instruments += [deep, strings, sweep, warm_voice, detune, sparkle]
    return pm


# ═══════════════════════════════════════════════════════════════
# EXHIBIT 3 — "THE WEIGHT OF THE AIR"
# Accumulating, suffocating, relentless — no resolution
# ═══════════════════════════════════════════════════════════════

def build_industrial(cfg, feats):
    step = cfg["step_seconds"]
    n = len(feats)
    pm = pretty_midi.PrettyMIDI(initial_tempo=60)

    lead = pretty_midi.Instrument(program=81, name="Saw lead")
    lead_detune = pretty_midi.Instrument(program=81, name="Saw detune")
    atmo = pretty_midi.Instrument(program=94, name="Halo pad")
    bass = pretty_midi.Instrument(program=39, name="Synth bass 2")
    accumulate = pretty_midi.Instrument(program=92, name="Accumulate")  # Pad: Space Voice
    metal = pretty_midi.Instrument(program=14, name="Tubular bells")
    taiko = pretty_midi.Instrument(program=116, name="Taiko", is_drum=False)

    # ── Dynamics: start near-silent, build relentlessly ──
    for i, f in enumerate(feats):
        t = i * step
        progress = i / max(n - 1, 1)
        # Never go back down — only up. Like CO2 itself.
        base_expr = int(20 + 90 * progress)
        lead.control_changes.append(ControlChange(11, min(120, base_expr), t))
        lead.control_changes.append(ControlChange(7, min(120, base_expr), t))  # volume too

    # ── Accelerating pulse: heartbeat speeds up with concentration ──
    for i, f in enumerate(feats):
        t = i * step
        # Pulse rate increases with norm: 1 hit at low, up to 4 at high
        pulses = max(1, int(1 + 3 * f["norm"]))
        pulse_vel = 25 + int(25 * f["norm"])
        for p in range(pulses):
            pt = t + p * (step / pulses) * 0.9
            bass.notes.append(Note(hv(pulse_vel), 38, h(pt, 0.02), pt + step / pulses * 0.6))

    # ── Atmospheric pad: increasingly dissonant ──
    for i in range(0, n, 3):
        t0 = i * step
        t1 = min((i + 3) * step, n * step)
        section = feats[i:min(i + 3, n)]
        avg_norm = sum(s["norm"] for s in section) / len(section)
        progress = i / max(n - 1, 1)

        if avg_norm > 0.7 or progress > 0.7:
            # Dissonant cluster: minor seconds
            chord = [50, 51, 56, 63]  # D Eb Gb Eb8 — grinding
        elif avg_norm > 0.4 or progress > 0.4:
            chord = TENSE[(i // 3) % 4]
        else:
            chord = MAJOR[(i // 3) % 4]

        vel = 15 + int(20 * progress)
        for j, p in enumerate(chord):
            atmo.notes.append(Note(hv(vel), p, h(t0 + j * 0.08, 0.04), t1 + 1.0))

    # ── Accumulation layer: notes that NEVER fully fade ──
    # Each high-concentration frame adds a sustained tone
    active_tones = []
    for i, f in enumerate(feats):
        t = i * step
        if f["norm"] > 0.3:
            # Add a new sustained tone — stays for the rest of the piece
            acc_pitch = SCALE[int(f["norm"] * (len(SCALE) - 1))]
            remain = (n * step + 3.0) - t  # sustain to the very end
            vel = max(8, int(10 + 12 * f["norm"]))
            accumulate.notes.append(Note(vel, acc_pitch, h(t, 0.05), t + remain))
            active_tones.append(acc_pitch)

    # ── Lead melody: saw wave, short and rhythmic ──
    prev_pitch = None
    for i, f in enumerate(feats):
        t = i * step

        if f["coverage"] == 0:
            prev_pitch = None
            continue

        idx = constrain_pitch(int(f["norm"] * (len(SCALE) - 1)), prev_pitch, max_leap=3)
        pitch = SCALE[idx]
        prev_pitch = pitch
        progress = i / max(n - 1, 1)
        base_vel = int(30 + 50 * progress * f["norm"])

        lead.notes.append(Note(hv(base_vel), pitch, h(t), t + step * 1.4))

        # ── Detuned double at high concentration: physical discomfort ──
        if f["norm"] > 0.5:
            lead_detune.notes.append(Note(
                hv(max(20, base_vel - 10)), pitch,
                h(t + 0.03), t + step * 1.3
            ))
            # ~20 cents sharp
            cents = int(8192 * (15 + 10 * f["norm"]) / 200)
            lead_detune.pitch_bends.append(pretty_midi.PitchBend(cents, t))

        # Echo that builds density
        if f["norm"] > 0.4:
            echo_idx = min(len(SCALE) - 1, idx + 1)
            lead.notes.append(Note(hv(max(15, base_vel - 18)), SCALE[echo_idx],
                                   h(t + step * 0.6), t + step * 1.6))

        # ── Taiko on concentration peaks ──
        if f["norm"] > 0.75:
            taiko.notes.append(Note(hv(50 + int(20 * progress)), 50, h(t, 0.02), t + 0.6))

        # ── Tubular bells: alarm at highest peaks ──
        if f["norm"] > 0.9:
            metal.notes.append(Note(hv(40), SCALE[min(len(SCALE) - 1, idx + 4)],
                                    h(t + 0.1), t + 2.5))

    # ── Ending: NO RESOLUTION. Abrupt stop on dense cluster. ──
    ft = n * step
    # One final dissonant chord, no fade — the CO2 stays
    for p in [50, 51, 57, 58, 63]:
        atmo.notes.append(Note(30, p, ft, ft + 0.8))
    # Then a single high tone that sustains — the ringing in your ears
    lead.notes.append(Note(25, SCALE[-2], ft + 1.0, ft + 6.0))

    pm.instruments += [bass, atmo, accumulate, lead, lead_detune, taiko, metal]
    return pm


# ═══════════════════════════════════════════════════════════════
# EXHIBIT 4 — "STORM SYMPHONY"
# Silence, anticipation, explosive bursts, raw energy
# ═══════════════════════════════════════════════════════════════

def build_electric(cfg, feats):
    step = cfg["step_seconds"]
    n = len(feats)
    pm = pretty_midi.PrettyMIDI(initial_tempo=60)

    guitar = pretty_midi.Instrument(program=29, name="Lightning")      # Overdriven Guitar
    hum = pretty_midi.Instrument(program=90, name="Atmosphere")        # Pad: Polysynth
    bass = pretty_midi.Instrument(program=36, name="Thunder bass")     # Slap Bass 1
    taiko = pretty_midi.Instrument(program=116, name="Taiko", is_drum=False)
    cymbal = pretty_midi.Instrument(program=119, name="Cymbal", is_drum=False)
    crackle = pretty_midi.Instrument(program=29, name="Crackle")       # Overdriven Guitar (high)

    # ── Background atmospheric hum: quiet, ominous, always present ──
    for chunk in range(0, n, 6):
        t0 = chunk * step
        t1 = min((chunk + 6) * step, n * step)
        section = feats[chunk:min(chunk + 6, n)]
        avg_norm = sum(s["norm"] for s in section) / len(section)
        hum_vel = 12 + int(15 * avg_norm)
        hum.notes.append(Note(hv(hum_vel), 38, h(t0, 0.04), t1 + 0.5))  # D2
        hum.notes.append(Note(hv(max(8, hum_vel - 5)), 45, h(t0 + 0.2, 0.04), t1 + 0.3))  # A2

    # ── Pan jumps: lightning comes from random directions ──
    pan_positions = [random.randint(10, 117) for _ in range(n)]

    prev_pitch = None
    for i, f in enumerate(feats):
        t = i * step
        is_event = cfg.get("events") and f["norm"] >= cfg["event_threshold"]

        # Jumping pan
        guitar.control_changes.append(ControlChange(10, pan_positions[i], t))
        crackle.control_changes.append(ControlChange(10, 127 - pan_positions[i], t))

        # ── Silence for quiet frames: the dark between flashes ──
        if f["norm"] < 0.15:
            prev_pitch = None
            # Just the atmospheric hum — nothing else
            continue

        idx = constrain_pitch(int(f["norm"] * (len(SCALE) - 1)), prev_pitch, max_leap=4)
        pitch = SCALE[idx]
        prev_pitch = pitch
        base_vel = 40 + int(45 * f["norm"])

        if is_event:
            # ═══ LIGHTNING FLASH: simultaneous explosion ═══

            # Taiko thunder hit
            taiko.notes.append(Note(hv(80), 50, h(t, 0.01), t + 0.9))
            # Second taiko for rumble
            taiko.notes.append(Note(hv(55), 47, h(t + 0.15, 0.02), t + 0.7))

            # Reverse cymbal swell (if room)
            if t > 0.8:
                cymbal.notes.append(Note(hv(55), 55, t - 0.8, t + 0.2))

            # Guitar stab — loud, short
            guitar.notes.append(Note(hv(min(120, base_vel + 25)), pitch, h(t, 0.02), t + step * 0.5))

            # ── Electrical crackle: rapid 32nd-note cluster ──
            for j in range(6):
                ct = t + j * 0.08
                cp = SCALE[min(len(SCALE) - 1, idx + random.randint(0, 5))]
                crackle.notes.append(Note(
                    hv(max(30, base_vel - j * 8)),  # rapid decay
                    cp, h(ct, 0.01), ct + 0.12
                ))

            # Bass thunder: deep slam
            bass.notes.append(Note(hv(75), LOW_SCALE[min(len(LOW_SCALE) - 1, idx // 2)],
                                   h(t, 0.02), t + step * 0.8))

            # Rapid decay to silence — the flash is over
            guitar.control_changes.append(ControlChange(11, 120, t))
            guitar.control_changes.append(ControlChange(11, 30, t + step * 0.5))

        else:
            # ── Non-event: quieter, more distant ──
            # Distant flash: softer, longer decay
            flash_vel = max(25, int(base_vel * 0.6))
            guitar.notes.append(Note(hv(flash_vel), pitch, h(t, 0.03), t + step * 0.7))

            # Occasional bass rumble
            if f["norm"] > 0.3 and i % 2 == 0:
                bass.notes.append(Note(
                    hv(max(20, flash_vel - 15)),
                    LOW_SCALE[min(len(LOW_SCALE) - 1, idx // 2)],
                    h(t + 0.1, 0.03), t + step * 0.6
                ))

    # ── Ending: one final strike, then silence ──
    ft = n * step
    taiko.notes.append(Note(70, 50, ft, ft + 1.2))
    guitar.notes.append(Note(80, SCALE[-3], ft, ft + 0.4))
    # Long atmospheric decay — the storm passes
    hum.notes.append(Note(15, 38, ft + 0.5, ft + 6.0))

    pm.instruments += [hum, bass, guitar, crackle, taiko, cymbal]
    return pm


# ═══════════════════════════════════════════════════════════════
# DISPATCH
# ═══════════════════════════════════════════════════════════════

BUILDERS = {
    1: build_choral,
    2: build_fluid,
    3: build_industrial,
    4: build_electric,
}

if __name__ == "__main__":
    data = json.load(open(sys.argv[1]))
    cfg, feats = data["config"], data["features"]
    exhibit_id = cfg["id"]

    builder = BUILDERS.get(exhibit_id)
    if not builder:
        print(f"No builder for exhibit {exhibit_id}")
        sys.exit(1)

    pm = builder(cfg, feats)
    os.makedirs("build", exist_ok=True)
    out = f"build/exhibit-{exhibit_id}.mid"
    pm.write(out)
    total_notes = sum(len(i.notes) for i in pm.instruments)
    print(f"Saved {out} ({pm.get_end_time():.0f} s, {total_notes} notes)")
