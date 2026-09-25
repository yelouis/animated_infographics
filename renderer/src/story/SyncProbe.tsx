import React from "react";

export interface SyncProbeProps {
  sceneIndex: number;
}

export const SyncProbe: React.FC<SyncProbeProps> = ({ sceneIndex }) => {
  const isEven = sceneIndex % 2 === 0;

  return (
    <div
      style={{
        position: "absolute",
        top: 0,
        left: 0,
        width: 48,
        height: 48,
        backgroundColor: isEven ? "#000000" : "#FFFFFF",
        zIndex: 99999,
        pointerEvents: "none",
      }}
    />
  );
};
