import React, { createContext, useContext } from "react";
import type { GlobalClock } from "./types";

export const GlobalClockContext = createContext<GlobalClock | null>(null);

export const useGlobalClock = (): GlobalClock => {
  const clock = useContext(GlobalClockContext);
  if (!clock) {
    throw new Error("useGlobalClock must be used within a GlobalClockContext.Provider");
  }
  return clock;
};

export const GlobalClockProvider: React.FC<{
  value: GlobalClock;
  children: React.ReactNode;
}> = ({ value, children }) => {
  return (
    <GlobalClockContext.Provider value={value}>
      {children}
    </GlobalClockContext.Provider>
  );
};
