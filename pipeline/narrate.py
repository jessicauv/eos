"""Generate all narration WAVs using Microsoft edge-tts (GuyNeural voice)."""
import os, subprocess, asyncio
import edge_tts

VOICE = "en-US-GuyNeural"

WELCOME = (
    "Welcome to Eos, a museum where you can hear our changing planet. "
    "This museum has four exhibits, each turning NASA satellite data into music. "
    "You'll hear how city lights have changed, how oceans are warming, "
    "how carbon dioxide ebbs and flows, and where lightning strikes around the world. "
    "Each exhibit plays a short piece of music with a spoken explanation. "
    "Use the keyboard shortcuts or tab through the controls to explore. "
    "Enjoy your visit."
)

CLOSING = (
    "Thank you for visiting Eos. Every sound you heard was shaped by real NASA data, "
    "measurements taken from satellites orbiting hundreds of miles above us, "
    "turned into music so you could hear what our planet is going through. "
    "I hope it gave you a new way to feel the changes happening on Earth. "
    "Safe travels."
)

INTROS = {
    1: "Exhibit 1: Earth's Night Lights. You're looking at a map of every artificial light visible from space, comparing 2012 to 2023.",
    2: "Exhibit 2: Ocean Temperatures. The ocean covers 70 percent of Earth's surface and has absorbed over 90 percent of the extra heat trapped by greenhouse gases.",
    3: "Exhibit 3: Carbon Dioxide. Every year, Earth breathes. In spring, forests pull carbon dioxide out of the air. In winter, they release it back.",
    4: "Exhibit 4: Lightning. Right now, roughly 45 bolts of lightning are striking the Earth every second. This piece maps where they fall.",
}

EXPLAINS = {
    1: (
        "In the music, each voice in the choir represents a region of the globe. "
        "Where lights grew brighter, more voices join and the pitch rises. "
        "Where lights dimmed, sometimes from conflict, sometimes from disaster, "
        "the harmony shifts to minor chords and the voice trembles. "
        "Listen for the contrast between the growing glow of India "
        "and the darkened patches over Syria. "
        "The music scans from west to east across the planet, "
        "so the choir builds as it passes through the most populated regions."
    ),
    2: (
        "A deep bass drone represents the ocean's cold depths. "
        "Flowing voices glide between notes like currents, "
        "breathing in and out in slow swells. "
        "Where the water is warmer, a detuned second voice enters, "
        "creating a shimmer that's beautiful but unsettling. "
        "Bright sparkles mark the hottest surface temperatures. "
        "The piece scans from the cool Atlantic through the warm tropics "
        "to the vast Pacific. Notice how the warmth never really fades. "
        "The ocean remembers every degree."
    ),
    3: (
        "A steady bass pulse represents the seasonal cycle, Earth breathing in and out. "
        "But that pulse accelerates as concentration rises. "
        "The lead tone only climbs, it never comes back down, "
        "and each new high note stays, accumulating like the gas itself. "
        "The chords grow increasingly dissonant as we pass 400 parts per million. "
        "Taiko drums mark the highest concentration peaks. "
        "And at the end, there is no resolution. "
        "The music simply stops, because the CO2 doesn't."
    ),
    4: (
        "The piece begins in near silence, the dark sky between flashes. "
        "When lightning strikes, you hear an explosion: "
        "a taiko drum for thunder, a guitar stab for the bolt, "
        "and a rapid crackle of electrical energy that decays in milliseconds. "
        "Each flash comes from a different direction in the stereo field. "
        "The densest cluster is the Congo Basin, "
        "the single most electric place on Earth. "
        "Notice the silence between strikes. "
        "Lightning is violent but brief, and the darkness always returns."
    ),
}

DIRECTIONS = {
    1: "Exhibit 2, Ocean Temperatures, is next.",
    2: "Exhibit 3, Carbon Dioxide, is next.",
    3: "Exhibit 4, Lightning, is the final exhibit.",
}


async def tts_to_wav(text, out_path, retries=3):
    """Generate speech with edge-tts, convert MP3 output to WAV."""
    if os.path.exists(out_path) and os.path.getsize(out_path) > 1000:
        size = os.path.getsize(out_path)
        print(f"  {out_path} ({size // 1024}K) [cached]")
        return

    mp3_path = out_path.replace(".wav", ".mp3")
    for attempt in range(retries):
        try:
            await asyncio.sleep(1.5)
            communicate = edge_tts.Communicate(text, VOICE)
            await communicate.save(mp3_path)
            break
        except Exception as e:
            if attempt < retries - 1:
                wait = 3 * (attempt + 1)
                print(f"    retry {attempt + 1} in {wait}s: {e}")
                await asyncio.sleep(wait)
            else:
                raise

    subprocess.run(
        ["ffmpeg", "-y", "-i", mp3_path, "-ar", "44100", "-ac", "1",
         "-loglevel", "quiet", out_path],
        check=True,
    )
    os.remove(mp3_path)
    size = os.path.getsize(out_path)
    print(f"  {out_path} ({size // 1024}K)")


async def main():
    os.makedirs("narration", exist_ok=True)

    print("Generating welcome + closing...")
    await tts_to_wav(WELCOME, "narration/welcome.wav")
    await tts_to_wav(CLOSING, "narration/closing.wav")

    for n in range(1, 5):
        print(f"\nExhibit {n}:")
        await tts_to_wav(INTROS[n], f"narration/intro-{n}.wav")
        await tts_to_wav(EXPLAINS[n], f"narration/explain-{n}.wav")
        if n in DIRECTIONS:
            await tts_to_wav(DIRECTIONS[n], f"narration/directions-{n}.wav")

    print("\nDone — all narration WAVs generated.")


if __name__ == "__main__":
    asyncio.run(main())
