# Eos — Hear Our Changing Planet

Eos is an accessible digital museum that turns NASA visualizations of our
changing planet into music with spoken narration. It's designed for blind and
low-vision visitors, and is the digital companion to a miniature physical
museum built from cardboard, an LED strip, and a microcontroller.

Each exhibit pairs an Earth-science image with a short generated soundtrack and
a plain-language explanation of what the image shows and how the sound maps to
the data.

## Exhibits

1. **Earth's Night Lights, 2012–2023**
2. **Ocean Currents and Temperature**
3. **Carbon Dioxide, 2020**
4. **Lightning, 2017–2023**

Source imagery comes from NASA's
[Earth Information Center (EIC) content database](https://svs.gsfc.nasa.gov/gallery/earth-information-center/).

## The website

A static site built with plain HTML, CSS, and ES modules — no build step and no
dependencies. The look is a warm, illustrated "vintage museum": cream and brown
walls, a wood floor, rope barriers, spotlights, and gilt picture frames, with
headings in Federo and body text in Inter (both self-hosted in `fonts/`).

### Running locally

Serve the folder with any static file server, for example:

```bash
python3 -m http.server 8080
```

Then open <http://localhost:8080>. (`.claude/launch.json` defines the same
`eos-dev` server for the editor's preview.)

### Using it

- **Enter the museum** from the intro screen, which shows the physical build
  (a photo and a YouTube walkthrough).
- **Open an exhibit** to read its description and play its soundtrack; the frame
  glows in time with the audio, mirroring the physical LEDs.
- **Start the guided tour** to visit all four exhibits hands-free: each opens
  automatically and plays in the background while you read. Move on or leave with
  **Next**, **Previous**, or the **✕** close button.
- **Leave museum** returns to the intro screen.

Keyboard shortcuts:

| Key | Action |
| --- | --- |
| `1`–`4` | Open exhibit 1–4 |
| `Space` | Play / pause current audio |
| `T` | Start / stop the guided tour |
| `N` / `P` | Next / previous exhibit |
| `Escape` | Close the exhibit view |
| `?` | Move focus to the shortcuts list |

### Accessibility

Built for screen-reader and keyboard use: semantic landmarks, an `aria-live`
status region for announcements, visible focus styles that work on both the
light and dark walls, full keyboard operation, every exhibit has a transcript
and a long image description, and decorative artwork is hidden from assistive
tech. Animation is disabled under `prefers-reduced-motion`.

### Demo video

The walkthrough is embedded from YouTube (the source file is far larger than
GitHub's 100 MB limit, so it is not committed). For the embed to play for
visitors, the YouTube video must be **Public** or **Unlisted**.

## Project layout

```
index.html            Markup for the intro, museum, and exhibit dialog
css/style.css         All styling
js/                   main, exhibits, tour, player, led, announcer (ES modules)
data/                 exhibits.json and per-exhibit LED timelines
audio/                Generated exhibit, welcome, and closing soundtracks
images/               Exhibit images + decor SVGs + the physical-build photo
fonts/                Self-hosted Federo and Inter
pipeline/             Scripts that generate the audio and LED timelines
hardware/             Firmware and driver for the physical museum
```

## Audio pipeline

The soundtracks and LED timelines in `audio/` and `data/` are generated from the
exhibit images by the scripts in `pipeline/` (configured per exhibit in
`pipeline/config/`):

1. `extract.py` — pull colour/feature bands from each source image.
2. `sonify.py` — map those features to a MIDI score.
3. `render.py` — render the MIDI to audio with a SoundFont.
4. `narrate.py` — synthesize the spoken narration (edge-tts).
5. `mix.py` — assemble the final exhibit audio and the LED timeline JSON.

`make_chime.py` generates the UI chime.

## Hardware

The physical museum is driven by the code in `hardware/`:

- `eos_device/eos_device.ino` — microcontroller firmware for the LED strip.
- `tour.py` — host-side driver that plays the audio and streams LED colour and
  brightness to the device over serial, synced to the same timelines the website
  uses.

## License

MIT — see [LICENSE](LICENSE). NASA imagery is courtesy of the Earth Information
Center content database.
