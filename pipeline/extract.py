import json, sys, os
import numpy as np
from PIL import Image


def extract_video_frames(video_path, n_frames):
    """Extract n evenly-spaced frames from a video using ffmpeg."""
    import subprocess, tempfile
    tmpdir = tempfile.mkdtemp()
    result = subprocess.run(
        ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
         "-of", "csv=p=0", video_path],
        capture_output=True, text=True)
    duration = float(result.stdout.strip())

    frames = []
    for i in range(n_frames):
        t = duration * i / n_frames
        out_path = os.path.join(tmpdir, f"frame_{i:03d}.png")
        subprocess.run(
            ["ffmpeg", "-ss", str(t), "-i", video_path,
             "-frames:v", "1", "-y", "-loglevel", "quiet", out_path])
        frames.append(np.asarray(Image.open(out_path).convert("RGB"),
                                 dtype=np.float32))
        os.remove(out_path)
    os.rmdir(tmpdir)
    return frames


def rgb_to_hsv_array(rgb_flat):
    """Vectorized RGB (0-1 float, shape Nx3) to HSV (H 0-360, S 0-100, V 0-1)."""
    r, g, b = rgb_flat[:, 0], rgb_flat[:, 1], rgb_flat[:, 2]
    maxc = np.maximum(np.maximum(r, g), b)
    minc = np.minimum(np.minimum(r, g), b)
    diff = maxc - minc

    h = np.zeros_like(maxc)
    mask = diff > 0
    rm = mask & (maxc == r)
    gm = mask & (maxc == g) & ~rm
    bm = mask & ~rm & ~gm

    h[rm] = (60 * ((g[rm] - b[rm]) / diff[rm]) + 360) % 360
    h[gm] = (60 * ((b[gm] - r[gm]) / diff[gm]) + 120) % 360
    h[bm] = (60 * ((r[bm] - g[bm]) / diff[bm]) + 240) % 360

    s = np.where(maxc > 0, (diff / maxc) * 100, 0.0)
    return h, s, maxc


# ── Exhibit 1: purple/orange detection ──

def extract_purple_orange(cfg):
    img = Image.open(cfg["source"]).convert("RGB")
    if cfg.get("crop"):
        img = img.crop(tuple(cfg["crop"]))
    img = img.resize((720, int(img.height * 720 / img.width)))
    arr = np.asarray(img, dtype=np.float32)

    h, w, _ = arr.shape
    flat = arr.reshape(-1, 3) / 255.0
    hue, sat, val = rgb_to_hsv_array(flat)

    o_lo, o_hi = cfg["orange_hue_range"]
    p_lo, p_hi = cfg["purple_hue_range"]
    sat_min = cfg["saturation_min"]

    is_orange = (hue >= o_lo) & (hue <= o_hi) & (sat >= sat_min)
    is_purple = (hue >= p_lo) & (hue <= p_hi) & (sat >= sat_min)
    is_colored = is_orange | is_purple

    is_colored_2d = is_colored.reshape(h, w)
    is_purple_2d = is_purple.reshape(h, w)
    val_2d = val.reshape(h, w)

    n_bands = cfg["n_bands"]
    feats = []
    for b in range(n_bands):
        col_start = b * w // n_bands
        col_end = (b + 1) * w // n_bands
        band_colored = is_colored_2d[:, col_start:col_end]
        band_purple = is_purple_2d[:, col_start:col_end]
        band_val = val_2d[:, col_start:col_end]

        n_colored = band_colored.sum()
        total = band_colored.size

        if n_colored < 10:
            feats.append({"band": b, "norm": 0.0, "coverage": 0.0,
                          "tension": 0.0, "mean": None})
            continue

        intensity = float(band_val[band_colored].mean())
        coverage = float(n_colored / total)
        tension = float(band_purple.sum() / n_colored)

        feats.append({
            "band": b,
            "lon_start": -180 + b * 360 / n_bands,
            "mean": round(intensity, 3),
            "norm": round(min(max(intensity, 0.0), 1.0), 3),
            "coverage": round(coverage, 3),
            "tension": round(tension, 3),
        })
    return feats


# ── Exhibit 2: synthetic gradient lookup ──

def build_gradient_strip(gradient_points, n_steps=256):
    """Build an RGB strip from gradient control points."""
    strip = np.zeros((n_steps, 3), dtype=np.float32)
    for i in range(len(gradient_points) - 1):
        v0, c0 = gradient_points[i]
        v1, c1 = gradient_points[i + 1]
        i0 = int(v0 * (n_steps - 1))
        i1 = int(v1 * (n_steps - 1))
        for ch in range(3):
            strip[i0:i1 + 1, ch] = np.linspace(c0[ch], c1[ch], i1 - i0 + 1)
    return strip


