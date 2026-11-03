import React from 'react';
import { Composition } from 'remotion';
import { Vlog, VlogProps } from './Vlog';
import { DURATION_FRAMES, FPS, HEIGHT, WIDTH } from './config';
import './fonts';

export const Root: React.FC = () => {
  return (
    <Composition
      id="Vlog"
      component={Vlog}
      durationInFrames={DURATION_FRAMES}
      fps={FPS}
      width={WIDTH}
      height={HEIGHT}
      // Set showGuides to true to paint the TikTok and Reels danger zones red.
      defaultProps={{ showGuides: false } satisfies VlogProps}
    />
  );
};
