// Loads the three font files from public/fonts so text looks the same on any
// computer. "delayRender" tells Remotion to wait until fonts are ready before
// it takes a picture of each frame.
import { continueRender, delayRender, staticFile } from 'remotion';

export const SERIF = '"Playfair Display", serif'; // big headlines and numerals
export const SANS = '"Montserrat", sans-serif'; // captions and small labels

const files: [string, string, string, string][] = [
  ['Playfair Display', 'fonts/playfair-display-latin-900-normal.woff2', '900', 'normal'],
  ['Playfair Display', 'fonts/playfair-display-latin-900-italic.woff2', '900', 'italic'],
  ['Montserrat', 'fonts/montserrat-latin-800-normal.woff2', '800', 'normal'],
];

const handle = delayRender('Loading fonts');

Promise.all(
  files.map(([family, file, weight, style]) =>
    new FontFace(family, `url(${staticFile(file)})`, { weight, style })
      .load()
      .then((face) => document.fonts.add(face)),
  ),
)
  .then(() => continueRender(handle))
  .catch((err) => {
    console.error('Font load failed', err);
    continueRender(handle);
  });
