"""
build_ad.py  |  Renders a vertical product ad from a settings file.

HOW TO RUN
    python3 build_ad.py <settings.json> <footage folder> <output.mp4>

WHAT IT DOES, IN ORDER
    1. Cuts each shot listed in the settings file out of the footage.
    2. Makes the end card from a still photo (if the settings ask for one).
    3. Glues the pieces into one silent video.
    4. Builds the sound track from the footage's own audio.
    5. Draws the animated text, frame by frame, and lays it on top.

The settings file is described in ../references/config.md.
Needs: ffmpeg, ffprobe and the Python library Pillow.
"""

import glob
import json
import math
import os
import re
import subprocess
import sys

from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
IMAGE_TYPES = (".jpg", ".jpeg", ".png", ".webp", ".bmp")

WHITE = (255, 255, 255)
BLACK = (0, 0, 0)

# Ready made caption looks. "hook" is the big opening line, "feature" the calmer mid video line.
CAPTION_STYLES = {
    "hook": dict(size=112, y=1240),
    "feature": dict(size=84, y=1290),
}


# ---------------------------------------------------------------------------
# SETTINGS: read the JSON file and fill in defaults
# ---------------------------------------------------------------------------
class Settings:
    def __init__(self, path):
        with open(path) as f:
            raw = json.load(f)
        self.W = raw.get("width", 1080)
        self.H = raw.get("height", 1920)
        self.FPS = raw.get("fps", 30)
        self.accent = hex_to_rgb(raw.get("accent", "#FFD928"))
        self.kicker_colour = hex_to_rgb(raw.get("kicker_colour", "#B6F23A"))
        self.loudness = raw.get("loudness", -14)
        self.tag = raw.get("tag")
        self.shots = raw["shots"]
        self.extra_sounds = raw.get("sounds", [])
        self.end_card = raw.get("end_card")

        # TikTok covers the edges with its own buttons and caption.
        # Text stays inside this box. Numbers are for a 1080 x 1920 frame and scale with the size.
        k = self.W / 1080
        self.k = k
        self.safe_left, self.safe_right = int(60 * k), int(920 * k)
        self.safe_top, self.safe_bottom = int(190 * k), int(1500 * k)

        for shot in self.shots:
            shot.setdefault("speed", 1.0)
            shot.setdefault("zoom", [1.0, 1.0])
            shot.setdefault("focus", [0.5, 0.5])
            shot["zoom"] = [max(1.0, z) for z in shot["zoom"]]

        # when each shot starts on the ad timeline (running total)
        self.starts, t = [], 0.0
        for shot in self.shots:
            self.starts.append(t)
            t += shot["dur"]
        self.end_start = t
        self.end_dur = self.end_card.get("dur", 4.0) if self.end_card else 0.0
        self.total = t + self.end_dur


def hex_to_rgb(text):
    text = text.lstrip("#")
    return tuple(int(text[i:i + 2], 16) for i in (0, 2, 4))


# ---------------------------------------------------------------------------
# SMALL HELPERS
# ---------------------------------------------------------------------------
def run(cmd):
    """Run one ffmpeg command and stop the script if it fails."""
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(result.stderr[-3000:])
        sys.exit("ffmpeg failed, see the message above")


def find(src_dir, name):
    """Find the footage file whose name contains `name`."""
    hits = sorted(glob.glob(os.path.join(src_dir, f"*{name}*")))
    hits = [h for h in hits if os.path.isfile(h)]
    if not hits:
        sys.exit(f"Could not find a file containing '{name}' in {src_dir}")
    if len(hits) > 1:
        sys.exit(f"'{name}' matches more than one file, use a longer name: {[os.path.basename(h) for h in hits]}")
    return hits[0]


def is_image(path):
    return path.lower().endswith(IMAGE_TYPES)


def has_audio(path):
    if is_image(path):
        return False
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries",
                          "stream=codec_type", "-of", "csv=p=0", path], capture_output=True, text=True).stdout
    return "audio" in out


