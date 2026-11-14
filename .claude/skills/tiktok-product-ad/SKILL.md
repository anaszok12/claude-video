---
name: tiktok-product-ad
description: Turn raw phone footage and photos of a physical product into a finished vertical short form ad (TikTok, TikTok Shop, Shopee Video, Reels, Shorts) with a hook, animated captions, the product's own sound and a call to action end card. Use this skill whenever the user uploads product clips or photos and asks for an ad, promo, product video, affiliate video or "a video like these samples", when they attach reference ads and ask to study the hook, motion, pacing or length, or when they want an existing product video re cut, shortened or re captioned. Use it even if they never say "TikTok" or "ad", as long as the goal is a short selling video made from their own footage.
---

# TikTok product ad

Builds a 15 to 30 second vertical ad (1080x1920) from the user's own footage. You study the footage, plan a shot list, write it into a settings file, and a bundled script renders the video.

You cannot watch video or hear audio. The whole workflow is built around that limit: `scripts/study_footage.py` turns video into contact sheets (pictures you can read), cut times, a loudness timeline and optional transcripts. Never describe or plan around something you have not seen on a sheet or measured.

## What you need from the user

- **Product footage** (required): video clips and or photos. If there is none, ask for it. Do not build an ad from listing screenshots alone, because they are someone else's marketing images.
- **Reference ads** (optional): samples whose style they like.
- **Listing screenshots or description** (optional): a source of feature claims and the product name.

## Workflow

### 1. Study everything

```bash
python3 scripts/study_footage.py <folder or files> --out <scratch folder>/study --transcribe
```

Read every contact sheet it writes. `--transcribe` needs `pip install faster-whisper`; if that cannot be installed, drop the flag and carry on.

For **reference ads**, note three things per sample: what the first 2 to 4 seconds do (the hook), the cut rhythm (the script prints shot lengths), and the total length. Reference ads set the style only. Do not copy their wording, logos or footage.

For the **user's footage**, build an inventory: what each clip shows, the exact seconds of its best moment, and what its sound does. Sheets are coarse (one frame per 0.5 s or more), so before committing to a start time, pull a finer strip of that moment:

```bash
ffmpeg -ss <start> -t 2 -i <clip> -vf "fps=8,scale=-2:384,tile=8x2" -frames:v 1 strip.jpg
```

Use the loudness rows to find where a sound actually becomes loud. A sound effect often ramps up for half a second, and a hook that opens on the quiet ramp feels dead.

Check the transcript for people talking in the background. Raw home footage often has family voices, and the user will not expect those in a public ad. If a clip has speech that is not part of the product, set that shot's `"sound": "none"` and say so.

### 2. Ask one question, then build

Unless the user's message says otherwise, assume:

| Setting | Default |
|---|---|
| Style and length | Hybrid, about 22 s: bold text hook, then hands on close ups with a pinned title tag, then end card |
| Language of on screen text | English |
| Ending | "TAP THE YELLOW BASKET" with an arrow to the bottom left, no price |

Do not re ask these. Do ask this, in one question:

> Which of these features have you confirmed on your own unit?

List only claims from the listing that the footage does **not** already prove. Anything visible or audible in the footage counts as proven. Put only proven or confirmed claims on screen. The reason: marketplace listings routinely overstate (the dino toy that started this skill was listed with a smoke effect the buyer never confirmed), and the ad goes out under the user's name.

No price by default because voucher prices expire and a stale price makes the ad wrong.

If there is no listing and nothing unproven, skip the question and build.

### 3. Plan the shot list

What the reference study behind this skill found, and why each rule exists:

- **Open on the payoff.** Frame one shows the product already doing its most surprising thing, with its sound, and the claim as text. Viewers decide in the first second, and none of the strong samples spent time on an introduction.
- **6 to 8 shots of 2 to 4 seconds**, then a 4 second end card. Shorter than 2 s and a caption cannot be read; longer than 4 s and a product close up goes stale.
- **One idea per caption**, two lines at most, about 14 characters per line at hook size and 18 at feature size. Mark the one word that matters with stars so it takes the accent colour.
- **Shot 2 answers "what is it for".** After the surprise, show the main use.
- **Bring the best trick back just before the end card**, from a different moment or a tighter zoom, so the last thing seen before the call to action is the strongest.
- **Speed up slow camera moves** (walk arounds, pans) 2 to 3 times instead of cutting them out. They show the whole product quickly.
- **Vary the framing between neighbours.** Two shots from the same clip need different zoom or they read as a glitch.
- **Sound**: use the product's own sound when it has one. A sped up shot has no usable sound, so lay sound from another clip under it with a `sounds` entry so there is no silent hole. Do not add music you have no rights to. Tell the user to add a trending sound inside the TikTok app at low volume.

If the product makes no sound and does nothing dramatic, the hook is a bold claim over the most attractive moving shot.

### 4. Write the settings file and render

The settings file is JSON. Read `references/config.md` for every field, and start from `assets/example_dino_scooter.json`, a complete working example.

```bash
python3 scripts/build_ad.py <settings.json> <footage folder> <output.mp4>
```

Save the settings file and the output where the user can reach them. The script prints a note when it had to shrink a caption to fit, which means the wording is too long: shorten it instead of accepting small text.

### 5. Check the render before showing it

```bash
python3 scripts/study_footage.py <output.mp4> --out <scratch folder>/check
```

Read the sheet and confirm:

- The first frame already shows the action, and loudness reaches about -20 dB or higher within the first 0.5 s (when the product has a sound).
- Every caption is fully on screen, not covering the thing it describes, and matches what the shot shows.
- Cut times match the plan, and no stretch is silent by accident.
- The end card title does not collide with the photo.

Fix the settings and render again. One or two rounds is normal.

### 6. Hand over

Send the video file. Then report, briefly:

- A table of what you learned from the reference ads, if any were given.
- A table of the shot list: time, shot, on screen text.
- What you left out and why (unconfirmed claims, clips with voices).
- That you cannot hear audio, so they should listen once before posting.
- Anything that would make it stronger and needs new footage, for example a person using the product.

**Privacy**: raw footage usually shows the user's home. Do not commit or push footage or the rendered video to a public repository unless they ask. Keeping the settings file is fine.

## Files in this skill

| File | Purpose |
|---|---|
| `scripts/study_footage.py` | Contact sheets, cut times, loudness, transcripts for any video |
| `scripts/build_ad.py` | Renders the ad from a settings file |
| `references/config.md` | Every settings field, with safe zone numbers |
| `assets/example_dino_scooter.json` | Complete worked example |
| `assets/fonts/` | Inter Display fonts used for captions (open licence) |
