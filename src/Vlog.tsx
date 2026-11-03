// ============================================================================
// Vlog.tsx  =  the main video. Layers are stacked bottom to top:
//   1. Board   : paper, face card, dino card, big numerals, slam text
//                (this layer gets the camera zoom and shake)
//   2. Eye and question mark graphics
//   3. Paper texture overlay (gives everything a printed feel)
//   4. Captions (kept still so they stay inside the safe zone)
//   5. Title sheet and end sheet (full page paper that slides over)
//   6. Flash on the ZOMBIE hit
//   7. Optional red safe zone guides
// Plus audio: the original sound, and the sound effects from config.ts.
// ============================================================================
import React from 'react';
import { AbsoluteFill, Audio, Img, Sequence, interpolate, staticFile, useCurrentFrame } from 'remotion';
import {
  COPY,
  COLORS,
  COUNT,
  FACE_CROP,
  FPS,
  POV_CROP,
  SFX_CUES,
  T,
} from './config';
import {
  BigNumeral,
  Captions,
  ChapterLabel,
  CropVideo,
  EndSheet,
  Eye,
  Newsprint,
  Paper,
  PaperCard,
  QuestionMark,
  SafeGuides,
  SlotItem,
  Slam,
  TitleSheet,
} from './graphics';

export type VlogProps = { showGuides: boolean };

// Where the numeral and label sit (right of the face card, inside the safe zone)
const SLOT = { left: 450, top: 268 };
const LABEL = { left: 462, top: 510 };

// Shows whichever counted number is current. Each number pops when it is "said".
const CountingNumeral: React.FC = () => {
  const frame = useCurrentFrame();
  const t = frame / FPS;
  const current = [...COUNT].reverse().find((c) => t >= c.t - 0.02) ?? COUNT[0];
  return <BigNumeral key={current.n} text={String(current.n)} popAt={current.t} />;
};

export const Vlog: React.FC<VlogProps> = ({ showGuides }) => {
  const frame = useCurrentFrame();
  const t = frame / FPS;

  // ---- camera: slow push in the whole time, plus a punch and shake on ZOMBIE
  const slowZoom = 1 + 0.03 * (t / 42.6);
  const sinceSlam = t - T.slam[0];
  const punch = sinceSlam >= 0 ? Math.exp(-sinceSlam * 8) * 0.085 : 0;
  const shake = sinceSlam >= 0 ? Math.exp(-sinceSlam * 6) * 20 : 0;
  const shakeX = Math.sin(sinceSlam * 80) * shake;
  const shakeY = Math.cos(sinceSlam * 67) * shake * 0.7;

  // white flash right on the hit
  const flash = sinceSlam >= 0 ? Math.max(0, 0.75 - sinceSlam * 6) : 0;

  return (
    <AbsoluteFill style={{ background: COLORS.paper, overflow: 'hidden' }}>
      {/* original sound from the raw clip (the video itself is muted in the cards) */}
      <Audio src={staticFile('media/raw.mp4')} volume={1} />

      {/* sound effects */}
      {SFX_CUES.map((c, i) => (
        <Sequence key={i} from={Math.round(c.t * FPS)} layout="none">
          <Audio src={staticFile(`sfx/${c.file}`)} volume={c.vol} playbackRate={c.rate ?? 1} />
        </Sequence>
      ))}

      {/* 1. BOARD */}
      <AbsoluteFill
        style={{
          transform: `translate(${shakeX}px, ${shakeY}px) scale(${slowZoom + punch})`,
          transformOrigin: '50% 55%',
        }}
      >
        <Paper drift={t * 3} />
        <Newsprint drift={t} />

        {/* dino view card (bigger, sits behind) */}
        <PaperCard left={100} top={610} rotate={1.2} appear={T.cardsIn + 0.2} tapeAt="right">
          <CropVideo crop={POV_CROP} w={812} innerZoom={1.02 + 0.04 * (t / 42.6)} />
        </PaperCard>

        {/* face camera card (smaller, overlaps the dino card) */}
        <PaperCard left={70} top={285} rotate={-3.5} appear={T.cardsIn} tapeAt="left">
          <CropVideo crop={FACE_CROP} w={302} />
        </PaperCard>

        {/* chapter 1 */}
        <div style={{ position: 'absolute', left: SLOT.left, top: SLOT.top }}>
          <SlotItem start={T.ch1[0]} end={T.ch1[1]}>
            <BigNumeral text="1" popAt={T.ch1[0] + 0.15} />
          </SlotItem>
        </div>
        <div style={{ position: 'absolute', left: LABEL.left, top: LABEL.top }}>
          <SlotItem start={T.ch1[0] + 0.1} end={T.ch1[1]}>
            <ChapterLabel text={COPY.chapter1} start={T.ch1[0] + 0.1} />
          </SlotItem>
        </div>

        {/* chapter 2: a "2" first, then the counting numbers take over */}
        <div style={{ position: 'absolute', left: SLOT.left, top: SLOT.top }}>
          <SlotItem start={T.ch2Label[0]} end={COUNT[0].t - 0.1}>
            <BigNumeral text="2" popAt={T.ch2Label[0] + 0.15} />
          </SlotItem>
          <SlotItem start={COUNT[0].t - 0.05} end={T.ch2Label[1]}>
            <CountingNumeral />
          </SlotItem>
        </div>
        <div style={{ position: 'absolute', left: LABEL.left, top: LABEL.top }}>
          <SlotItem start={T.ch2Label[0] + 0.1} end={T.ch2Label[1]}>
            <ChapterLabel text={COPY.chapter2} start={T.ch2Label[0] + 0.1} />
          </SlotItem>
        </div>

        {/* chapter 3 */}
        <div style={{ position: 'absolute', left: SLOT.left, top: SLOT.top }}>
          <SlotItem start={T.ch3[0]} end={T.ch3[1]}>
            <BigNumeral text="3" popAt={T.ch3[0] + 0.15} />
          </SlotItem>
        </div>
        <div style={{ position: 'absolute', left: LABEL.left, top: LABEL.top }}>
          <SlotItem start={T.ch3[0] + 0.1} end={T.ch3[1]}>
            <ChapterLabel text={COPY.chapter3} start={T.ch3[0] + 0.1} />
          </SlotItem>
        </div>

        {/* ZOMBIE! slam */}
        <Slam text={COPY.slam} />
      </AbsoluteFill>

      {/* 2. eye and question mark (sit in the same slot, so no camera shake needed) */}
      <Eye start={T.eye1[0]} end={T.eye1[1]} />
      <QuestionMark start={T.question[0]} end={T.question[1]} />
      <Eye start={T.eye2[0]} end={T.eye2[1]} />

      {/* 3. paper texture over everything below the captions */}
      <AbsoluteFill style={{ mixBlendMode: 'multiply', opacity: 0.22, pointerEvents: 'none' }}>
        <Img src={staticFile('paper.png')} style={{ width: '100%', height: '100%' }} />
      </AbsoluteFill>

      {/* 4. captions */}
      <Captions />

      {/* 5. full page sheets */}
      <TitleSheet kicker={COPY.titleKicker} l1={COPY.titleLine1} l2={COPY.titleLine2} />
      <EndSheet line={COPY.endLine} />

      {/* 6. flash */}
      {flash > 0 && (
        <AbsoluteFill style={{ background: '#fff', opacity: interpolate(flash, [0, 0.75], [0, 0.75]) }} />
      )}

      {/* 7. guides */}
      {showGuides && <SafeGuides />}
    </AbsoluteFill>
  );
};
