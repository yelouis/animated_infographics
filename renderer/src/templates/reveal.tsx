import React from "react";
import { interpolate } from "remotion";
import { useSceneClock } from "../clock/SceneClockContext";
import { FitText, type FitTextSlot } from "../components/FitText";
import type { RevealProps, SceneOverlay, TimelineSceneTiming } from "../generated/contracts";
import { EASE_EXIT } from "../theme/motion";
import { palette } from "../theme/palette";

const KICKER_SLOT: FitTextSlot = {
  font: "display",
  weight: 800,
  size_max: 56,
  size_min: 40,
  max_lines: 1,
  box_width: 900,
};

const TEXT_SLOT: FitTextSlot = {
  font: "display",
  weight: 800,
  size_max: 96,
  size_min: 60,
  max_lines: 4,
  box_width: 920,
};

export interface RevealTemplateProps {
  sceneId: string;
  props: RevealProps;
  timing?: TimelineSceneTiming;
  debug?: boolean;
  isGallery?: boolean;
  overlays?: SceneOverlay[];
}

export const Reveal: React.FC<RevealTemplateProps> = ({
  sceneId,
  props,
  debug = false,
  isGallery = false,
  overlays,
}) => {
  const clock = useSceneClock();
  const hasProp = overlays?.some((o) => o.kind === "prop");

  // Full-canvas ink flash at opacity 0.35 fading to 0 over frames 0-3
  const flashOpacity =
    clock.frame <= 3
      ? interpolate(clock.frame, [0, 3], [0.35, 0], {
          extrapolateRight: "clamp",
        })
      : 0;

  // Text zooms 1.30 -> 1.00 with spring pop
  const zoom = interpolate(clock.frame, [0, 8, 14], [1.3, 0.98, 1.0], {
    extrapolateRight: "clamp",
  });

  // Hold: 2 px shake decaying to 0 over 20 frames, then a slow 1.00 -> 1.02 scale
  const shakeX =
    clock.frame < 20
      ? (1 - clock.frame / 20) * 2 * Math.sin(clock.frame * Math.PI)
      : 0;
  const holdScale =
    1.0 + 0.02 * (clock.frame / Math.max(1, clock.sceneFrames));

  // Exit transforms
  const exitOpacity = interpolate(clock.exitProgress, [0, 1], [1, 0]);
  const exitY = interpolate(clock.exitProgress, [0, 1], [0, -24], {
    easing: EASE_EXIT,
  });

  const kickerText = (props.kicker || "").toUpperCase();

  return (
    <div
      style={{
        position: "absolute",
        top: 0,
        left: 0,
        width: 1080,
        height: 1920,
        opacity: exitOpacity,
        transform: `translateY(${exitY}px)`,
        pointerEvents: "none",
      }}
    >
      {/* Full-canvas ink flash */}
      {flashOpacity > 0 && (
        <div
          style={{
            position: "absolute",
            top: 0,
            left: 0,
            width: 1080,
            height: 1920,
            backgroundColor: palette.ink,
            opacity: flashOpacity,
            zIndex: 10,
          }}
        />
      )}

      {/* Kicker: centred at y 440 in danger */}
      <div
        style={{
          position: "absolute",
          left: 90,
          top: 410,
          width: 900,
          transform: `translateX(${shakeX}px)`,
        }}
      >
        <FitText
          slot={KICKER_SLOT}
          text={kickerText}
          sceneId={sceneId}
          template="reveal"
          slotName="kicker"
          debug={debug}
          isGallery={isGallery}
          style={{
            textAlign: "center",
            color: palette.danger,
            letterSpacing: 4,
          }}
        />
      </div>

      {/* Text block: centred at y 700; lifts to top: 480 when prop overlay is present */}
      <div
        style={{
          position: "absolute",
          left: 80,
          top: hasProp ? 480 : 560,
          width: 920,
          transformOrigin: "center center",
          transform: `scale(${zoom * holdScale}) translateX(${shakeX}px)`,
        }}
      >
        <FitText
          slot={TEXT_SLOT}
          text={props.text}
          sceneId={sceneId}
          template="reveal"
          slotName="text"
          debug={debug}
          isGallery={isGallery}
          style={{
            textAlign: "center",
            color: palette.ink,
          }}
        />
      </div>
    </div>
  );
};
