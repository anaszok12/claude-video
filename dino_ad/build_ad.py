"""
build_ad.py  |  Builds the 21 second TikTok ad for the dino scooter.

HOW TO RUN
    python3 build_ad.py <folder with the footage> <output.mp4>

WHAT IT DOES, IN ORDER
    1. Cuts 6 short pieces out of the phone clips (the "shots").
    2. Makes the end card from a still photo.
    3. Glues the 7 pieces into one silent video.
    4. Builds the sound track from the toy's own sounds.
    5. Draws the animated text, frame by frame, and lays it on top.

Needs: ffmpeg (video tool) and the Python library Pillow (drawing tool).
"""

import glob
import math
import os
import subprocess
import sys

from PIL import Image, ImageDraw, ImageFilter, ImageFont

# ---------------------------------------------------------------------------
# SETTINGS
# ---------------------------------------------------------------------------
W, H = 1080, 1920          # TikTok portrait size in pixels
FPS = 30                   # frames per second of the finished ad

FONT_BIG = "/usr/share/fonts/opentype/inter/InterDisplay-Black.otf"
FONT_BOLD = "/usr/share/fonts/opentype/inter/InterDisplay-ExtraBold.otf"

WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
YELLOW = (255, 217, 40)    # accent colour, matches the TikTok yellow basket
GREEN = (182, 242, 58)     # small kicker text in the title tag

# TikTok covers the edges of the video with its own buttons and caption.
# All text stays inside this box so nothing gets hidden.
SAFE_LEFT, SAFE_RIGHT = 60, 920
SAFE_TOP, SAFE_BOTTOM = 190, 1500

# ---------------------------------------------------------------------------
# THE SHOT LIST
# Each shot says: which clip, where to start (seconds), how long it lasts in
# the ad, how much to speed it up, and how much to zoom (start, end).
#   focus = which part of the picture the zoom aims at (0 = left/top, 1 = right/bottom)
# ---------------------------------------------------------------------------
SHOTS = [
    # 1 HOOK: jaw is already swinging open on frame one, roar is loud by 0.3 s, jaw snaps shut at the end
    dict(clip="IMG_6315", start=6.65, dur=2.5, speed=1.0, zoom=(1.00, 1.12), focus=(0.45, 0.35)),
    # 2 A hand pushes the dino and it rolls away
    dict(clip="IMG_6318", start=0.90, dur=2.0, speed=1.0, zoom=(1.00, 1.00), focus=(0.5, 0.5)),
    # 3 Walk around the whole toy, played 2.5 times faster
    dict(clip="IMG_6314", start=1.00, dur=3.8, speed=2.5, zoom=(1.00, 1.00), focus=(0.5, 0.5)),
    # 4 Finger presses the red buttons
    dict(clip="IMG_6316", start=5.50, dur=3.2, speed=1.0, zoom=(1.00, 1.05), focus=(0.5, 0.4)),
    # 5 Eye switches on and off
    dict(clip="IMG_6317", start=0.75, dur=3.0, speed=1.0, zoom=(1.05, 1.15), focus=(0.4, 0.25)),
    # 6 Second roar: jaw is shut for a moment, then opens, zoomed in closer than the hook
    dict(clip="IMG_6315", start=9.65, dur=2.7, speed=1.0, zoom=(1.15, 1.35), focus=(0.45, 0.38)),
]
END_CARD_DUR = 4.0         # seconds for the final "tap the basket" screen
END_CARD_PHOTO = "62ee2a71-image.jpg"   # the side view photo

# Work out when each shot starts on the ad timeline (running total).
STARTS = []
_t = 0.0
for _s in SHOTS:
    STARTS.append(_t)
    _t += _s["dur"]
END_CARD_START = _t
TOTAL = _t + END_CARD_DUR

