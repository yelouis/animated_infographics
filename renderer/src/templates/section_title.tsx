import React from "react";
import { interpolate, spring } from "remotion";
import { useSceneClock } from "../clock/SceneClockContext";
import { FitText, type FitTextSlot } from "../components/FitText";
import type { SectionTitleProps, TimelineSceneTiming } from "../generated/contracts";
import { EASE_ENTER, EASE_EXIT, SPRING_POP_CONFIG } from "../theme/motion";
import { palette } from "../theme/palette";

const TITLE_SLOT: FitTextSlot = {
  font: "display",
  weight: 800,
  size_max: 96,
  size_min: 64,
  max_lines: 3,
  box_width: 900,
};

export interface SectionTitleTemplateProps {
  sceneId: string;
  props: SectionTitleProps;
  timing?: TimelineSceneTiming;
  debug?: boolean;
  isGallery?: boolean;
}

export const SectionTitle: React.FC<SectionTitleTemplateProps> = ({
  sceneId,
  props,
  debug = false,
  isGallery = false,
}) => {
  const clock = useSceneClock();

  // Exit transforms
  const exitOpacity = interpolate(clock.exitProgress, [0, 1], [1, 0]);
  const exitY = interpolate(clock.exitProgress, [0, 1], [0, -24], {
    easing: EASE_EXIT,
  });

  // Hold motion: title block scales 1.00 -> 1.03 across the scene
  const titleScale = interpolate(
    clock.frame,
    [0, Math.max(1, clock.sceneFrames)],
    [1.0, 1.03],
    { extrapolateRight: "clamp" }
  );

  // Words stagger 3 frames each
  const words = (props.title || "").split(/\s+/).filter(Boolean);

  // Dots progress row: count dots of 28 px with 24 px gaps, centred at y 820
  // Dot at index is highlight and 36 px; earlier dots ink; later dots inkMuted
  // Current dot springs from 28 to 36 px at frame 8.
  // Hold: current dot pulses 1.00 -> 1.10, period 45 frames.
  const currentDotSpring =
    clock.frame < 8
      ? 0
      : spring({
          frame: clock.frame - 8,
          fps: 30,
          config: SPRING_POP_CONFIG,
        });

  // Spring from 28 to 36 px (ratio 28 / 36 to 1.0)
  const springScale = interpolate(currentDotSpring, [0, 1], [28 / 36, 1.0]);

  // Pulse 1.00 -> 1.10, period 45 frames
  const dotPulse = 1.05 + 0.05 * Math.sin((clock.frame * 2 * Math.PI) / 45);

  const currentDotScale = springScale * (clock.frame >= 8 ? dotPulse : 1.0);

  const count = Math.max(1, Math.min(10, props.count || 1));
  const currentIndex = Math.max(0, Math.min(count - 1, props.index ?? 0));

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
      {/* Title display block centred at y 620 */}
      <div
        style={{
          position: "absolute",
          left: 90,
          top: 620,
          width: 900,
          transform: `translateY(-50%) scale(${titleScale})`,
          transformOrigin: "center center",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
        }}
      >
        <FitText
          slot={TITLE_SLOT}
          text={props.title}
          sceneId={sceneId}
          template="section_title"
          slotName="title"
          debug={debug}
          isGallery={isGallery}
          style={{
            textAlign: "center",
            color: palette.ink,
          }}
        >
          {words.map((word, idx) => {
            const wordStartFrame = idx * 3;
            const wordOpacity = interpolate(
              clock.frame,
              [wordStartFrame, wordStartFrame + 6],
              [0, 1],
              {
                extrapolateLeft: "clamp",
                extrapolateRight: "clamp",
              }
            );
            const wordY = interpolate(
              clock.frame,
              [wordStartFrame, wordStartFrame + 6],
              [16, 0],
              {
                easing: EASE_ENTER,
                extrapolateLeft: "clamp",
                extrapolateRight: "clamp",
              }
            );

            return (
              <span
                key={`${idx}-${word}`}
                style={{
                  display: "inline-block",
                  margin: "0 0.18em",
                  opacity: wordOpacity,
                  transform: `translateY(${wordY}px)`,
                }}
              >
                {word}
              </span>
            );
          })}
        </FitText>
      </div>

      {/* Progress row: count dots of 28 px with 24 px gaps, centred at y 820 */}
      <div
        style={{
          position: "absolute",
          left: 0,
          top: 820,
          width: 1080,
          height: 48,
          transform: "translateY(-50%)",
          display: "flex",
          justifyContent: "center",
          alignItems: "center",
          gap: 24,
        }}
      >
        {Array.from({ length: count }).map((_, idx) => {
          const isCurrent = idx === currentIndex;
          const isEarlier = idx < currentIndex;

          if (isCurrent) {
            return (
              <div
                key={idx}
                style={{
                  width: 36,
                  height: 36,
                  borderRadius: "50%",
                  backgroundColor: palette.highlight,
                  boxSizing: "border-box",
                  flexShrink: 0,
                  transform: `scale(${currentDotScale})`,
                }}
              />
            );
          }

          return (
            <div
              key={idx}
              style={{
                width: 28,
                height: 28,
                borderRadius: "50%",
                backgroundColor: isEarlier ? palette.ink : palette.inkMuted,
                boxSizing: "border-box",
                flexShrink: 0,
              }}
            />
          );
        })}
      </div>
    </div>
  );
};
