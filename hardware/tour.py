import json
import sys
import time

import pygame
import serial

PORT = "/dev/cu.usbmodem101"
BAUD = 115200
GAP_SECONDS = 3
FPS = 20

IDLE = (8, 8, 14)
SOFT_GLOW = (40, 40, 60)
DIM = (5, 5, 10)

TOUR = [
    {"audio": "audio/welcome.mp3",   "zone": None, "timeline": None},
    {"audio": "audio/exhibit-1.mp3", "zone": 1, "timeline": "data/led-timeline-1.json"},
    {"audio": "audio/exhibit-2.mp3", "zone": 2, "timeline": "data/led-timeline-2.json"},
    {"audio": "audio/exhibit-3.mp3", "zone": 3, "timeline": "data/led-timeline-3.json"},
    {"audio": "audio/exhibit-4.mp3", "zone": 4, "timeline": "data/led-timeline-4.json"},
    {"audio": "audio/closing.mp3",   "zone": None, "timeline": None},
]


def send(ser, cmd):
    ser.write((cmd + "\n").encode())


def set_all(ser, rgb):
    send(ser, f"A,{rgb[0]},{rgb[1]},{rgb[2]}")


def load_frames(path):
    if not path:
        return []
    with open(path) as f:
        return json.load(f)["frames"]


def frame_at(frames, t):
    current = frames[0]
    for fr in frames:
        if fr["t"] <= t:
            current = fr
        else:
            break
    return current


def play_item(ser, item):
    frames = load_frames(item["timeline"])
    zone = item["zone"]

    if zone is None:
        set_all(ser, SOFT_GLOW)
    else:
        set_all(ser, DIM)

    pygame.mixer.music.load(item["audio"])
    pygame.mixer.music.play()

    last_sent = None
    while pygame.mixer.music.get_busy():
        if zone is not None and frames:
            t = pygame.mixer.music.get_pos() / 1000.0
            fr = frame_at(frames, t)
            r, g, b = (int(c * fr["brightness"]) for c in fr["color"])
            if (r, g, b) != last_sent:
                send(ser, f"A,{r},{g},{b}")
                last_sent = (r, g, b)
        time.sleep(1 / FPS)


def run_tour(ser):
    print("Tour started")
    for i, item in enumerate(TOUR):
        print(f"Playing {item['audio']}")
        play_item(ser, item)
        if i < len(TOUR) - 1:
            time.sleep(GAP_SECONDS)
    set_all(ser, IDLE)
    ser.reset_input_buffer()   # ignore button presses made during the tour
    print("Tour finished. Waiting for button…")


def main():
    pygame.mixer.init()
    ser = serial.Serial(PORT, BAUD, timeout=0.1)
    time.sleep(2)              # let the board reset after connecting
    set_all(ser, IDLE)

    if "--start" in sys.argv:  # test without pressing the button
        run_tour(ser)

    print("Waiting for button…")
    while True:
        msg = ser.readline().decode(errors="ignore").strip()
        if msg == "START":
            run_tour(ser)


if __name__ == "__main__":
    main()
