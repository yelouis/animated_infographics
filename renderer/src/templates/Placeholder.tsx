import React from "react";
import { palette } from "../theme/palette";

export interface PlaceholderProps {
  templateName: string;
}

export const Placeholder: React.FC<PlaceholderProps> = ({ templateName }) => {
  return (
    <div
      style={{
        position: "absolute",
        left: 120,
        top: 360,
        width: 840,
        height: 600,
        backgroundColor: palette.bgRaised,
        borderRadius: 32,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        gap: 24,
        padding: 40,
        boxSizing: "border-box",
      }}
    >
      <div
        style={{
          fontFamily: "Poppins, sans-serif",
          fontWeight: 800,
          fontSize: 64,
          color: palette.ink,
          textAlign: "center",
        }}
      >
        {templateName}
      </div>
      <div
        style={{
          fontFamily: "Inter, sans-serif",
          fontWeight: 600,
          fontSize: 32,
          color: palette.inkMuted,
          letterSpacing: 2,
        }}
      >
        NOT YET IMPLEMENTED
      </div>
    </div>
  );
};
