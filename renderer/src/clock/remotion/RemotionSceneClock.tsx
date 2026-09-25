import React from "react";
import { Sequence, useCurrentFrame, useVideoConfig } from "remotion";
import { ENTER_FRAMES, EXIT_FRAMES } from "../../theme/motion";
import { SceneClockContext } from "../SceneClockContext";
import type { SceneClock } from "../types";

interface SceneClockInnerProps {
  sceneFrames: number;
  children: React.ReactNode;
}

const SceneClockInner: React.FC<SceneClockInnerProps> = ({
  sceneFrames,
  children,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  let phase: "enter" | "hold" | "exit";
  if (frame < ENTER_FRAMES) {
    phase = "enter";
  } else if (frame >= sceneFrames) {
    phase = "exit";
  } else {
    phase = "hold";
  }

  const enterProgress = Math.min(1, Math.max(0, frame / ENTER_FRAMES));
  const exitProgress =
    frame >= sceneFrames
      ? Math.min(1, Math.max(0, (frame - sceneFrames) / EXIT_FRAMES))
      : 0;

  const clock: SceneClock = {
    frame,
    fps: (fps as 30) || 30,
    sceneFrames,
    phase,
    enterProgress,
    exitProgress,
  };

  return (
    <SceneClockContext.Provider value={clock}>
      {children}
    </SceneClockContext.Provider>
  );
};

export interface RemotionSceneClockProps {
  startFrame: number;
  durationFrames: number;
  sceneFrames: number;
  children: React.ReactNode;
}

export const RemotionSceneClock: React.FC<RemotionSceneClockProps> = ({
  startFrame,
  durationFrames,
  sceneFrames,
  children,
}) => {
  return (
    <Sequence from={startFrame} durationInFrames={durationFrames} layout="none">
      <SceneClockInner sceneFrames={sceneFrames}>{children}</SceneClockInner>
    </Sequence>
  );
};
