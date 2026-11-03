// ============================================================================
// config.ts  =  the ONE file you edit to change text, timings, and sounds.
// All times are in SECONDS from the start of the video.
// ============================================================================

export const FPS = 30;
export const WIDTH = 1080;
export const HEIGHT = 1920;
// 42.6 seconds. The raw clip is 42.64 s, so we stop a hair early to be safe.
export const DURATION_FRAMES = 1278;

// ---------------------------------------------------------------------------
// SAFE ZONE (TikTok and Instagram Reels, 1080 x 1920)
// Keep ALL text and important faces inside this box. The app draws its own
// buttons, username and caption outside it.
//   top    250 px : search bar, "Following / For You", Reels camera icon
//   bottom 450 px : username, caption, music bar, progress bar
//   right  140 px : like, comment, share, save buttons
//   left    60 px : edge margin so nothing gets clipped on small phones
// ---------------------------------------------------------------------------
export const SAFE = { top: 250, bottom: 450, left: 60, right: 140 };
export const SAFE_BOX = {
  x0: SAFE.left,
  x1: WIDTH - SAFE.right, // 940
  y0: SAFE.top, // 250
  y1: HEIGHT - SAFE.bottom, // 1470
};

export const COLORS = {
  paper: '#eee9de',
  ink: '#141414',
  yellow: '#ffe11a', // the Vox style highlighter yellow
  pink: '#ff3e9a', // matches the pink dino in the footage
  white: '#ffffff',
};

// ---------------------------------------------------------------------------
// WHERE THINGS COME FROM IN THE RAW VIDEO (pixels, in the 1080 x 1920 frame)
// The raw clip has the face camera burned into the top right corner. We cut
// it out (FACE_CROP) and cut the dino view out separately (POV_CROP), then
// place each one on its own paper card inside the safe zone.
// ---------------------------------------------------------------------------
export const FACE_CROP = { x: 626, y: 29, w: 424, h: 756 };
export const POV_CROP = { x: 0, y: 820, w: 1080, h: 1100 };

// ---------------------------------------------------------------------------
// TEXT. Change the words here. Spelling is yours to check.
// ---------------------------------------------------------------------------
export const COPY = {
  titleKicker: 'MALL KOSONG',
  titleLine1: 'Ada',
  titleLine2: 'zombie?!',
  chapter1: 'Mall kosong',
  chapter2: 'Kira sampai 15',
  slam: 'ZOMBIE!',
  chapter3: 'Mana dia?',
  endLine: 'Bersambung...',
};

// ---------------------------------------------------------------------------
// TIMELINE (seconds)
// ---------------------------------------------------------------------------
export const T = {
  titleExitStart: 2.15, // title paper sheet starts sliding up
  titleExitEnd: 2.7,
  cardsIn: 2.55, // face card and dino card pop in
  ch1: [4.0, 9.7] as [number, number],
  ch2Label: [10.2, 25.6] as [number, number],
  slam: [26.0, 28.4] as [number, number],
  ch3: [29.0, 32.5] as [number, number],
  eye1: [33.95, 35.8] as [number, number],
  question: [36.45, 37.75] as [number, number],
  eye2: [38.7, 40.2] as [number, number],
  endSheet: 40.2,
};

// Kid counting out loud. Times are estimates from the speech model, so nudge
// them if a number feels early or late.
export const COUNT: { n: number; t: number }[] = [
  { n: 7, t: 11.85 },
  { n: 8, t: 13.2 },
  { n: 9, t: 14.4 },
  { n: 10, t: 15.8 },
  { n: 11, t: 17.15 },
  { n: 12, t: 18.55 },
  { n: 13, t: 19.95 },
  { n: 14, t: 21.4 },
  { n: 15, t: 22.9 },
];

