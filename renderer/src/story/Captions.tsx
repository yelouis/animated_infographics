import React from "react";
import { interpolate } from "remotion";
import { useGlobalClock } from "../clock/GlobalClockContext";
import type { CaptionPage, Scenes } from "../generated/contracts";
import { FitText } from "../components/FitText";
import { ZONES } from "../theme/layout";
import { palette } from "../theme/palette";
import { CAPTION_SLOT } from "../theme/type";

export interface CaptionsProps {
  pages: CaptionPage[];
  scenes: Scenes;
}

export const Captions: React.FC<CaptionsProps> = ({ pages, scenes }) => {
  const clock = useGlobalClock();
  const frame = clock.frame;

  // 1. Check if current frame is hidden by any hide_captions scene
  const isHidden = scenes.some(
    (sc) =>
      sc.hide_captions &&
      frame >= sc.start_frame &&
      frame < sc.end_frame
  );

  if (isHidden) {
    return null;
  }

  // 2. Find active page
  const activePage = pages.find(
    (p) => frame >= p.start_frame && frame < p.end_frame
  );

  if (!activePage) {
    return null;
  }

  // 3. Page entrance: 4 frames scale 0.92->1, opacity 0->1
  const pageAge = frame - activePage.start_frame;
  const enterProgress = Math.min(1, Math.max(0, pageAge / 4));
  const pageScale = interpolate(enterProgress, [0, 1], [0.92, 1]);
  const pageOpacity = enterProgress;

  return (
    <div
      style={{
        position: "absolute",
        left: ZONES.captionBand.x0,
        top: ZONES.captionBand.centerY - 100,
        width: ZONES.captionBand.width,
        height: 200,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        opacity: pageOpacity,
        transform: `scale(${pageScale})`,
        transformOrigin: "center center",
        pointerEvents: "none",
        zIndex: 50,
      }}
    >
      <FitText
        slot={CAPTION_SLOT}
        sceneId="captions"
        template="captions"
        slotName="captions"
        style={{
          textAlign: "center",
          wordBreak: "break-word",
        }}
      >
        {activePage.words.map((w, idx) => {
          const nextStart =
            idx < activePage.words.length - 1
              ? activePage.words[idx + 1].start_frame
              : activePage.end_frame;
          const isActive = frame >= w.start_frame && frame < nextStart;

          return (
            <span
              key={`${idx}-${w.text}`}
              style={{
                display: "inline-block",
                marginLeft: isActive ? "0.15em" : "0",
                marginRight: isActive ? "0.45em" : "0.3em",
                color: isActive ? palette.highlight : palette.ink,
                transform: `scale(${isActive ? 1.12 : 1.0})`,
                transformOrigin: "bottom center",
                WebkitTextStroke: `12px ${palette.bgDeep}`,
                paintOrder: "stroke fill",
              }}
            >
              {w.text}
            </span>
          );
        })}
      </FitText>
    </div>
  );
};
