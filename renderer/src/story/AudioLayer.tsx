import React from "react";
import { RemotionAudioCue } from "../clock/remotion/RemotionAudioSequence";
import type { TimelineAudio } from "../generated/contracts";

export interface AudioLayerProps {
  audio: TimelineAudio;
  durationFrames: number;
}

export const AudioLayer: React.FC<AudioLayerProps> = ({
  audio,
  durationFrames,
}) => {
  const baseMusicVolume = audio.music?.volume ?? 0.126;

  const musicVolumeCallback = (frame: number): number => {
    if (frame < 30) {
      return Math.max(0.001, (frame / 30) * baseMusicVolume);
    }
    if (frame >= durationFrames - 60) {
      return Math.max(0.001, ((durationFrames - frame) / 60) * baseMusicVolume);
    }
    return baseMusicVolume;
  };

  return (
    <>
      {/* 1. Narration */}
      {audio.narration?.src && (
        <RemotionAudioCue
          src={audio.narration.src}
          startFrame={0}
          volume={1.0}
        />
      )}

      {/* 2. Music */}
      {audio.music && audio.music.src && (
        <RemotionAudioCue
          src={audio.music.src}
          startFrame={0}
          durationInFrames={durationFrames}
          volume={musicVolumeCallback}
          loop
        />
      )}

      {/* 3. SFX Cues */}
      {audio.sfx &&
        audio.sfx.map((cue, idx) => (
          <RemotionAudioCue
            key={`sfx-${idx}-${cue.src}-${cue.frame}`}
            src={cue.src}
            startFrame={cue.frame}
            volume={cue.volume ?? 0.35}
          />
        ))}
    </>
  );
};
