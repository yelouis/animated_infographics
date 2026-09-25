import React from "react";
import { palette } from "../theme/palette";

export interface BubbleProps {
  text?: string;
  speaker?: string;
  color?: string;
  textColor?: string;
  tail?: "bottom-left" | "bottom-right" | "left" | "right" | "none";
  style?: React.CSSProperties;
  children?: React.ReactNode;
}

export const Bubble: React.FC<BubbleProps> = ({
  text,
  speaker,
  color = palette.bgRaised,
  textColor = palette.ink,
  tail = "none",
  style,
  children,
}) => {
  return (
    <div
      style={{
        position: "relative",
        backgroundColor: color,
        color: textColor,
        borderRadius: 24,
        padding: "20px 28px",
        boxSizing: "border-box",
        fontFamily: "Inter, sans-serif",
        fontWeight: 500,
        fontSize: 32,
        lineHeight: 1.25,
        maxWidth: "100%",
        ...style,
      }}
    >
      {speaker && (
        <div
          style={{
            fontFamily: "Poppins, sans-serif",
            fontWeight: 700,
            fontSize: 24,
            marginBottom: 6,
            color: textColor === palette.ink ? palette.inkMuted : textColor,
          }}
        >
          {speaker}
        </div>
      )}
      {text && <div>{text}</div>}
      {children}
      {tail === "bottom-left" && (
        <div
          style={{
            position: "absolute",
            bottom: -12,
            left: 36,
            width: 0,
            height: 0,
            borderLeft: "12px solid transparent",
            borderRight: "12px solid transparent",
            borderTop: `14px solid ${color}`,
          }}
        />
      )}
      {tail === "bottom-right" && (
        <div
          style={{
            position: "absolute",
            bottom: -12,
            right: 36,
            width: 0,
            height: 0,
            borderLeft: "12px solid transparent",
            borderRight: "12px solid transparent",
            borderTop: `14px solid ${color}`,
          }}
        />
      )}
      {tail === "left" && (
        <div
          style={{
            position: "absolute",
            top: 24,
            left: -12,
            width: 0,
            height: 0,
            borderTop: "12px solid transparent",
            borderBottom: "12px solid transparent",
            borderRight: `14px solid ${color}`,
          }}
        />
      )}
      {tail === "right" && (
        <div
          style={{
            position: "absolute",
            top: 24,
            right: -12,
            width: 0,
            height: 0,
            borderTop: "12px solid transparent",
            borderBottom: "12px solid transparent",
            borderLeft: `14px solid ${color}`,
          }}
        />
      )}
    </div>
  );
};