# ---------------------------------------------------------------------------
# THE SOUND LIST
# Each line: which clip's sound, where to start in that clip, how long,
# where it lands on the ad timeline, and a volume boost in decibels.
# ---------------------------------------------------------------------------
SOUNDS = [
    dict(clip="IMG_6315", start=6.65, dur=2.5, at=STARTS[0], gain=0),        # roar
    dict(clip="IMG_6318", start=0.90, dur=2.0, at=STARTS[1], gain=8),        # wheels rolling
    # toy music starts under shot 3 and carries on into shot 4 without a break
    dict(clip="IMG_6316", start=5.50 - 3.8, dur=3.8 + 3.2, at=STARTS[2], gain=6),
    dict(clip="IMG_6317", start=0.75, dur=3.0, at=STARTS[4], gain=6),        # light and sound
    dict(clip="IMG_6315", start=9.65, dur=2.7, at=STARTS[5], gain=0),        # second roar
    dict(clip="IMG_6316", start=9.00, dur=END_CARD_DUR, at=END_CARD_START, gain=2, fade_out=1.2),
]

# ---------------------------------------------------------------------------
# THE TEXT LIST
# Each caption: when it appears, when it leaves, and its lines.
# A line is a list of (words, colour) pairs so one word can be yellow.
# ---------------------------------------------------------------------------
def _cap(shot, lines, size, y, lead=0.10, tail=0.12):
    start = STARTS[shot] + lead
    end = STARTS[shot] + SHOTS[shot]["dur"] - tail
    return dict(start=start, end=end, lines=lines, size=size, y=y)

CAPTIONS = [
    _cap(0, [[("THIS DINO", WHITE)], [("REALLY ", WHITE), ("ROARS", YELLOW)]], 112, 1240, lead=0.05),
    _cap(1, [[("AND YOUR KID", WHITE)], [("CAN ", WHITE), ("RIDE", YELLOW), (" IT", WHITE)]], 110, 1240),
    _cap(2, [[("A dino scooter", WHITE)], [("for ", WHITE), ("ages 3", YELLOW), (" and up", WHITE)]], 84, 1290),
    _cap(3, [[("Press the buttons", WHITE)], [("for ", WHITE), ("music", YELLOW)]], 84, 1290),
    _cap(4, [[("Eyes ", WHITE), ("light up", YELLOW)], [("bright green", WHITE)]], 84, 1290),
    _cap(5, [[("JAW OPENS.", WHITE)], [("THEN IT ", WHITE), ("ROARS.", YELLOW)]], 104, 1260),
]


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
    """Find a file in the footage folder whose name contains `name`."""
    hits = glob.glob(os.path.join(src_dir, f"*{name}*"))
    if not hits:
        sys.exit(f"Could not find a file containing '{name}' in {src_dir}")
    return hits[0]


def ease_out_back(x):
    """Turns a 0..1 progress value into a 'pop' that overshoots a little then settles."""
    c1, c3 = 1.70158, 2.70158
    return 1 + c3 * (x - 1) ** 3 + c1 * (x - 1) ** 2


# ---------------------------------------------------------------------------
# STEP 1: CUT THE SHOTS
# ---------------------------------------------------------------------------
def cut_shot(src_dir, tmp, i, shot):
    out = os.path.join(tmp, f"shot{i}.mp4")
    src_len = shot["dur"] * shot["speed"]        # how much of the phone clip we use
    z0, z1 = shot["zoom"]
    fx, fy = shot["focus"]
    # zoom grows smoothly from z0 to z1 over the life of the shot
    z = f"({z0}+({z1}-{z0})*t/{shot['dur']})"
    filters = (
        f"setpts=(PTS-STARTPTS)/{shot['speed']},"       # speed up if needed
        f"fps={FPS},"
        f"scale=w='2*trunc({W}*{z}/2)':h='2*trunc({H}*{z}/2)':eval=frame,"
        f"crop={W}:{H}:x='(iw-{W})*{fx}':y='(ih-{H})*{fy}',"
        f"eq=saturation=1.12:contrast=1.04,"             # a touch more colour
        f"format=yuv420p"
    )
    run(["ffmpeg", "-y", "-v", "error", "-ss", str(shot["start"]), "-t", str(src_len),
         "-i", find(src_dir, shot["clip"]), "-an", "-vf", filters, "-t", str(shot["dur"]),
         "-c:v", "libx264", "-preset", "medium", "-crf", "14", out])
    return out


