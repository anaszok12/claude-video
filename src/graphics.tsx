// ============================================================================
// graphics.tsx  =  small reusable building blocks (cards, numerals, captions...)
// Think of these as stickers. Vlog.tsx decides WHEN and WHERE to stick them.
// ============================================================================
import React from 'react';
import {
  Easing,
  Img,
  OffthreadVideo,
  interpolate,
  spring,
  staticFile,
  useCurrentFrame,
} from 'remotion';
import { CAPTIONS, COLORS, FPS, HEIGHT, SAFE_BOX, T, WIDTH } from './config';
import { SANS, SERIF } from './fonts';

// ---------------------------------------------------------------- helpers
// Two easing curves: "ease" starts fast and settles (good for things arriving),
// "easeIn" starts slow and speeds up (good for things leaving).
export const ease = Easing.bezier(0.2, 0.8, 0.2, 1);
export const easeIn = Easing.bezier(0.6, 0, 0.9, 0.4);
const clamp = { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' } as const;

// A springy 0 to 1 animation that starts at `startSec`. Overshoots a little,
// which is what gives the "pop".
export const springAt = (
  frame: number,
  startSec: number,
  config: { damping?: number; stiffness?: number; mass?: number } = {},
) =>
  spring({
    frame: Math.max(0, frame - startSec * FPS),
    fps: FPS,
    config: { damping: 13, stiffness: 150, mass: 0.7, ...config },
  });

// ---------------------------------------------------------------- paper
export const Paper: React.FC<{ drift?: number }> = ({ drift = 0 }) => (
  <div style={{ position: 'absolute', inset: 0, background: COLORS.paper, overflow: 'hidden' }}>
    <Img
      src={staticFile('paper.png')}
      style={{
        position: 'absolute',
        left: -20,
        top: -20,
        width: WIDTH + 40,
        height: HEIGHT + 40,
        transform: `translate(${drift}px, ${drift * 0.6}px)`,
      }}
    />
  </div>
);

// Yellow circle with a halftone dot fade, the Vox look.
export const Disc: React.FC<{ size: number }> = ({ size }) => (
  <div
    style={{
      width: size,
      height: size,
      borderRadius: '50%',
      background: COLORS.yellow,
      position: 'relative',
      overflow: 'hidden',
    }}
  >
    <div
      style={{
        position: 'absolute',
        inset: 0,
        backgroundImage: 'radial-gradient(circle, rgba(20,20,20,0.38) 1.7px, transparent 2.4px)',
        backgroundSize: '11px 11px',
        WebkitMaskImage: 'linear-gradient(135deg, transparent 25%, black 100%)',
      }}
    />
  </div>
);

// Big faded headline text behind everything, like the blurred newspaper in the
// sample. It only lives in the top and bottom bands that TikTok and Reels cover
// with their own buttons, so it never hides anything important.
export const Newsprint: React.FC<{ drift: number }> = ({ drift }) => (
  <div style={{ position: 'absolute', inset: 0, overflow: 'hidden', opacity: 0.1, filter: 'blur(1.3px)' }}>
    {[
      { top: 10, size: 150, x: -80, text: 'Ada zombie? Ada zombie? Ada' },
      { top: 1495, size: 170, x: -150, text: 'Ada mata! Ada mata! Ada' },
      { top: 1690, size: 150, x: -40, text: 'Mall kosong. Mall kosong.' },
    ].map((l, i) => (
      <div
        key={i}
        style={{
          position: 'absolute',
          top: l.top,
          left: l.x + drift * (i % 2 ? -6 : 6),
          fontFamily: SERIF,
          fontStyle: i === 1 ? 'normal' : 'italic',
          fontWeight: 900,
          fontSize: l.size,
          color: COLORS.ink,
          whiteSpace: 'nowrap',
          transform: 'rotate(-3deg)',
        }}
      >
        {l.text}
      </div>
    ))}
  </div>
);

// ---------------------------------------------------------------- highlighter
// Draws a yellow marker swipe behind its text, left to right.
export const Marker: React.FC<{
  start: number;
  children: React.ReactNode;
  color?: string;
  duration?: number;
}> = ({ start, children, color = COLORS.yellow, duration = 0.35 }) => {
  const frame = useCurrentFrame();
  const p = interpolate(frame / FPS, [start, start + duration], [0, 1], {
    ...clamp,
    easing: ease,
  });
  return (
    <span style={{ position: 'relative', display: 'inline-block', whiteSpace: 'nowrap' }}>
      <span
        style={{
          position: 'absolute',
          left: -14,
          right: -14,
          bottom: '4%',
          height: '50%',
          background: color,
          transformOrigin: 'left center',
          transform: `scaleX(${p}) rotate(-1deg)`,
          mixBlendMode: 'multiply',
          borderRadius: 6,
        }}
      />
      <span style={{ position: 'relative' }}>{children}</span>
    </span>
  );
};

// ---------------------------------------------------------------- slide wrapper
// Shows its children between `start` and `end` seconds. It slides in from the
// right with a blur, and slides out to the left with a blur (the blur is the
// "motion blur" feel from the sample video).
export const SlotItem: React.FC<{
  start: number;
  end: number;
  children: React.ReactNode;
}> = ({ start, end, children }) => {
  const frame = useCurrentFrame();
  const t = frame / FPS;
  if (t < start - 0.01 || t > end + 0.5) return null;
  const enter = springAt(frame, start, { damping: 16, stiffness: 120 });
  const exit = interpolate(t, [end, end + 0.4], [0, 1], { ...clamp, easing: easeIn });
  const x = (1 - enter) * 140 - exit * 170;
  const blur = Math.max(0, (1 - Math.min(enter, 1)) * 14 + exit * 18);
  const opacity = Math.min(1, enter * 1.6) * (1 - exit);
  return (
    <div style={{ transform: `translateX(${x}px)`, filter: `blur(${blur}px)`, opacity }}>
      {children}
    </div>
  );
};

// ---------------------------------------------------------------- cards
// Cuts one rectangle out of the raw video. The raw file is 1080 x 1920; we
// scale it so the chosen rectangle fits `w` pixels wide and slide the video so
// only that rectangle shows.
export const CropVideo: React.FC<{
  crop: { x: number; y: number; w: number; h: number };
  w: number;
  innerZoom?: number;
}> = ({ crop, w, innerZoom = 1 }) => {
  const s = w / crop.w;
  const h = crop.h * s;
  return (
    <div style={{ width: w, height: h, overflow: 'hidden', position: 'relative', background: '#000' }}>
      <div
        style={{
          position: 'absolute',
          left: 0,
          top: 0,
          width: w,
          height: h,
          transform: `scale(${innerZoom})`,
          transformOrigin: 'center',
        }}
      >
        <OffthreadVideo
          src={staticFile('media/raw.mp4')}
          muted
          style={{
            position: 'absolute',
            width: 1080 * s,
            height: 1920 * s,
            left: -crop.x * s,
            top: -crop.y * s,
            maxWidth: 'none',
          }}
        />
      </div>
    </div>
  );
};

// A white bordered paper card with a shadow and a piece of tape. Pops in with
// a spring at `appear` seconds, then wobbles very slightly so it feels alive.
export const PaperCard: React.FC<{
  left: number;
  top: number;
  rotate: number;
  appear: number;
  tapeAt: 'left' | 'right';
  children: React.ReactNode;
}> = ({ left, top, rotate, appear, tapeAt, children }) => {
  const frame = useCurrentFrame();
  const t = frame / FPS;
  const p = springAt(frame, appear, { damping: 12, stiffness: 130, mass: 0.8 });
  const wobble = Math.sin(t * 0.9 + left) * 0.35;
  const scale = 0.55 + 0.45 * p;
  const dy = (1 - Math.min(p, 1)) * 140;
  return (
    <div
      style={{
        position: 'absolute',
        left,
        top,
        transform: `translateY(${dy}px) rotate(${rotate + wobble + (1 - p) * -6}deg) scale(${scale})`,
        opacity: Math.min(1, p * 3),
        background: '#fbfaf6',
        padding: 14,
        boxShadow: '0 30px 50px rgba(0,0,0,0.38), 0 4px 10px rgba(0,0,0,0.25)',
      }}
    >
      {children}
      <div
        style={{
          position: 'absolute',
          top: -22,
          [tapeAt]: 28,
          width: 150,
          height: 44,
          background: 'rgba(255, 225, 26, 0.62)',
          transform: `rotate(${tapeAt === 'left' ? -28 : 24}deg)`,
          boxShadow: '0 2px 4px rgba(0,0,0,0.2)',
        }}
      />
    </div>
  );
};

// ---------------------------------------------------------------- numerals
// Big serif number on a halftone yellow disc (like the "1" and "2" in the sample).
export const BigNumeral: React.FC<{ text: string; size?: number; popAt?: number }> = ({
  text,
  size = 280,
  popAt,
}) => {
  const frame = useCurrentFrame();
  const p = popAt === undefined ? 1 : springAt(frame, popAt, { damping: 10, stiffness: 260, mass: 0.5 });
  return (
    <div style={{ position: 'relative', width: 490, height: 250 }}>
      <div style={{ position: 'absolute', left: 20, top: 0, transform: `scale(${0.4 + 0.6 * p})` }}>
        <Disc size={240} />
      </div>
      <div
        style={{
          position: 'absolute',
          left: 60,
          top: -34,
          fontFamily: SERIF,
          fontWeight: 900,
          fontSize: size,
          lineHeight: 1,
          color: COLORS.ink,
          transform: `scale(${0.5 + 0.5 * p})`,
          transformOrigin: '30% 60%',
        }}
      >
        {text}
      </div>
    </div>
  );
};

export const ChapterLabel: React.FC<{ text: string; start: number }> = ({ text, start }) => (
  <div
    style={{
      fontFamily: SERIF,
      fontWeight: 900,
      fontSize: 60,
      lineHeight: 1.1,
      color: COLORS.ink,
      whiteSpace: 'nowrap',
    }}
  >
    <Marker start={start + 0.25}>{text}</Marker>
  </div>
);

// ---------------------------------------------------------------- slam
// The big ZOMBIE! stamp. Flies in huge, lands with a bounce.
export const Slam: React.FC<{ text: string }> = ({ text }) => {
  const frame = useCurrentFrame();
  const t = frame / FPS;
  const [a, b] = T.slam;
  if (t < a - 0.02 || t > b + 0.5) return null;
  const exit = interpolate(t, [b, b + 0.4], [0, 1], { ...clamp, easing: easeIn });
  // fly in from 3x size down to 1x in 0.12 s, then a tiny settle bounce
  const fly = interpolate(t, [a, a + 0.12], [3, 1], { ...clamp, easing: Easing.out(Easing.cubic) });
  const settle = t > a + 0.12 ? 0.05 * Math.exp(-(t - a - 0.12) * 14) * Math.cos((t - a - 0.12) * 40) : 0;
  const scale = fly + settle;
  return (
    <div
      style={{
        position: 'absolute',
        left: SAFE_BOX.x0,
        width: SAFE_BOX.x1 - SAFE_BOX.x0,
        top: 770,
        display: 'flex',
        justifyContent: 'center',
        transform: `translateX(${-exit * 900}px) rotate(-5deg) scale(${scale})`,
        filter: `blur(${exit * 22}px)`,
        opacity: Math.min(1, (t - a) / 0.04) * (1 - exit),
      }}
    >
      <div
        style={{
          fontFamily: SERIF,
          fontStyle: 'italic',
          fontWeight: 900,
          fontSize: 160,
          lineHeight: 1.05,
          color: COLORS.ink,
          background: COLORS.yellow,
          padding: '6px 34px 14px',
          boxShadow: `14px 14px 0 ${COLORS.pink}`,
          whiteSpace: 'nowrap',
        }}
      >
        {text}
      </div>
    </div>
  );
};

// ---------------------------------------------------------------- eye + question mark
export const Eye: React.FC<{ start: number; end: number }> = ({ start, end }) => {
  const frame = useCurrentFrame();
  const t = frame / FPS;
  if (t < start - 0.01 || t > end + 0.4) return null;
  const p = springAt(frame, start, { damping: 9, stiffness: 220, mass: 0.6 });
  const exit = interpolate(t, [end, end + 0.3], [0, 1], { ...clamp, easing: easeIn });
  // pupil darts left and right
  const look = Math.sin((t - start) * 7) * 16;
  // a quick blink right after it appears
  const blink = interpolate((t - start) % 1.4, [0.9, 1.0, 1.1], [1, 0.08, 1], clamp);
  return (
    <div
      style={{
        position: 'absolute',
        left: 520,
        top: 290,
        width: 380,
        height: 240,
        transform: `rotate(${(1 - p) * 20 - 4}deg) scale(${p * (1 - exit)})`,
        opacity: 1 - exit,
      }}
    >
      <div style={{ position: 'absolute', left: 40, top: 0 }}>
        <Disc size={220} />
      </div>
      <svg viewBox="0 0 200 130" width={380} height={247} style={{ position: 'absolute', left: 0, top: -4 }}>
        <defs>
          <clipPath id="eyeClip">
            <path d="M8 65 Q100 -22 192 65 Q100 152 8 65Z" />
          </clipPath>
        </defs>
        <path d="M8 65 Q100 -22 192 65 Q100 152 8 65Z" fill="#fff" stroke={COLORS.ink} strokeWidth={7} />
        <g clipPath="url(#eyeClip)">
          <g transform={`translate(${look * 0.5} 0) translate(0 ${65 * (1 - blink)}) scale(1 ${blink})`}>
            <circle cx={100} cy={65} r={38} fill={COLORS.pink} stroke={COLORS.ink} strokeWidth={5} />
            <circle cx={100} cy={65} r={16} fill={COLORS.ink} />
            <circle cx={90} cy={54} r={7} fill="#fff" />
          </g>
        </g>
        {[-1, 0, 1].map((i) => (
          <line
            key={i}
            x1={100 + i * 42}
            y1={14 + Math.abs(i) * 12}
            x2={100 + i * 56}
            y2={-4 + Math.abs(i) * 14}
            stroke={COLORS.ink}
            strokeWidth={6}
            strokeLinecap="round"
          />
        ))}
      </svg>
    </div>
  );
};

export const QuestionMark: React.FC<{ start: number; end: number }> = ({ start, end }) => (
  <SlotItem start={start} end={end}>
    <div style={{ position: 'absolute', left: 560, top: 270 }}>
      <div style={{ position: 'absolute', left: 20, top: 10 }}>
        <Disc size={220} />
      </div>
      <div
        style={{
          position: 'relative',
          fontFamily: SERIF,
          fontStyle: 'italic',
          fontWeight: 900,
          fontSize: 330,
          lineHeight: 1,
          color: COLORS.ink,
          paddingLeft: 60,
          marginTop: -30,
        }}
      >
        ?
      </div>
    </div>
  </SlotItem>
);

// ---------------------------------------------------------------- captions
// Words appear as they are spoken. The word being spoken right now is yellow.
// Pinned so the BOTTOM of the text sits at y = 1440 (30 px above the unsafe
// bottom zone) and grows upward if it wraps to two lines.
export const Captions: React.FC = () => {
  const frame = useCurrentFrame();
  const t = frame / FPS;
  const cap = CAPTIONS.find((c) => t >= c.words[0][1] - 0.05 && t <= c.end);
  if (!cap) return null;
  const p = springAt(frame, cap.words[0][1] - 0.05, { damping: 14, stiffness: 220, mass: 0.5 });
  return (
    <div
      style={{
        position: 'absolute',
        left: SAFE_BOX.x0,
        width: SAFE_BOX.x1 - SAFE_BOX.x0,
        bottom: HEIGHT - 1440,
        display: 'flex',
        justifyContent: 'center',
        flexWrap: 'wrap',
        gap: '0 36px',
        transform: `scale(${0.86 + 0.14 * Math.min(p, 1.1)})`,
        transformOrigin: 'center bottom',
        opacity: Math.min(1, p * 2),
      }}
    >
      {cap.words.map(([word, ws], i) => {
        const spoken = t >= ws;
        const next = cap.words[i + 1];
        const active = spoken && (!next || t < next[1]);
        const wp = springAt(frame, ws, { damping: 12, stiffness: 300, mass: 0.4 });
        return (
          <span
            key={i}
            style={{
              fontFamily: SANS,
              fontWeight: 800,
              fontSize: 76,
              lineHeight: 1.18,
              color: active ? COLORS.yellow : COLORS.white,
              WebkitTextStroke: '13px #141414',
              paintOrder: 'stroke fill',
              textShadow: '0 7px 0 rgba(0,0,0,0.35)',
              opacity: spoken ? 1 : 0,
              transform: `scale(${active ? 1 + 0.12 * Math.min(wp, 1.2) : 1})`,
              display: 'inline-block',
            }}
          >
            {word}
          </span>
        );
      })}
    </div>
  );
};

// ---------------------------------------------------------------- full page sheets
export const TitleSheet: React.FC<{ kicker: string; l1: string; l2: string }> = ({
  kicker,
  l1,
  l2,
}) => {
  const frame = useCurrentFrame();
  const t = frame / FPS;
  if (t > T.titleExitEnd + 0.1) return null;
  const out = interpolate(t, [T.titleExitStart, T.titleExitEnd], [0, 1], {
    ...clamp,
    easing: Easing.bezier(0.7, 0, 0.3, 1),
  });
  const pDisc = springAt(frame, 0.05, { damping: 14, stiffness: 90 });
  const p1 = springAt(frame, 0.12, { damping: 11, stiffness: 140 });
  const p2 = springAt(frame, 0.3, { damping: 11, stiffness: 140 });
  const kick = interpolate(t, [0.2, 0.6], [0, 1], { ...clamp, easing: ease });
  return (
    <div
      style={{
        position: 'absolute',
        inset: 0,
        transform: `translateY(${-out * (HEIGHT + 80)}px)`,
        filter: `blur(${out * 10}px)`,
        boxShadow: '0 40px 60px rgba(0,0,0,0.4)',
      }}
    >
      <Paper />
      <div
        style={{
          position: 'absolute',
          left: 80,
          top: 470,
          transform: `scale(${0.3 + 0.7 * pDisc})`,
        }}
      >
        <Disc size={620} />
      </div>
      <div
        style={{
          position: 'absolute',
          left: SAFE_BOX.x0,
          width: SAFE_BOX.x1 - SAFE_BOX.x0,
          top: 600,
          textAlign: 'left',
          color: COLORS.ink,
        }}
      >
        <div
          style={{
            fontFamily: SANS,
            fontWeight: 800,
            fontSize: 40,
            letterSpacing: '0.28em',
            opacity: kick,
            transform: `translateX(${(1 - kick) * -40}px)`,
            marginBottom: 6,
          }}
        >
          {kicker}
        </div>
        <div
          style={{
            fontFamily: SERIF,
            fontWeight: 900,
            fontSize: 330,
            lineHeight: 0.95,
            transform: `translateY(${(1 - Math.min(p1, 1)) * 120}px) scale(${0.8 + 0.2 * p1})`,
            transformOrigin: 'left bottom',
            opacity: Math.min(1, p1 * 2),
          }}
        >
          {l1}
        </div>
        <div
          style={{
            fontFamily: SERIF,
            fontStyle: 'italic',
            fontWeight: 900,
            fontSize: 232,
            lineHeight: 1,
            transform: `translateY(${(1 - Math.min(p2, 1)) * 120}px) scale(${0.8 + 0.2 * p2})`,
            transformOrigin: 'left bottom',
            opacity: Math.min(1, p2 * 2),
          }}
        >
          <Marker start={0.65} color={COLORS.pink} duration={0.4}>
            {l2}
          </Marker>
        </div>
      </div>
    </div>
  );
};

export const EndSheet: React.FC<{ line: string }> = ({ line }) => {
  const frame = useCurrentFrame();
  const t = frame / FPS;
  if (t < T.endSheet - 0.05) return null;
  const inP = interpolate(t, [T.endSheet, T.endSheet + 0.45], [1, 0], {
    ...clamp,
    easing: Easing.bezier(0.7, 0, 0.3, 1),
  });
  const pText = springAt(frame, T.endSheet + 0.3, { damping: 11, stiffness: 130 });
  return (
    <div
      style={{
        position: 'absolute',
        inset: 0,
        transform: `translateY(${inP * (HEIGHT + 80)}px)`,
        filter: `blur(${inP * 10}px)`,
        boxShadow: '0 -40px 60px rgba(0,0,0,0.4)',
      }}
    >
      <Paper />
      <div style={{ position: 'absolute', left: 240, top: 590, transform: `scale(${0.3 + 0.7 * Math.min(pText, 1)})` }}>
        <Disc size={520} />
      </div>
      <div
        style={{
          position: 'absolute',
          left: SAFE_BOX.x0,
          width: SAFE_BOX.x1 - SAFE_BOX.x0,
          top: 800,
          textAlign: 'center',
          fontFamily: SERIF,
          fontStyle: 'italic',
          fontWeight: 900,
          fontSize: 118,
          lineHeight: 1.1,
          color: COLORS.ink,
          opacity: Math.min(1, pText * 2),
          transform: `translateY(${(1 - Math.min(pText, 1)) * 90}px)`,
          whiteSpace: 'nowrap',
        }}
      >
        <Marker start={T.endSheet + 0.7} color={COLORS.pink} duration={0.45}>
          {line}
        </Marker>
      </div>
    </div>
  );
};

// ---------------------------------------------------------------- debug overlay
// Paints the TikTok and Reels danger zones red so you can check the layout.
export const SafeGuides: React.FC = () => (
  <div style={{ position: 'absolute', inset: 0, pointerEvents: 'none' }}>
    {[
      { left: 0, top: 0, width: WIDTH, height: SAFE_BOX.y0 },
      { left: 0, top: SAFE_BOX.y1, width: WIDTH, height: HEIGHT - SAFE_BOX.y1 },
      { left: 0, top: SAFE_BOX.y0, width: SAFE_BOX.x0, height: SAFE_BOX.y1 - SAFE_BOX.y0 },
      { left: SAFE_BOX.x1, top: SAFE_BOX.y0, width: WIDTH - SAFE_BOX.x1, height: SAFE_BOX.y1 - SAFE_BOX.y0 },
    ].map((r, i) => (
      <div key={i} style={{ position: 'absolute', ...r, background: 'rgba(255,0,0,0.28)' }} />
    ))}
    <div
      style={{
        position: 'absolute',
        left: SAFE_BOX.x0,
        top: SAFE_BOX.y0,
        width: SAFE_BOX.x1 - SAFE_BOX.x0,
        height: SAFE_BOX.y1 - SAFE_BOX.y0,
        border: '3px dashed #00e676',
      }}
    />
  </div>
);