// Burned in captions. Each caption is a list of [word, secondWordStarts].
export const CAPTIONS: { words: [string, number][]; end: number }[] = [
  { words: [['Ada', 26.0], ['zombie!', 26.2]], end: 26.85 },
  { words: [['Ada', 26.9], ['zombie!', 27.0]], end: 28.0 },
  { words: [['Ada', 32.9], ['dia!', 33.3], ['Ada', 33.7], ['mata!', 33.95]], end: 34.7 },
  { words: [['Ada', 36.5], ['ke?', 36.8]], end: 37.5 },
  { words: [['Ada', 37.8], ['mana?', 38.0], ['Ada', 38.5], ['mata!', 38.7]], end: 39.7 },
];

// ---------------------------------------------------------------------------
// SOUND EFFECTS. t = when it plays. vol = loudness (0 to 1).
// rate = playback speed (1 is normal, higher makes it higher pitched).
// The sound files live in public/sfx and are made by scripts/make_assets.py.
// The kid's real voice and the ambient sound stay at full volume underneath.
// ---------------------------------------------------------------------------
export type Cue = { t: number; file: string; vol: number; rate?: number };

const countCues: Cue[] = COUNT.map((c, i) => ({
  t: c.t - 0.03,
  file: 'pop.wav',
  vol: 0.5,
  rate: 1 + i * 0.07, // each number a little higher pitched than the last
}));

export const SFX_CUES: Cue[] = [
  // title
  { t: 0.12, file: 'boom.wav', vol: 0.55 },
  { t: 0.7, file: 'marker.wav', vol: 0.35 },
  { t: 2.12, file: 'whoosh.wav', vol: 0.5 },
  { t: 2.3, file: 'paper.wav', vol: 0.4 },
  // cards pop in
  { t: 2.55, file: 'pop.wav', vol: 0.45, rate: 0.9 },
  { t: 2.75, file: 'pop.wav', vol: 0.45, rate: 1.1 },
  // chapter 1
  { t: 4.0, file: 'whoosh_short.wav', vol: 0.4 },
  { t: 4.15, file: 'pop.wav', vol: 0.5 },
  { t: 4.5, file: 'marker.wav', vol: 0.3 },
  { t: 9.6, file: 'whoosh_short.wav', vol: 0.35 },
  // chapter 2
  { t: 10.15, file: 'whoosh_short.wav', vol: 0.4 },
  { t: 10.3, file: 'pop.wav', vol: 0.45, rate: 0.9 },
  { t: 10.6, file: 'marker.wav', vol: 0.3 },
  ...countCues,
  // build up to the reveal, then hit
  { t: 24.4, file: 'riser.wav', vol: 0.5 },
  { t: 25.55, file: 'whoosh_short.wav', vol: 0.3 },
  { t: 26.0, file: 'stamp.wav', vol: 0.85 },
  { t: 26.0, file: 'sting.wav', vol: 0.5 },
  { t: 28.25, file: 'whoosh.wav', vol: 0.45 },
  // chapter 3
  { t: 29.0, file: 'whoosh_short.wav', vol: 0.4 },
  { t: 29.15, file: 'pop.wav', vol: 0.5, rate: 1.1 },
  { t: 29.5, file: 'marker.wav', vol: 0.3 },
  { t: 32.4, file: 'whoosh_short.wav', vol: 0.35 },
  // eye and question
  { t: 33.95, file: 'sparkle.wav', vol: 0.5 },
  { t: 34.0, file: 'pop.wav', vol: 0.4, rate: 1.3 },
  { t: 36.45, file: 'ding.wav', vol: 0.5 },
  { t: 36.45, file: 'pop.wav', vol: 0.4 },
  { t: 38.7, file: 'sparkle.wav', vol: 0.5 },
  { t: 38.75, file: 'pop.wav', vol: 0.4, rate: 1.3 },
  // end card
  { t: 40.15, file: 'whoosh.wav', vol: 0.5 },
  { t: 40.4, file: 'boom.wav', vol: 0.45 },
  { t: 40.9, file: 'marker.wav', vol: 0.35 },
];
