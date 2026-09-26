import React from "react";
import { IMAGE_SCRIM } from "../theme/layout";
import { palette } from "../theme/palette";

function hexToRgba(hex: string, alpha: number): string {
  const clean = hex.replace("#", "");
  const r = parseInt(clean.substring(0, 2), 16);
  const g = parseInt(clean.substring(2, 4), 16);
  const b = parseInt(clean.substring(4, 6), 16);
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

export interface ImageScrimProps {
  style?: React.CSSProperties;
  className?: string;
}

export const ImageScrim: React.FC<ImageScrimProps> = ({ style, className }) => {
  const [start, mid, end] = IMAGE_SCRIM.stops;
  const totalSpan = end[0] - start[0]; // 1120 - 640 = 480 px
  const midPct = ((mid[0] - start[0]) / totalSpan) * 100; // (160 / 480) * 100 = 33.333%

  const c0 = hexToRgba(palette.bg, start[1]);
  const c1 = hexToRgba(palette.bg, mid[1]);
  const c2 = hexToRgba(palette.bg, end[1]);

  const gradient = `linear-gradient(to bottom, ${c0} 0%, ${c1} ${midPct.toFixed(2)}%, ${c2} 100%)`;

  return (
    <div
      className={className}
      style={{
        position: "absolute",
        bottom: 0,
        left: 0,
        width: "100%",
        height: totalSpan,
        background: gradient,
        pointerEvents: "none",
        ...style,
      }}
    />
  );
};