def find_font(weight):
    """Use the fonts shipped with the skill, else a bold system font."""
    names = {"black": "InterDisplay-Black.otf", "bold": "InterDisplay-ExtraBold.otf"}
    places = [
        os.path.join(HERE, "..", "assets", "fonts", names[weight]),
        os.path.join("/usr/share/fonts/opentype/inter", names[weight]),
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/Library/Fonts/Arial Bold.ttf",
        "C:/Windows/Fonts/arialbd.ttf",
    ]
    for p in places:
        if os.path.exists(p):
            return p
    sys.exit("No usable bold font found. Put a .ttf or .otf in assets/fonts.")


def even(x):
    return 2 * int(round(x / 2))


def ease_out_back(x):
    """Turns a 0..1 progress value into a 'pop' that overshoots a little then settles."""
    c1, c3 = 1.70158, 2.70158
    return 1 + c3 * (x - 1) ** 3 + c1 * (x - 1) ** 2


# ---------------------------------------------------------------------------
# STEP 1: CUT THE SHOTS
# ---------------------------------------------------------------------------
def cut_shot(cfg, src_dir, tmp, i, shot):
    out = os.path.join(tmp, f"shot{i}.mp4")
    src = find(src_dir, shot["clip"])
    z0, z1 = shot["zoom"]
    zmax = max(z0, z1)
    fx, fy = shot["focus"]
    big_w, big_h = 2 * math.ceil(cfg.W * zmax / 2), 2 * math.ceil(cfg.H * zmax / 2)

    steps = []
    if not is_image(src):
        steps.append(f"setpts=(PTS-STARTPTS)/{shot['speed']}")      # speed up or slow down
    steps.append(f"fps={cfg.FPS}")
    # fill the frame at the largest zoom this shot needs (crops the sides of wide footage)
    steps.append(f"scale={big_w}:{big_h}:force_original_aspect_ratio=increase:flags=lanczos")
    steps.append(f"crop={big_w}:{big_h}:x='(iw-{big_w})*{fx}':y='(ih-{big_h})*{fy}'")
    if abs(z1 - z0) > 0.001:
        # zoom moves smoothly from z0 to z1 over the life of the shot
        z = f"({z0}+({z1}-{z0})*min(t,{shot['dur']})/{shot['dur']})"
        # rounding up keeps the picture at least as big as the frame, so the crop below never fails
        steps.append(f"scale=w='2*ceil({cfg.W}*{z}/2)':h='2*ceil({cfg.H}*{z}/2)':eval=frame")
    steps.append(f"crop={cfg.W}:{cfg.H}:x='(iw-{cfg.W})*{fx}':y='(ih-{cfg.H})*{fy}'")
    steps.append("eq=saturation=1.12:contrast=1.04")                 # a touch more colour
    steps.append("format=yuv420p")

    if is_image(src):
        source = ["-loop", "1", "-framerate", str(cfg.FPS), "-i", src]
    else:
        source = ["-ss", str(shot["start"]), "-t", str(shot["dur"] * shot["speed"]), "-i", src]
    run(["ffmpeg", "-y", "-v", "error"] + source + ["-an", "-vf", ",".join(steps), "-t", str(shot["dur"]),
         "-c:v", "libx264", "-preset", "medium", "-crf", "14", out])
    return out


# ---------------------------------------------------------------------------
# STEP 2: END CARD (blurred photo behind, sharp photo card in front, slow zoom)
# ---------------------------------------------------------------------------
def load_end_photo(cfg, src_dir, tmp):
    card = cfg.end_card
    src = find(src_dir, card["photo"])
    if not is_image(src):                          # a video: grab one frame from it
        still = os.path.join(tmp, "end_still.png")
        run(["ffmpeg", "-y", "-v", "error", "-ss", str(card.get("photo_at", 0)), "-i", src, "-frames:v", "1", still])
        src = still
    return Image.open(src).convert("RGB")


