# Settings file reference

The settings file is JSON. `scripts/build_ad.py` reads it and renders the ad. A complete example is in `assets/example_dino_scooter.json`.

## Contents

1. Top level fields
2. Shots
3. Captions
4. Extra sounds
5. End card
6. Safe zones
7. Common problems

## 1. Top level fields

| Field | Default | Meaning |
|---|---|---|
| `width`, `height` | 1080, 1920 | Output size. All layout numbers below assume 1080x1920 and scale automatically. |
| `fps` | 30 | Frames per second of the output. |
| `accent` | `#FFD928` | Colour of starred caption words, the end card button and the arrow. Yellow matches the TikTok Shop basket. Pick a colour that contrasts with the product. |
| `tag` | none | Small black title tag pinned top left for the whole ad: `{"kicker": "RIDE ON TOY", "title": "Dino Scooter"}`. `kicker` is optional. Leave `tag` out for no tag. |
| `shots` | required | List of shots, in order. |
| `sounds` | none | Extra sound pieces laid over the timeline. |
| `end_card` | none | The final call to action screen. Leave out for no end card. |
| `loudness` | -14 | Target loudness in LUFS. -14 suits TikTok. |

## 2. Shots

Each entry in `shots`:

| Field | Default | Meaning |
|---|---|---|
| `clip` | required | Part of a file name in the footage folder, enough to match exactly one file (for example `IMG_6315`). Can be a video or a photo. |
| `start` | required for video | Second in the source clip where the shot begins. Ignored for photos. |
| `dur` | required | How long the shot lasts in the ad, in seconds. |
| `speed` | 1.0 | 2.5 plays the clip 2.5 times faster. The shot then uses `dur x speed` seconds of source, so check the clip is long enough. |
| `zoom` | `[1.0, 1.0]` | Zoom at the start and end of the shot. `[1.0, 1.12]` is a slow push in. `[1.3, 1.3]` is a fixed tighter crop. Minimum 1.0. Above about 1.5 the picture goes soft. |
| `focus` | `[0.5, 0.5]` | Where the crop and zoom aim, as fractions of the picture: `[0, 0]` is top left, `[1, 1]` bottom right. Use it to keep the subject in frame when zooming or when cropping landscape footage to portrait. |
| `sound` | see below | `"own"` plays the clip's own audio in sync. `"none"` mutes it. Default is `"own"` when `speed` is 1.0 and the file has audio, otherwise `"none"`. |
| `gain` | 0 | Volume change in decibels for the shot's own sound. Quiet sounds such as wheels rolling often need 6 to 8. |
| `caption` | none | Text shown during the shot, see below. |

Footage of any shape is scaled to fill the frame and the overflow is cropped, so landscape clips lose their sides. Use `focus` to choose what survives.

A photo used as a shot should have a `zoom` that changes, for example `[1.0, 1.08]`, so it does not look frozen.

## 3. Captions

`caption` inside a shot:

| Field | Default | Meaning |
|---|---|---|
| `lines` | required | List of one or two lines. Wrap words in stars to give them the accent colour: `"REALLY *ROARS*"`. |
| `style` | `"hook"` for shot 1, `"feature"` after | `"hook"`: 112 px, centred at y 1240, for big claims in capitals. `"feature"`: 84 px, centred at y 1290, for calmer feature lines. |
| `size` | from style | Font size in pixels. |
| `y` | from style | Vertical centre of the caption block. |
| `lead` | 0.05 on shot 1, 0.10 after | Seconds after the cut before the caption pops in. |

A caption that is too wide for the safe zone is shrunk automatically and the script prints a note. Treat that note as a prompt to shorten the wording.

Captions sit in the lower middle of the frame by default. If the subject is there, move the caption with `y` (for example 420 to put it near the top, below the tag).

## 4. Extra sounds

`sounds` is for audio that does not belong to the shot it plays under: a sound bed under a sped up shot, one continuous piece of product music across two shots, or sound under the end card.

| Field | Default | Meaning |
|---|---|---|
| `clip` | required | Source file, same matching rule as shots. |
| `start` | required | Second in the source where the piece begins. |
| `dur` | required | Length in seconds. |
| `at_shot` | | Start when this shot starts. Shots count from 1. |
| `at` | | Alternative to `at_shot`: a time in seconds on the ad timeline, or `"end_card"`. |
| `gain` | 0 | Volume change in decibels. |
| `fade_out` | 0.06 | Fade length at the end in seconds. Use about 1.2 for the last sound so the ad does not end abruptly. |

To run one continuous sound across two shots, set `"sound": "none"` on the shot whose clip it comes from and add one `sounds` entry that spans both. Two separate pieces would leave a small dip at the cut.

## 5. End card

A blurred copy of a photo fills the background, the sharp photo sits in a rounded card with a slow zoom, and the text pops in around it.

| Field | Default | Meaning |
|---|---|---|
| `photo` | required | A photo, or a video clip together with `photo_at` (seconds) to grab one frame. Choose a clean view of the whole product. |
| `dur` | 4.0 | Length in seconds. |
| `title` | none | One or two lines above the photo. Stars give the accent colour: `["*DINO*", "SCOOTER"]`. |
| `features` | none | One short line under the photo, for example `"Roars. Lights up. Plays music."`. Proven or confirmed claims only. |
| `button` | none | Text of the call to action button, for example `"TAP THE YELLOW BASKET"` or `"LINK IN BIO"`. |
| `arrow` | `"down_left"` | `"down_left"` points at the TikTok Shop basket. `"down_right"` or `"none"` for other endings. |
| `focus` | `[0.5, 0.5]` | Which part of a tall photo to keep when it is trimmed to fit the card. |

## 6. Safe zones

TikTok draws its own interface over the video. On a 1080x1920 frame keep text inside:

| Edge | Limit | What sits outside it |
|---|---|---|
| Top | y 190 | Following and For You tabs, search |
| Bottom | y 1500 | Username, caption, sound name, basket link |
| Right | x 920 | Like, comment, share buttons |
| Left | x 60 | Screen edge margin |

The script places captions and the tag inside this box by default. The end card arrow deliberately reaches below y 1500 because it points at the basket.

## 7. Common problems

| Symptom | Cause and fix |
|---|---|
| "matches more than one file" | `clip` is too short. Use more of the file name. |
| "asks for its own sound but that file has no audio" | Remove `"sound": "own"` or use a `sounds` entry from another clip. |
| Shot ends early or freezes | `start + dur x speed` runs past the end of the clip. Shorten `dur` or lower `speed`. |
| Caption hides the subject | Change the caption `y`, or shift the picture with `focus`. |
| Hook feels quiet | Move `start` later so the shot opens where loudness is already near its peak. |
| End card photo looks cut off | Tall photos are trimmed to fit. Use a landscape photo or set end card `focus`. |