# ---------------------------------------------------------------------------
# STEP 2: END CARD (blurred photo behind, sharp photo in front, slow zoom)
# ---------------------------------------------------------------------------
def make_end_card(src_dir, tmp):
    out = os.path.join(tmp, "endcard.mp4")
    photo = Image.open(find(src_dir, END_CARD_PHOTO)).convert("RGB")

    # background: the same photo, stretched to fill, blurred and darkened
    scale = max(W / photo.width, H / photo.height)
    bg = photo.resize((int(photo.width * scale) + 1, int(photo.height * scale) + 1))
    left = (bg.width - W) // 2
    bg = bg.crop((left, 0, left + W, H)).filter(ImageFilter.GaussianBlur(40))
    bg = Image.blend(bg, Image.new("RGB", (W, H), (10, 14, 8)), 0.55)
    bg.save(os.path.join(tmp, "end_bg.png"))

    # foreground: the photo at full width, with rounded corners
    fg_w = W - 80
    fg_h = int(photo.height * fg_w / photo.width)
    fg = photo.resize((fg_w * 2, fg_h * 2), Image.LANCZOS)      # 2x size keeps the zoom sharp
    mask = Image.new("L", fg.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, fg.width, fg.height), radius=72, fill=255)
    fg.putalpha(mask)
    fg.save(os.path.join(tmp, "end_fg.png"))

    z = f"(1+0.06*t/{END_CARD_DUR})"
    graph = (
        f"[1:v]scale=w='2*trunc({fg_w}*{z}/2)':h='2*trunc({fg_h}*{z}/2)':eval=frame[fg];"
        f"[0:v][fg]overlay=x='(W-w)/2':y='480+({fg_h}-h)/2':format=auto,"
        f"eq=saturation=1.12:contrast=1.04,format=yuv420p[v]"
    )
    run(["ffmpeg", "-y", "-v", "error",
         "-loop", "1", "-framerate", str(FPS), "-i", os.path.join(tmp, "end_bg.png"),
         "-loop", "1", "-framerate", str(FPS), "-i", os.path.join(tmp, "end_fg.png"),
         "-filter_complex", graph, "-map", "[v]", "-t", str(END_CARD_DUR),
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
def make_audio(src_dir, tmp):
    out = os.path.join(tmp, "audio.wav")
    cmd = ["ffmpeg", "-y", "-v", "error"]
    chains, labels = [], []
    for i, s in enumerate(SOUNDS):
        cmd += ["-ss", str(s["start"]), "-t", str(s["dur"]), "-i", find(src_dir, s["clip"])]
        fade_out = s.get("fade_out", 0.06)
        delay_ms = int(round(s["at"] * 1000))
        chains.append(
            f"[{i}:a]aresample=48000,aformat=channel_layouts=stereo,volume={s['gain']}dB,"
            f"afade=t=in:d=0.04,afade=t=out:st={s['dur'] - fade_out}:d={fade_out},"   # tiny fades stop clicks at the cuts
            f"adelay={delay_ms}:all=1[a{i}]"
        )
        labels.append(f"[a{i}]")
    graph = ";".join(chains) + ";" + "".join(labels) + (
        f"amix=inputs={len(SOUNDS)}:normalize=0:duration=longest,"
        f"alimiter=limit=0.89,apad,atrim=0:{TOTAL}[a]"
    )
    run(cmd + ["-filter_complex", graph, "-map", "[a]", out])
    return out


# ---------------------------------------------------------------------------
# STEP 5: ANIMATED TEXT
# ---------------------------------------------------------------------------
def render_lines(lines, size, font_path=FONT_BIG, stroke=None):
    """Draw a block of centred text lines onto a see-through picture and return it."""
    font = ImageFont.truetype(font_path, size)
    stroke = stroke if stroke is not None else max(6, size // 11)
    pad = stroke + 24
    gap = int(size * 0.14)
    widths, line_h = [], int(size * 1.02)
    for line in lines:
        widths.append(sum(font.getlength(text) for text, _ in line))
    block_w = int(max(widths)) + pad * 2
    block_h = line_h * len(lines) + gap * (len(lines) - 1) + pad * 2

    def draw_text(target, fill_override=None, stroke_w=0):
        d = ImageDraw.Draw(target)
        y = pad
        for line, lw in zip(lines, widths):
            x = (block_w - lw) / 2
            for text, colour in line:
                d.text((x, y), text, font=font, fill=fill_override or colour,
                       stroke_width=stroke_w, stroke_fill=fill_override or BLACK)
                x += font.getlength(text)
            y += line_h + gap

    # soft shadow, then black outline, then the coloured letters on top
    shadow = Image.new("RGBA", (block_w, block_h), (0, 0, 0, 0))
    draw_text(shadow, fill_override=(0, 0, 0, 150), stroke_w=stroke)
    shadow = shadow.filter(ImageFilter.GaussianBlur(10))
    img = Image.new("RGBA", (block_w, block_h), (0, 0, 0, 0))
    img.alpha_composite(shadow, (0, 8))
    outline = Image.new("RGBA", (block_w, block_h), (0, 0, 0, 0))
    draw_text(outline, fill_override=BLACK + (255,), stroke_w=stroke)
    img.alpha_composite(outline)
    letters = Image.new("RGBA", (block_w, block_h), (0, 0, 0, 0))
    draw_text(letters)
    img.alpha_composite(letters)
    return img


def render_tag():
    """The small black title tag pinned top left (same idea as the news style sample)."""
    kicker_font = ImageFont.truetype(FONT_BOLD, 26)
    title_font = ImageFont.truetype(FONT_BOLD, 50)
    kicker, title = "RIDE ON TOY", "Dino Scooter"
    w = int(max(kicker_font.getlength(kicker), title_font.getlength(title))) + 56
    h = 136
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((0, 0, w, h), radius=10, fill=(12, 12, 12, 235))
    d.text((28, 20), kicker, font=kicker_font, fill=GREEN)
    d.text((28, 54), title, font=title_font, fill=WHITE)
    return img


def render_button():
    """Yellow 'TAP THE YELLOW BASKET' button for the end card."""
    font = ImageFont.truetype(FONT_BIG, 62)
    text = "TAP THE YELLOW BASKET"
    w, h = int(font.getlength(text)) + 90, 132
    img = Image.new("RGBA", (w + 24, h + 24), (0, 0, 0, 0))
    shadow = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(shadow).rounded_rectangle((12, 20, w + 12, h + 20), radius=h // 2, fill=(0, 0, 0, 170))
    img.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(8)))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((12, 8, w + 12, h + 8), radius=h // 2, fill=YELLOW)
    d.text((12 + w / 2, 8 + h / 2), text, font=font, fill=BLACK, anchor="mm")
    return img


def render_arrow():
    """Chunky yellow arrow that points down and to the left, toward the basket."""
    size = 220
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    # arrow drawn pointing straight down, then turned 45 degrees
    shape = [(85, 10), (135, 10), (135, 120), (185, 120), (110, 210), (35, 120), (85, 120)]
    outline = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    ImageDraw.Draw(outline).polygon(shape, fill=BLACK)
    outline = outline.filter(ImageFilter.MaxFilter(13))        # fatten the black shape into an outline
    img.alpha_composite(outline)
    ImageDraw.Draw(img).polygon(shape, fill=YELLOW)
    return img.rotate(-45, resample=Image.BICUBIC)


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


def make_overlay_and_finish(tmp, base, audio, out_path):
    """Draw every text frame and feed it straight into ffmpeg, which lays it over the video."""
    centre_x = (SAFE_LEFT + SAFE_RIGHT) // 2          # text sits a little left of centre, clear of TikTok's buttons

    sprites = []
    for cap in CAPTIONS:
        # each line is its own picture so the lines can pop in one after another
        line_imgs = [render_lines([line], cap["size"]) for line in cap["lines"]]
        for im in line_imgs:
            pad = max(6, cap["size"] // 11) + 24       # empty margin around the letters
            assert im.width - 2 * pad <= SAFE_RIGHT - SAFE_LEFT, f"caption too wide: {cap['lines']}"
        sprites.append(line_imgs)

    tag = render_tag()
    end_title = [render_lines([[("DINO", YELLOW)]], 170), render_lines([[("SCOOTER", WHITE)]], 136)]
    end_feats = render_lines([[("Roars. Lights up. Plays music.", WHITE)]], 54, font_path=FONT_BOLD, stroke=5)
    button = render_button()
    arrow = render_arrow()

    ff = subprocess.Popen(
        ["ffmpeg", "-y", "-v", "error",
         "-i", base,
         "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
         "-i", audio,
         "-filter_complex",
         "[0:v][1:v]overlay=format=auto,format=yuv420p[v];"
         "[2:a]loudnorm=I=-14:TP=-1.5:LRA=11[a]",
         "-map", "[v]", "-map", "[a]",
         "-c:v", "libx264", "-preset", "slow", "-crf", "17", "-profile:v", "high",
         "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
         "-movflags", "+faststart", "-t", f"{TOTAL}", out_path],
        stdin=subprocess.PIPE)

    n_frames = int(round(TOTAL * FPS))
    for n in range(n_frames):
        t = n / FPS
        frame = Image.new("RGBA", (W, H), (0, 0, 0, 0))

        # title tag: slides in from the left at the start, leaves before the end card
        if t < END_CARD_START:
            slide = min(1.0, t / 0.3)
            fade = min(1.0, (END_CARD_START - t) / 0.15)
            x = int(-tag.width + (SAFE_LEFT + tag.width) * (1 - (1 - slide) ** 3))
            paste_scaled(frame, tag, x + tag.width / 2, SAFE_TOP + 20 + tag.height / 2, 1.0, fade)

        # captions: line 2 pops 0.12 s after line 1
        for cap, line_imgs in zip(CAPTIONS, sprites):
            line_h = line_imgs[0].height - 2 * (max(6, cap["size"] // 11) + 24) + int(cap["size"] * 0.14)
            first_y = cap["y"] - line_h * (len(line_imgs) - 1) / 2
            for k, im in enumerate(line_imgs):
                scale, alpha = pop(t, cap["start"] + 0.12 * k, cap["end"])
                paste_scaled(frame, im, centre_x, first_y + line_h * k, scale, alpha)

        # end card
        if t >= END_CARD_START:
            te = t - END_CARD_START
            s, a = pop(te, 0.05, END_CARD_DUR + 1)
            paste_scaled(frame, end_title[0], W / 2, 262, s, a)
            s, a = pop(te, 0.17, END_CARD_DUR + 1)
            paste_scaled(frame, end_title[1], W / 2, 392, s, a)
            s, a = pop(te, 0.45, END_CARD_DUR + 1)
            paste_scaled(frame, end_feats, W / 2, 1285, s, a)
            s, a = pop(te, 0.75, END_CARD_DUR + 1)
            pulse = 1.0 + 0.035 * math.sin(max(0.0, te - 1.0) * 2 * math.pi * 1.5) if te > 1.0 else 1.0
            paste_scaled(frame, button, W / 2 - 20, 1395, s * pulse, a)
            s, a = pop(te, 1.0, END_CARD_DUR + 1)
            bounce = 16 * abs(math.sin(max(0.0, te - 1.0) * math.pi * 1.6))
            paste_scaled(frame, arrow, 170 - bounce, 1525 + bounce - 20, s, a)

        ff.stdin.write(frame.tobytes())
    ff.stdin.close()
    if ff.wait() != 0:
        sys.exit("ffmpeg failed while adding the text")


# ---------------------------------------------------------------------------
# MAIN: run the five steps
# ---------------------------------------------------------------------------
def main():
    if len(sys.argv) != 3:
        sys.exit("Usage: python3 build_ad.py <footage folder> <output.mp4>")
    src_dir, out_path = sys.argv[1], sys.argv[2]
    tmp = os.path.join(os.path.dirname(os.path.abspath(out_path)), "_build_tmp")
    os.makedirs(tmp, exist_ok=True)

    print("1/5 cutting shots")
    pieces = [cut_shot(src_dir, tmp, i, shot) for i, shot in enumerate(SHOTS)]
    print("2/5 end card")
    pieces.append(make_end_card(src_dir, tmp))
    print("3/5 joining")
    base = join(tmp, pieces)
    print("4/5 sound")
    audio = make_audio(src_dir, tmp)
    print("5/5 text and final export")
    make_overlay_and_finish(tmp, base, audio, out_path)
    print(f"done: {out_path}  ({TOTAL:.1f} s)")


if __name__ == "__main__":
    main()
