import sys, os, subprocess, glob

SOUNDFONT_SEARCH = [
    "assets/*.sf3",
    "assets/*.sf2",
    "/opt/homebrew/Cellar/fluid-synth/*/share/fluid-synth/sf2/*.sf2",
    "/usr/share/sounds/sf2/*.sf2",
    "/usr/local/share/fluidsynth/*.sf2",
]

def find_soundfont():
    for pattern in SOUNDFONT_SEARCH:
        matches = sorted(glob.glob(pattern))
        if matches:
            return matches[0]
    return None

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python render.py build/exhibit-1.mid rendered/music-1.wav")
        sys.exit(1)

    mid_path, wav_path = sys.argv[1], sys.argv[2]
    os.makedirs(os.path.dirname(wav_path), exist_ok=True)

    sf = find_soundfont()
    if not sf:
        print("Error: no soundfont found. Place a .sf2 file in assets/")
        sys.exit(1)
    print(f"Using soundfont: {sf}")

    subprocess.run([
        "fluidsynth", "-ni",
        "-F", wav_path, "-r", "44100",
        "-o", "synth.reverb.active=yes",
        "-o", "synth.reverb.room-size=0.6",
        "-o", "synth.chorus.active=yes",
        sf, mid_path,
    ], check=True)
    print(f"Rendered {wav_path}")
