import React, { createContext, useContext } from "react";
import type { SceneClock } from "./types";

export const SceneClockContext = createContext<SceneClock | null>(null);

export const useSceneClock = (): SceneClock => {
  const clock = useContext(SceneClockContext);
  if (!clock) {
    throw new Error("useSceneClock must be used within a SceneClockContext.Provider");
  }
  return clock;
};

export const SceneClockProvider: React.FC<{
  value: SceneClock;
  children: React.ReactNode;
}> = ({ value, children }) => {
  return (
    <SceneClockContext.Provider value={value}>
      {children}
    </SceneClockContext.Provider>
  );
};