def extract_synthetic_gradient(cfg):
    img = Image.open(cfg["source"]).convert("RGB")
    if cfg.get("crop"):
        img = img.crop(tuple(cfg["crop"]))
    img = img.resize((720, int(img.height * 720 / img.width)))
    arr = np.asarray(img, dtype=np.float32)
    h, w, _ = arr.shape

    strip = build_gradient_strip(cfg["gradient"])
    values = np.linspace(0.0, 1.0, len(strip))

    flat = arr.reshape(-1, 3) / 255.0
    _, sat, _ = rgb_to_hsv_array(flat)
    is_land = sat < cfg["land_gray_max_saturation"]

    flat_255 = arr.reshape(-1, 3)
    max_dist = cfg["max_color_distance"]
    out = np.full(len(flat_255), np.nan, dtype=np.float32)
    for i in range(0, len(flat_255), 20000):
        chunk = flat_255[i:i + 20000]
        d = np.linalg.norm(chunk[:, None, :] - strip[None, :, :], axis=2)
        idx, dist = d.argmin(axis=1), d.min(axis=1)
        v = values[idx]
        v[dist > max_dist] = np.nan
        out[i:i + 20000] = v

    out[is_land] = np.nan
    grid = out.reshape(h, w)

    n_bands = cfg["n_bands"]
    feats = []
    for b in range(n_bands):
        col = grid[:, b * w // n_bands:(b + 1) * w // n_bands]
        valid = col[~np.isnan(col)]
        if valid.size == 0:
            feats.append({"band": b, "norm": 0.0, "coverage": 0.0,
                          "tension": 0.0, "mean": None})
            continue
        mean = float(np.mean(valid))
        feats.append({
            "band": b,
            "lon_start": -180 + b * 360 / n_bands,
            "mean": round(mean, 3),
            "norm": round(min(max(mean, 0.0), 1.0), 3),
            "coverage": round(valid.size / col.size, 3),
            "tension": 0.0,
        })
    return feats


# ── Exhibit 3: CO2 time mode (video) ──

def extract_time_co2(cfg):
    frames = extract_video_frames(cfg["source"], cfg["n_frames"])

    h_lo, h_hi = cfg["co2_hue_range"]
    sat_min = cfg["co2_saturation_min"]

    raw_norms = []
    raw_coverages = []

    for frame in frames:
        resized = np.asarray(
            Image.fromarray(frame.astype(np.uint8)).resize((360, 180)),
            dtype=np.float32)
        flat = resized.reshape(-1, 3) / 255.0
        hue, sat, _ = rgb_to_hsv_array(flat)

        is_warm = (hue >= h_lo) & (hue <= h_hi) & (sat >= sat_min)
        warm_frac = float(is_warm.sum() / len(flat))
        raw_norms.append(warm_frac)
        raw_coverages.append(float((sat >= 10).sum() / len(flat)))

    peak = max(raw_norms) if max(raw_norms) > 0 else 1.0

    feats = []
    for i in range(len(frames)):
        feats.append({
            "band": i,
            "frame_index": i,
            "mean": round(raw_norms[i], 5),
            "norm": round(raw_norms[i] / peak, 3),
            "coverage": round(raw_coverages[i], 3),
            "tension": 0.0,
        })
    return feats


# ── Exhibit 4: lightning time mode + events (video) ──

def extract_time_lightning(cfg):
    frames = extract_video_frames(cfg["source"], cfg["n_frames"])

    threshold = cfg["brightness_threshold"]
    cluster_min = cfg["flash_cluster_min"]

    raw_norms = []
    raw_coverages = []

    for frame in frames:
        resized = np.asarray(
            Image.fromarray(frame.astype(np.uint8)).resize((480, 270)),
            dtype=np.float32)
        gray = np.mean(resized, axis=2)
        bright = gray >= threshold

        n_bright = int(bright.sum())
        if n_bright < cluster_min:
            n_bright = 0

        total = gray.size
        raw_norms.append(n_bright / total)
        raw_coverages.append(float(n_bright / total))

    peak = max(raw_norms) if max(raw_norms) > 0 else 1.0

    feats = []
    for i in range(len(frames)):
        feats.append({
            "band": i,
            "frame_index": i,
            "mean": round(raw_norms[i], 5),
            "norm": round(raw_norms[i] / peak, 3),
            "coverage": round(raw_coverages[i], 3),
            "tension": 0.0,
        })
    return feats


# ── Main dispatch ──

METHODS = {
    "purple_orange": extract_purple_orange,
    "synthetic_gradient": extract_synthetic_gradient,
    "time_co2": extract_time_co2,
    "time_lightning": extract_time_lightning,
}

if __name__ == "__main__":
    cfg = json.load(open(sys.argv[1]))
    method = cfg.get("method")
    if method not in METHODS:
        print(f"Unknown method: {method}")
        sys.exit(1)

    feats = METHODS[method](cfg)
    os.makedirs("build", exist_ok=True)
    json.dump({"config": cfg, "features": feats},
              open(f"build/features-{cfg['id']}.json", "w"), indent=2)
    print(f"Saved build/features-{cfg['id']}.json ({len(feats)} features)")
