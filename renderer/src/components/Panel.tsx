import React from "react";
import { palette } from "../theme/palette";

export interface PanelProps {
  children?: React.ReactNode;
  radius?: number;
  color?: string;
  padding?: number | string;
  width?: number | string;
  height?: number | string;
  style?: React.CSSProperties;
  className?: string;
}

export const Panel: React.FC<PanelProps> = ({
  children,
  radius = 32,
  color = palette.bgRaised,
  padding = 32,
  width,
  height,
  style,
  className,
}) => {
  return (
    <div
      className={className}
      style={{
        backgroundColor: color,
        borderRadius: radius,
        padding,
        width,
        height,
        boxSizing: "border-box",
        position: "relative",
        overflow: "hidden",
        ...style,
      }}
    >
      {children}
    </div>
  );
};
