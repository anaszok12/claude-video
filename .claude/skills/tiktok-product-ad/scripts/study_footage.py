"""
study_footage.py  |  Turns videos into things that can be read without watching or listening.

HOW TO RUN
    python3 study_footage.py <file or folder> [more files or folders] --out <folder> [--transcribe]

FOR EACH VIDEO IT GIVES
    * length, picture size, frame rate, whether it has sound
    * cut times (where one shot changes to the next)
    * a contact sheet: one picture holding small frames with time stamps (saved in --out)
    * loudness over time, so loud moments (a roar, a click, music) can be located
    * with --transcribe: any spoken words it can make out (needs the faster-whisper library)

Use it on reference ads, on raw product footage, and on the finished ad to check the result.
Needs: ffmpeg and ffprobe.
"""

import argparse
import array
import json
import math
import os
import re
import subprocess
import sys

VIDEO_TYPES = (".mp4", ".mov", ".m4v", ".webm", ".mkv", ".avi")
IMAGE_TYPES = (".jpg", ".jpeg", ".png", ".webp", ".heic")


def probe(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_format", "-show_streams", "-of", "json", path],
                         capture_output=True, text=True).stdout
    info = json.loads(out or "{}")
    video = next((s for s in info.get("streams", []) if s.get("codec_type") == "video"), None)
    audio = any(s.get("codec_type") == "audio" for s in info.get("streams", []))
    if not video:
        return None
    w, h = video["width"], video["height"]
    # phone clips are often stored sideways with a "rotation" note; swap so the numbers match what you see
    rotation = 0
    for side in video.get("side_data_list", []):
        rotation = abs(int(side.get("rotation", 0))) or rotation
    if rotation in (90, 270):
        w, h = h, w
    num, den = video.get("r_frame_rate", "30/1").split("/")
    return dict(w=w, h=h, fps=float(num) / float(den or 1),
                dur=float(info["format"].get("duration", 0)), audio=audio)


def contact_sheet(path, info, out_dir):
    """One picture with a grid of small frames. Picks the spacing so there are at most about 45 frames."""
    step = next((s for s in (0.5, 1, 2, 4, 8) if info["dur"] / s <= 45), 15)
    count = max(1, int(math.ceil(info["dur"] / step)))
    cols = min(8, count)
    rows = int(math.ceil(count / cols))
    name = os.path.splitext(os.path.basename(path))[0][-40:] + "_sheet.jpg"
    out = os.path.join(out_dir, name)
    filters = (f"fps=1/{step},scale=-2:384,"
               "drawtext=text='%{pts\\:hms}':fontcolor=yellow:fontsize=20:box=1:boxcolor=black@0.6:x=4:y=4,"
               f"tile={cols}x{rows}")
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", path, "-vf", filters, "-frames:v", "1", out])
    return out, step


def cut_times(path):
    """Seconds at which the picture changes sharply, which is where an editor made a cut."""
    err = subprocess.run(["ffmpeg", "-hide_banner", "-i", path, "-vf", "scdet=threshold=12", "-an", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    return [float(x) for x in re.findall(r"lavfi\.scd\.time: ([0-9.]+)", err)]


def loudness(path, window):
    """Loudness in decibels for each slice of `window` seconds. Around -60 is silence, -20 and up is loud."""
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-ac", "1", "-ar", "8000", "-f", "s16le", "-"],
                         capture_output=True).stdout
    samples = array.array("h")
    samples.frombytes(raw[:len(raw) // 2 * 2])
    n = int(8000 * window)
    levels = []
    for i in range(0, len(samples) - n + 1, n):
        chunk = samples[i:i + n]
        rms = math.sqrt(sum(x * x for x in chunk) / n) / 32768
        levels.append(round(20 * math.log10(rms + 1e-9)))
    return levels


def transcribe(path, model_holder):
    try:
        import numpy as np
        from faster_whisper import WhisperModel
    except ImportError:
        return ["(transcription skipped: run  pip install faster-whisper  first)"]
    if "m" not in model_holder:
        model_holder["m"] = WhisperModel("small", device="cpu", compute_type="int8")
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-ac", "1", "-ar", "16000", "-f", "s16le", "-"],
                         capture_output=True).stdout
    audio = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768
    segments, _ = model_holder["m"].transcribe(audio, vad_filter=True)
    lines = [f"{s.start:5.1f} to {s.end:5.1f} s: {s.text.strip()}" for s in segments]
    return lines or ["(no speech found)"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("paths", nargs="+")
    ap.add_argument("--out", required=True, help="folder for the contact sheets")
    ap.add_argument("--transcribe", action="store_true", help="also write down any speech")
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)

    files = []
    for p in args.paths:
        if os.path.isdir(p):
            files += sorted(os.path.join(p, f) for f in os.listdir(p))
        else:
            files.append(p)

    model_holder = {}
    for path in files:
        low = path.lower()
        if low.endswith(IMAGE_TYPES):
            print(f"\n== PHOTO {os.path.basename(path)}  (open it directly to look at it)")
            continue
        if not low.endswith(VIDEO_TYPES):
            continue
        info = probe(path)
        if not info:
            print(f"\n== {os.path.basename(path)}: could not be read as video")
            continue
        shape = "portrait" if info["h"] > info["w"] else "landscape" if info["w"] > info["h"] else "square"
        print(f"\n== VIDEO {os.path.basename(path)}")
        print(f"   length {info['dur']:.1f} s | {info['w']}x{info['h']} {shape} | {info['fps']:.0f} fps | "
              f"sound: {'yes' if info['audio'] else 'no'}")

        cuts = cut_times(path)
        if cuts:
            edges = [0.0] + cuts + [info["dur"]]
            lengths = [b - a for a, b in zip(edges, edges[1:]) if b - a > 0.05]
            print(f"   cuts: {len(cuts)} at " + " ".join(f"{c:.1f}" for c in cuts))
            print(f"   shot length: shortest {min(lengths):.1f} s, longest {max(lengths):.1f} s, "
                  f"average {sum(lengths) / len(lengths):.1f} s")
        else:
            print("   cuts: none found (one continuous shot)")

        sheet, step = contact_sheet(path, info, args.out)
        print(f"   contact sheet (one frame every {step} s): {sheet}")

        if info["audio"]:
            window = 0.25 if info["dur"] <= 40 else 0.5
            levels = loudness(path, window)
            per_row = int(5 / window)                           # one printed row covers 5 seconds
            print(f"   loudness in dB, one number per {window} s (about -60 is silence, -20 or higher is loud):")
            for i in range(0, len(levels), per_row):
                print(f"     {i * window:5.1f} s | " + " ".join(f"{v:4d}" for v in levels[i:i + per_row]))
            if args.transcribe:
                print("   speech:")
                for line in transcribe(path, model_holder):
                    print(f"     {line}")


if __name__ == "__main__":
    main()
