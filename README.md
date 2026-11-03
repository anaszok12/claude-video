# Mall vlog, Vox style Remotion edit

A 9:16 (1080 x 1920, 30fps) edit of a Malay family vlog. The look is borrowed from the "sample style" video: paper texture, big serif numerals, yellow halftone discs, highlighter swipes, blurred slide transitions, and word by word captions. Everything is built with Remotion (React) and rendered to MP4.

## Folder map

| Path | What it is |
| --- | --- |
| `src/config.ts` | **The file you edit.** Text, timings, safe zone numbers, sound cue list. |
| `src/Vlog.tsx` | The main video. Decides what appears when. |
| `src/graphics.tsx` | Reusable pieces: cards, numerals, captions, title and end sheets. |
| `src/fonts.ts` | Loads the fonts from `public/fonts`. |
| `scripts/make_assets.py` | Generates the paper texture and all sound effects (no downloads). |
| `public/sfx/` | The generated sound effects. |
| `public/media/raw.mp4` | The footage (30fps copy of the raw clip). Not committed, see below. |

## Safe zones (TikTok and Instagram Reels)

Text and key content stay inside x 60 to 940 and y 250 to 1470.

- top 250 px: search bar, tabs, Reels camera
- bottom 450 px: username, caption, music bar
- right 140 px: like, comment, share buttons

To see the zones painted red, run the studio and set `showGuides` to `true`, or render a still:

```
npx remotion still src/index.ts Vlog out/guides.png --frame=800 --props='{"showGuides":true}'
```

## Commands

```
npm install
python3 scripts/make_assets.py     # only if you change the paper or sounds (needs numpy and pillow)
npm run studio                     # live preview in the browser
npm run render                     # writes out/vlog.mp4
```

## Footage

`public/media/raw.mp4` is large, so it is git ignored. Make it from the original `.mov`:

```
ffmpeg -i 10242026_113836.mov -vf fps=30 -c:v libx264 -crf 21 -pix_fmt yuv420p -c:a aac -b:a 160k public/media/raw.mp4
```

## Things to check by ear

- Captions and counting times come from a speech model on noisy audio, so they are estimates. Edit `COUNT` and `CAPTIONS` in `src/config.ts`.
- Chapter titles ("Mall kosong", "Kira sampai 15", "Mana dia?", "Bersambung...") are my wording. Change them in `COPY`.
