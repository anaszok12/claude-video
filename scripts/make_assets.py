"""
Makes two kinds of assets for the video, with no downloads and no copyright worries:

  1. public/paper.png      a paper texture (cream colour, grain, fold creases)
  2. public/sfx/*.wav      sound effects built from maths (noise, sine waves)

Run it with:  python3 scripts/make_assets.py
It needs numpy and pillow:  pip install numpy pillow
"""
import os
import wave

import numpy as np
from PIL import Image, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PUBLIC = os.path.join(ROOT, "public")
SFX_DIR = os.path.join(PUBLIC, "sfx")
os.makedirs(SFX_DIR, exist_ok=True)

SR = 48000  # audio sample rate, same as the raw clip
rng = np.random.default_rng(7)  # fixed seed so every run gives the same result


# ---------------------------------------------------------------- paper texture
def make_paper():
    W, H = 1080, 1920
    base = np.zeros((H, W, 3), dtype=np.float32)
    base[:] = (238, 233, 222)  # warm off white, like newsprint

    # fine grain: random noise, slightly blurred
    grain = rng.normal(0, 7, (H, W)).astype(np.float32)
    grain_img = Image.fromarray(np.clip(grain + 128, 0, 255).astype(np.uint8)).filter(
        ImageFilter.GaussianBlur(0.7)
    )
    grain = np.asarray(grain_img).astype(np.float32) - 128
    base += grain[..., None] * 1.6

    # soft cloudy blotches (big blurred noise) so it does not look flat
    blotch = rng.normal(0, 1, (H // 40, W // 40)).astype(np.float32)
    blotch_img = Image.fromarray(
        np.clip(blotch * 40 + 128, 0, 255).astype(np.uint8)
    ).resize((W, H), Image.BICUBIC)
    blotch = np.asarray(blotch_img.filter(ImageFilter.GaussianBlur(30))).astype(np.float32) - 128
    base += blotch[..., None] * 0.09

    # fold creases: one vertical, two horizontal, as a dark line plus a light line
    yy, xx = np.mgrid[0:H, 0:W]

    def crease(dist, strength=10.0):
        dark = np.exp(-(dist / 1.6) ** 2) * strength
        light = np.exp(-((dist - 3.5) / 2.5) ** 2) * strength * 0.7
        return light - dark

    c = crease(np.abs(xx - 540 + 2 * np.sin(yy / 160.0)))
    c += crease(np.abs(yy - 640 + 2 * np.sin(xx / 120.0)))
    c += crease(np.abs(yy - 1280 + 2 * np.sin(xx / 140.0)))
    base += c[..., None]

    # vignette: edges a little darker
    d = np.sqrt(((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2)
    base *= (1 - 0.10 * np.clip(d - 0.6, 0, 1) ** 1.5)[..., None]

    Image.fromarray(np.clip(base, 0, 255).astype(np.uint8)).save(
        os.path.join(PUBLIC, "paper.png")
    )


# ---------------------------------------------------------------- audio helpers
def t_axis(seconds):
    return np.arange(int(SR * seconds)) / SR


def env_exp(n, decay):
    """Fast attack, exponential fade out."""
    t = np.arange(n) / SR
    attack = np.clip(t / 0.004, 0, 1)
    return attack * np.exp(-t * decay)


def lowpass(x, cutoff):
    """Very simple one pole low pass filter (smooths the signal)."""
    a = np.exp(-2 * np.pi * cutoff / SR)
    out = np.zeros_like(x)
    prev = 0.0
    for i, v in enumerate(x):
        prev = (1 - a) * v + a * prev
        out[i] = prev
    return out


def highpass(x, cutoff):
    return x - lowpass(x, cutoff)


def sweep_noise(seconds, f_start, f_end, q_smooth=4):
    """White noise whose brightness glides from f_start to f_end. This is a whoosh."""
    n = int(SR * seconds)
    noise = rng.normal(0, 1, n)
    out = np.zeros(n)
    prev = 0.0
    freqs = np.geomspace(f_start, f_end, n)
    for i in range(n):
        a = np.exp(-2 * np.pi * freqs[i] / SR)
        prev = (1 - a) * noise[i] + a * prev
        out[i] = prev
    # also remove the very low rumble so it sounds airy
    out = highpass(out, 150)
    return out


def normalize(x, peak=0.9):
    m = np.max(np.abs(x))
    return x / m * peak if m > 0 else x


def fade_edges(x, ms=8):
    n = int(SR * ms / 1000)
    x = x.copy()
    x[:n] *= np.linspace(0, 1, n)
    x[-n:] *= np.linspace(1, 0, n)
    return x


def save(name, x, peak=0.9):
    x = fade_edges(normalize(x, peak))
    data = (x * 32767).astype(np.int16)
    with wave.open(os.path.join(SFX_DIR, name), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(data.tobytes())


# ---------------------------------------------------------------- the sounds
def make_sfx():
    # WHOOSH: used on every transition. Noise that gets brighter, then fades.
    n = int(SR * 0.55)
    w = sweep_noise(0.55, 400, 7000)
    shape = np.sin(np.linspace(0, np.pi, n)) ** 1.5
    save("whoosh.wav", w * shape, 0.85)

    # SHORT WHOOSH: quick one for small card moves
    n = int(SR * 0.3)
    w = sweep_noise(0.3, 600, 6000)
    save("whoosh_short.wav", w * np.sin(np.linspace(0, np.pi, n)) ** 1.2, 0.8)

    # POP: a sine wave that drops in pitch very fast. Used for each counted number.
    t = t_axis(0.18)
    freq = 900 * np.exp(-t * 18) + 220
    phase = 2 * np.pi * np.cumsum(freq) / SR
    save("pop.wav", np.sin(phase) * env_exp(len(t), 22), 0.9)

    # TICK: tiny dry click for small UI style moments
    t = t_axis(0.06)
    click = rng.normal(0, 1, len(t)) * env_exp(len(t), 90)
    click = highpass(click, 1500) + 0.5 * np.sin(2 * np.pi * 1800 * t) * env_exp(len(t), 120)
    save("tick.wav", click, 0.7)

    # STAMP: heavy thud (low sine) plus a paper slap (noise). For the big ZOMBIE word.
    t = t_axis(0.5)
    freq = 140 * np.exp(-t * 9) + 45
    thud = np.sin(2 * np.pi * np.cumsum(freq) / SR) * env_exp(len(t), 8)
    slap = lowpass(rng.normal(0, 1, len(t)), 3500) * env_exp(len(t), 45)
    save("stamp.wav", thud * 1.0 + slap * 0.55, 0.95)

    # BOOM: deeper, longer hit for the opening title
    t = t_axis(1.1)
    freq = 90 * np.exp(-t * 4) + 34
    boom = np.sin(2 * np.pi * np.cumsum(freq) / SR) * env_exp(len(t), 3.2)
    air = lowpass(rng.normal(0, 1, len(t)), 900) * env_exp(len(t), 6)
    save("boom.wav", boom + air * 0.4, 0.95)

    # RISER: noise and a sine that climb upward. Builds tension before a reveal.
    seconds = 1.6
    t = t_axis(seconds)
    n = len(t)
    noise = sweep_noise(seconds, 300, 9000) * (t / seconds) ** 2.0
    tone = np.sin(2 * np.pi * np.cumsum(np.geomspace(180, 1400, n)) / SR) * (t / seconds) ** 2.5
    save("riser.wav", noise * 0.9 + tone * 0.35, 0.85)

    # PAPER: rustle for paper cards sliding. Short bursts of band limited noise.
    t = t_axis(0.35)
    rustle = rng.normal(0, 1, len(t))
    rustle = highpass(lowpass(rustle, 6000), 800)
    bursts = (
        (np.sin(2 * np.pi * 23 * t) > 0.3) * 0.6 + 0.4
    ) * np.sin(np.linspace(0, np.pi, len(t))) ** 1.3
    save("paper.wav", rustle * bursts, 0.65)

    # MARKER: highlighter swipe. Noisy scratch, a bit longer.
    t = t_axis(0.38)
    s = highpass(rng.normal(0, 1, len(t)), 2500)
    s *= (0.65 + 0.35 * np.sin(2 * np.pi * 38 * t)) * np.sin(np.linspace(0, np.pi, len(t))) ** 0.8
    save("marker.wav", s, 0.55)

    # SPARKLE: three quick rising bell notes. For "mata!" (eye).
    out = np.zeros(int(SR * 0.9))
    for k, f in enumerate([1318.5, 1760.0, 2349.3]):
        start = int(SR * 0.07 * k)
        t = t_axis(0.6)
        note = (np.sin(2 * np.pi * f * t) + 0.35 * np.sin(2 * np.pi * f * 2.01 * t)) * env_exp(len(t), 7)
        out[start : start + len(note)] += note
    save("sparkle.wav", out, 0.7)

    # SPOOKY STING: for "zombie". Low detuned tones that wobble, then fade.
    t = t_axis(1.0)
    a = np.sin(2 * np.pi * 110 * t + 3 * np.sin(2 * np.pi * 5 * t))
    b = np.sin(2 * np.pi * 116.5 * t + 3 * np.sin(2 * np.pi * 4.3 * t))
    c = np.sin(2 * np.pi * 164.8 * t)
    sting = (a + b + 0.5 * c) * np.exp(-t * 2.6) * np.clip(t / 0.03, 0, 1)
    save("sting.wav", sting, 0.8)

    # DING: friendly confirmation for the "Ada ke?" question beat
    t = t_axis(0.7)
    ding = (np.sin(2 * np.pi * 988 * t) + 0.3 * np.sin(2 * np.pi * 1976 * t)) * env_exp(len(t), 6)
    save("ding.wav", ding, 0.7)


if __name__ == "__main__":
    make_paper()
    make_sfx()
    print("done:", sorted(os.listdir(SFX_DIR)))
