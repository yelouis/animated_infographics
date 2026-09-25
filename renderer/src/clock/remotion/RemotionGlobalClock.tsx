import React from "react";
import { useCurrentFrame, useVideoConfig } from "remotion";
import { GlobalClockContext } from "../GlobalClockContext";
import type { GlobalClock } from "../types";

export const RemotionGlobalClock: React.FC<{ children: React.ReactNode }> = ({
  children,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const clock: GlobalClock = {
    frame,
    fps: (fps as 30) || 30,
  };

  return (
    <GlobalClockContext.Provider value={clock}>
      {children}
    </GlobalClockContext.Provider>
  );
};