def make_end_card(cfg, src_dir, tmp, layout):
    out = os.path.join(tmp, "endcard.mp4")
    W, H = cfg.W, cfg.H
    photo = load_end_photo(cfg, src_dir, tmp)

    # background: the same photo, stretched to fill, blurred and darkened
    scale = max(W / photo.width, H / photo.height)
    bg = photo.resize((int(photo.width * scale) + 1, int(photo.height * scale) + 1))
    left, top = (bg.width - W) // 2, (bg.height - H) // 2
    bg = bg.crop((left, top, left + W, top + H)).filter(ImageFilter.GaussianBlur(40))
    bg = Image.blend(bg, Image.new("RGB", (W, H), (10, 12, 10)), 0.55)
    bg.save(os.path.join(tmp, "end_bg.png"))

    # foreground card: the photo trimmed to the card shape, with rounded corners
    card_w, card_h = layout["card_w"], layout["card_h"]
    fx, fy = cfg.end_card.get("focus", [0.5, 0.5])
    scale = max(card_w / photo.width, card_h / photo.height) * 2        # 2x size keeps the zoom sharp
    fg = photo.resize((int(photo.width * scale) + 1, int(photo.height * scale) + 1), Image.LANCZOS)
    left, top = int((fg.width - card_w * 2) * fx), int((fg.height - card_h * 2) * fy)
    fg = fg.crop((left, top, left + card_w * 2, top + card_h * 2)).convert("RGBA")
    mask = Image.new("L", fg.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, fg.width, fg.height), radius=72, fill=255)
    fg.putalpha(mask)
    fg.save(os.path.join(tmp, "end_fg.png"))

    z = f"(1+0.06*min(t,{cfg.end_dur})/{cfg.end_dur})"
    graph = (
        f"[1:v]scale=w='2*trunc({card_w}*{z}/2)':h='2*trunc({card_h}*{z}/2)':eval=frame[fg];"
        f"[0:v][fg]overlay=x='(W-w)/2':y='{layout['card_top']}+({card_h}-h)/2':format=auto,"
        f"eq=saturation=1.12:contrast=1.04,format=yuv420p[v]"
    )
    run(["ffmpeg", "-y", "-v", "error",
         "-loop", "1", "-framerate", str(cfg.FPS), "-i", os.path.join(tmp, "end_bg.png"),
         "-loop", "1", "-framerate", str(cfg.FPS), "-i", os.path.join(tmp, "end_fg.png"),
         "-filter_complex", graph, "-map", "[v]", "-t", str(cfg.end_dur),
         "-c:v", "libx264", "-preset", "medium", "-crf", "14", out])
    return out


# ---------------------------------------------------------------------------
# STEP 3: GLUE THE PIECES TOGETHER
# ---------------------------------------------------------------------------
def join(tmp, pieces):
    out = os.path.join(tmp, "base.mp4")
    listing = os.path.join(tmp, "list.txt")
    with open(listing, "w") as f:
        for p in pieces:
            f.write(f"file '{p}'\n")
    run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", listing, "-c", "copy", out])
    return out


# ---------------------------------------------------------------------------
# STEP 4: SOUND TRACK
# ---------------------------------------------------------------------------
def collect_sounds(cfg, src_dir):
    """Build the full list of sound pieces: each shot's own audio plus any extra ones."""
    pieces = []
    for shot, at in zip(cfg.shots, cfg.starts):
        src = find(src_dir, shot["clip"])
        default = "own" if (shot["speed"] == 1.0 and has_audio(src)) else "none"
        if shot.get("sound", default) == "own":
            if not has_audio(src):
                sys.exit(f"Shot using '{shot['clip']}' asks for its own sound but that file has no audio")
            pieces.append(dict(src=src, start=shot["start"], dur=shot["dur"], at=at, gain=shot.get("gain", 0)))
    for s in cfg.extra_sounds:
        if s.get("at") == "end_card":
            at = cfg.end_start
        elif "at_shot" in s:
            at = cfg.starts[s["at_shot"] - 1]                 # shots are counted from 1 in the settings file
        else:
            at = float(s["at"])
        pieces.append(dict(src=find(src_dir, s["clip"]), start=s["start"], dur=s["dur"], at=at,
                           gain=s.get("gain", 0), fade_out=s.get("fade_out", 0.06)))
    return pieces


