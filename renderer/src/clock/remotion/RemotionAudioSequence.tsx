import React from "react";
import { Audio, Sequence, staticFile } from "remotion";

export interface RemotionAudioCueProps {
  src: string;
  startFrame: number;
  durationInFrames?: number;
  volume: number | ((frame: number) => number);
  loop?: boolean;
}

export const RemotionAudioCue: React.FC<RemotionAudioCueProps> = ({
  src,
  startFrame,
  durationInFrames,
  volume,
  loop = false,
}) => {
  // If src starts with http or is relative, staticFile handles relative bundle assets
  const fileUrl = src.startsWith("/") || src.startsWith("http") ? src : staticFile(src);

  if (loop && durationInFrames) {
    return (
      <Sequence from={startFrame} durationInFrames={durationInFrames} layout="none">
        <Audio
          src={fileUrl}
          volume={volume}
          loop
          loopVolumeCurveBehavior="extend"
        />
      </Sequence>
    );
  }

  if (durationInFrames) {
    return (
      <Sequence from={startFrame} durationInFrames={durationInFrames} layout="none">
        <Audio src={fileUrl} volume={volume} />
      </Sequence>
    );
  }

  return (
    <Sequence from={startFrame} layout="none">
      <Audio src={fileUrl} volume={volume} />
    </Sequence>
  );
};