def make_audio(cfg, src_dir, tmp):
    out = os.path.join(tmp, "audio.wav")
    pieces = collect_sounds(cfg, src_dir)
    if not pieces:                                             # no sound at all: make silence
        run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo",
             "-t", str(cfg.total), out])
        return out, False
    cmd = ["ffmpeg", "-y", "-v", "error"]
    chains, labels = [], []
    for i, s in enumerate(pieces):
        cmd += ["-ss", str(s["start"]), "-t", str(s["dur"]), "-i", s["src"]]
        fade_out = s.get("fade_out", 0.06)
        chains.append(
            f"[{i}:a]aresample=48000,aformat=channel_layouts=stereo,volume={s['gain']}dB,"
            f"afade=t=in:d=0.04,afade=t=out:st={s['dur'] - fade_out}:d={fade_out},"   # tiny fades stop clicks at the cuts
            f"adelay={int(round(s['at'] * 1000))}:all=1[a{i}]"
        )
        labels.append(f"[a{i}]")
    graph = ";".join(chains) + ";" + "".join(labels) + (
        f"amix=inputs={len(pieces)}:normalize=0:duration=longest,"
        f"alimiter=limit=0.89,apad,atrim=0:{cfg.total}[a]"
    )
    run(cmd + ["-filter_complex", graph, "-map", "[a]", out])
    return out, True


# ---------------------------------------------------------------------------
# STEP 5: ANIMATED TEXT
# ---------------------------------------------------------------------------
def parse_line(text, accent):
    """'REALLY *ROARS*' becomes [('REALLY ', white), ('ROARS', accent)]. Stars mark the accent words."""
    parts = []
    for n, chunk in enumerate(text.split("*")):
        if chunk:
            parts.append((chunk, accent if n % 2 else WHITE))
    return parts


def line_width(parts, font):
    return sum(font.getlength(text) for text, _ in parts)


def stroke_for(size):
    return max(5, size // 11)


def render_line(parts, size, font_path, stroke=None):
    """Draw one line of text on a see-through picture: soft shadow, black outline, coloured letters."""
    font = ImageFont.truetype(font_path, size)
    stroke = stroke if stroke is not None else stroke_for(size)
    pad = stroke + 24
    w = int(line_width(parts, font)) + pad * 2
    h = int(size * 1.02) + pad * 2

    def draw_text(target, fill_override=None, stroke_w=0):
        d = ImageDraw.Draw(target)
        x = pad
        for text, colour in parts:
            d.text((x, pad), text, font=font, fill=fill_override or colour,
                   stroke_width=stroke_w, stroke_fill=fill_override or BLACK)
            x += font.getlength(text)

    shadow = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw_text(shadow, fill_override=(0, 0, 0, 150), stroke_w=stroke)
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    img.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(10)), (0, 8))
    outline = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw_text(outline, fill_override=BLACK + (255,), stroke_w=stroke)
    img.alpha_composite(outline)
    letters = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw_text(letters)
    img.alpha_composite(letters)
    return img


def fit_size(lines, size, font_path, max_width, label):
    """Shrink the text until its widest line fits. Tells you when it had to shrink."""
    wanted = size
    while size > 24:
        font = ImageFont.truetype(font_path, size)
        if max(line_width(parts, font) for parts in lines) <= max_width:
            break
        size -= 2
    if size != wanted:
        print(f"   note: {label} shrunk from {wanted} to {size} px to fit. Shorter words read better.")
    return size


def render_tag(cfg, font_bold):
    """The small black title tag pinned top left."""
    k = cfg.k
    kicker_font = ImageFont.truetype(font_bold, int(26 * k))
    title_font = ImageFont.truetype(font_bold, int(50 * k))
    kicker, title = cfg.tag.get("kicker", ""), cfg.tag["title"]
    w = int(max(kicker_font.getlength(kicker), title_font.getlength(title)) + 56 * k)
    h = int(136 * k) if kicker else int(96 * k)
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((0, 0, w, h), radius=int(10 * k), fill=(12, 12, 12, 235))
    if kicker:
        d.text((28 * k, 20 * k), kicker, font=kicker_font, fill=cfg.kicker_colour)
        d.text((28 * k, 54 * k), title, font=title_font, fill=WHITE)
    else:
        d.text((28 * k, 20 * k), title, font=title_font, fill=WHITE)
    return img


def render_button(cfg, text, font_black):
    """Rounded button in the accent colour for the end card."""
    k = cfg.k
    size = int(62 * k)
    while size > 24 and ImageFont.truetype(font_black, size).getlength(text) > cfg.W - 250 * k:
        size -= 2
    font = ImageFont.truetype(font_black, size)
    w, h = int(font.getlength(text) + 90 * k), int(132 * k)
    img = Image.new("RGBA", (w + 24, h + 24), (0, 0, 0, 0))
    shadow = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(shadow).rounded_rectangle((12, 20, w + 12, h + 20), radius=h // 2, fill=(0, 0, 0, 170))
    img.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(8)))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((12, 8, w + 12, h + 8), radius=h // 2, fill=cfg.accent)
    d.text((12 + w / 2, 8 + h / 2), text, font=font, fill=BLACK, anchor="mm")
    return img


def render_arrow(cfg, direction):
    """Chunky arrow in the accent colour. Drawn pointing down, then turned toward a bottom corner."""
    size = 220
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    shape = [(85, 10), (135, 10), (135, 120), (185, 120), (110, 210), (35, 120), (85, 120)]
    outline = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    ImageDraw.Draw(outline).polygon(shape, fill=BLACK)
    img.alpha_composite(outline.filter(ImageFilter.MaxFilter(13)))      # fatten the black shape into an outline
    ImageDraw.Draw(img).polygon(shape, fill=cfg.accent)
    img = img.rotate(-45 if direction == "down_left" else 45, resample=Image.BICUBIC)
    if cfg.k != 1:
        img = img.resize((int(size * cfg.k), int(size * cfg.k)), Image.BICUBIC)
    return img


def paste_scaled(frame, sprite, cx, cy, scale=1.0, alpha=1.0):
    """Paste `sprite` centred on (cx, cy), optionally resized and faded."""
    if alpha <= 0:
        return
    if abs(scale - 1.0) > 0.001:
        sprite = sprite.resize((max(1, int(sprite.width * scale)), max(1, int(sprite.height * scale))), Image.BICUBIC)
    if alpha < 1:
        sprite = sprite.copy()
        sprite.putalpha(sprite.getchannel("A").point(lambda a: int(a * alpha)))
    frame.alpha_composite(sprite, (int(cx - sprite.width / 2), int(cy - sprite.height / 2)))


def pop(t, start, end, in_time=0.22, out_time=0.10):
    """Returns (scale, alpha) for something that pops in at `start` and fades at `end`."""
    if t < start or t > end:
        return 0.0, 0.0
    if t < start + in_time:
        x = (t - start) / in_time
        return 0.6 + 0.4 * ease_out_back(x), min(1.0, x * 2.5)
    if t > end - out_time:
        return 1.0, (end - t) / out_time
    return 1.0, 1.0


def prepare_captions(cfg, font_black):
    """Turn each shot's caption into ready made line pictures plus timing."""
    caps = []
    max_w = cfg.safe_right - cfg.safe_left
    for i, shot in enumerate(cfg.shots):
        cap = shot.get("caption")
        if not cap:
            continue
        style = CAPTION_STYLES[cap.get("style", "hook" if i == 0 else "feature")]
        lines = [parse_line(text, cfg.accent) for text in cap["lines"]]
        size = fit_size(lines, int(cap.get("size", style["size"]) * cfg.k), font_black, max_w, f"caption on shot {i + 1}")
        lead = cap.get("lead", 0.05 if i == 0 else 0.10)       # the hook text is on screen almost at once
        caps.append(dict(
            start=cfg.starts[i] + lead,
            end=cfg.starts[i] + shot["dur"] - 0.12,
            y=int(cap.get("y", style["y"]) * cfg.k),
            step=int(size * 1.16),                             # distance between line centres
            sprites=[render_line(parts, size, font_black) for parts in lines],
        ))
    return caps


def prepare_end_card(cfg, font_black, font_bold):
    """Work out where everything on the end card goes, and draw its text pieces."""
    card = cfg.end_card
    k = cfg.k
    max_w = cfg.W - int(180 * k)
    title_sprites, centres = [], []
    y = cfg.safe_top
    for n, text in enumerate(card.get("title", [])):
        parts = parse_line(text, cfg.accent)
        size = fit_size([parts], int((170 if n == 0 else 136) * k), font_black, max_w, f"end card title line {n + 1}")
        title_sprites.append(render_line(parts, size, font_black))
        centres.append(y + size * 0.5)
        y += int(size * 0.80)                                  # lines sit tight together
    card_top = int(y + 40 * k) if title_sprites else cfg.safe_top
    card_w = cfg.W - int(80 * k)
    layout = dict(title_sprites=title_sprites, title_centres=centres, card_top=card_top, card_w=card_w)
    layout["max_card_bottom"] = int(1230 * k)
    feats = card.get("features")
    layout["features"] = render_line(parse_line(feats, cfg.accent), fit_size(
        [parse_line(feats, cfg.accent)], int(54 * k), font_bold, cfg.W - int(120 * k), "end card feature line"),
        font_bold, stroke=5) if feats else None
    layout["button"] = render_button(cfg, card["button"], font_black) if card.get("button") else None
    direction = card.get("arrow", "down_left")
    layout["arrow_dir"] = direction
    layout["arrow"] = render_arrow(cfg, direction) if direction != "none" else None
    return layout


def finish_end_layout(cfg, layout, photo):
    """Card height follows the photo's shape, but never runs into the text below it."""
    natural = int(photo.height * layout["card_w"] / photo.width)
    layout["card_h"] = even(min(natural, layout["max_card_bottom"] - layout["card_top"]))
    layout["card_w"] = even(layout["card_w"])
    bottom = layout["card_top"] + layout["card_h"]
    k = cfg.k
    layout["feats_y"] = bottom + int(55 * k)
    layout["button_y"] = bottom + int((165 if layout["features"] else 110) * k)
    layout["arrow_y"] = layout["button_y"] + int(130 * k)


def make_overlay_and_finish(cfg, tmp, base, audio, has_sound, out_path, layout):
    """Draw every text frame and feed it straight into ffmpeg, which lays it over the video."""
    W, H, FPS = cfg.W, cfg.H, cfg.FPS
    font_black, font_bold = find_font("black"), find_font("bold")
    centre_x = (cfg.safe_left + cfg.safe_right) // 2   # a little left of centre, clear of TikTok's buttons
    caps = prepare_captions(cfg, font_black)
    tag = render_tag(cfg, font_bold) if cfg.tag else None

    audio_filter = f"[2:a]loudnorm=I={cfg.loudness}:TP=-1.5:LRA=11[a]" if has_sound else "[2:a]anull[a]"
    ff = subprocess.Popen(
        ["ffmpeg", "-y", "-v", "error",
         "-i", base,
         "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
         "-i", audio,
         "-filter_complex", f"[0:v][1:v]overlay=format=auto,format=yuv420p[v];{audio_filter}",
         "-map", "[v]", "-map", "[a]",
         "-c:v", "libx264", "-preset", "slow", "-crf", "17", "-profile:v", "high",
         "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
         "-movflags", "+faststart", "-t", f"{cfg.total}", out_path],
        stdin=subprocess.PIPE)

    tag_end = cfg.end_start if cfg.end_card else cfg.total + 1
    for n in range(int(round(cfg.total * FPS))):
        t = n / FPS
        frame = Image.new("RGBA", (W, H), (0, 0, 0, 0))

        # title tag: slides in from the left at the start, leaves before the end card
        if tag and t < tag_end:
            slide = min(1.0, t / 0.3)
            fade = min(1.0, (tag_end - t) / 0.15)
            x = int(-tag.width + (cfg.safe_left + tag.width) * (1 - (1 - slide) ** 3))
            paste_scaled(frame, tag, x + tag.width / 2, cfg.safe_top + 20 * cfg.k + tag.height / 2, 1.0, fade)

        # captions: each line pops 0.12 s after the one above it
        for cap in caps:
            first_y = cap["y"] - cap["step"] * (len(cap["sprites"]) - 1) / 2
            for j, sprite in enumerate(cap["sprites"]):
                scale, alpha = pop(t, cap["start"] + 0.12 * j, cap["end"])
                paste_scaled(frame, sprite, centre_x, first_y + cap["step"] * j, scale, alpha)

        # end card
        if cfg.end_card and t >= cfg.end_start:
            te = t - cfg.end_start
            forever = cfg.end_dur + 1
            for j, (sprite, cy) in enumerate(zip(layout["title_sprites"], layout["title_centres"])):
                s, a = pop(te, 0.05 + 0.12 * j, forever)
                paste_scaled(frame, sprite, W / 2, cy, s, a)
            if layout["features"]:
                s, a = pop(te, 0.45, forever)
                paste_scaled(frame, layout["features"], W / 2, layout["feats_y"], s, a)
            if layout["button"]:
                s, a = pop(te, 0.75, forever)
                pulse = 1.0 + 0.035 * math.sin((te - 1.0) * 2 * math.pi * 1.5) if te > 1.0 else 1.0
                paste_scaled(frame, layout["button"], W / 2 - 20 * cfg.k, layout["button_y"], s * pulse, a)
            if layout["arrow"] and layout["button"]:
                s, a = pop(te, 1.0, forever)
                bounce = 16 * abs(math.sin(max(0.0, te - 1.0) * math.pi * 1.6))
                side = -1 if layout["arrow_dir"] == "down_left" else 1
                ax = 170 * cfg.k if side < 0 else W - 170 * cfg.k
                paste_scaled(frame, layout["arrow"], ax + side * bounce, layout["arrow_y"] + bounce - 20, s, a)

        ff.stdin.write(frame.tobytes())
    ff.stdin.close()
    if ff.wait() != 0:
        sys.exit("ffmpeg failed while adding the text")


# ---------------------------------------------------------------------------
# MAIN: run the five steps
# ---------------------------------------------------------------------------
def main():
    if len(sys.argv) != 4:
        sys.exit("Usage: python3 build_ad.py <settings.json> <footage folder> <output.mp4>")
    cfg_path, src_dir, out_path = sys.argv[1], sys.argv[2], sys.argv[3]
    cfg = Settings(cfg_path)
    tmp = os.path.join(os.path.dirname(os.path.abspath(out_path)), "_build_tmp")
    os.makedirs(tmp, exist_ok=True)

    print(f"1/5 cutting {len(cfg.shots)} shots")
    pieces = [cut_shot(cfg, src_dir, tmp, i, shot) for i, shot in enumerate(cfg.shots)]
    layout = None
    if cfg.end_card:
        print("2/5 end card")
        layout = prepare_end_card(cfg, find_font("black"), find_font("bold"))
        finish_end_layout(cfg, layout, load_end_photo(cfg, src_dir, tmp))
        pieces.append(make_end_card(cfg, src_dir, tmp, layout))
    else:
        print("2/5 no end card in settings, skipping")
    print("3/5 joining")
    base = join(tmp, pieces)
    print("4/5 sound")
    audio, has_sound = make_audio(cfg, src_dir, tmp)
    print("5/5 text and final export")
    make_overlay_and_finish(cfg, tmp, base, audio, has_sound, out_path, layout)

    print(f"done: {out_path}  ({cfg.total:.1f} s)")
    marks = "  ".join(f"shot {i + 1} at {s:.1f}s" for i, s in enumerate(cfg.starts))
    print(f"timeline: {marks}" + (f"  end card at {cfg.end_start:.1f}s" if cfg.end_card else ""))


if __name__ == "__main__":
    main()
