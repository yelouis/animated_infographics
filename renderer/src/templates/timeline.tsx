import React from "react";
import { interpolate } from "remotion";
import { useSceneClock } from "../clock/SceneClockContext";
import { FitText, type FitTextSlot } from "../components/FitText";
import type { TimelineProps, TimelineSceneTiming } from "../generated/contracts";
import { EASE_ENTER, EASE_EXIT } from "../theme/motion";
import { palette } from "../theme/palette";

const DATE_SLOT: FitTextSlot = {
  font: "display",
  weight: 800,
  size_max: 44,
  size_min: 32,
  max_lines: 1,
  box_width: 760,
};

const LABEL_SLOT: FitTextSlot = {
  font: "body",
  weight: 600,
  size_max: 40,
  size_min: 28,
  max_lines: 2,
  box_width: 760,
};

export interface TimelineTemplateProps {
  sceneId: string;
  props: TimelineProps;
  timing?: TimelineSceneTiming;
  debug?: boolean;
  isGallery?: boolean;
}

export const Timeline: React.FC<TimelineTemplateProps> = ({
  sceneId,
  props,
  timing,
  debug = false,
  isGallery = false,
}) => {
  const clock = useSceneClock();

  // Exit transforms
  const exitOpacity = interpolate(clock.exitProgress, [0, 1], [1, 0]);
  const exitY = interpolate(clock.exitProgress, [0, 1], [0, -24], {
    easing: EASE_EXIT,
  });

  // Vertical axis draws top-down over 12 frames (height 0 -> 900)
  const axisHeight = interpolate(clock.frame, [0, 12], [0, 900], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // Hold: highlighted dot's glow pulses (period 30 frames)
  const glowPhase = (clock.frame % 30) / 30;
  const glowRadius = 14 + Math.sin(glowPhase * 2 * Math.PI) * 8; // 6px to 22px
  const glowAlpha = 0.5 + Math.sin(glowPhase * 2 * Math.PI) * 0.25; // 0.25 to 0.75

  const events = props.events || [];
  const N = events.length;
  const stepY = N > 1 ? 900 / (N - 1) : 0;
  const itemFrames = timing?.item_frames || [];

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
      {/* Vertical axis line: at x 160 from y 220 to 1120, width 6px */}
      <div
        style={{
          position: "absolute",
          left: 157, // centred on 160
          top: 220,
          width: 6,
          height: axisHeight,
          backgroundColor: palette.inkMuted,
          borderRadius: 3,
        }}
      />

      {/* Events */}
      {events.map((ev, idx) => {
        const isHighlighted = idx === props.highlight_index;
        const targetY = 220 + stepY * idx;
        const startFrame = itemFrames[idx] ?? idx * 14;

        // Dot animation: scales from 0 to 1
        const dotScale = interpolate(
          clock.frame,
          [startFrame, startFrame + 6],
          [0, 1],
          {
            easing: EASE_ENTER,
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
          }
        );

        // Content animation: slides in from left (x: -16 -> 0, opacity 0 -> 1)
        const textOpacity = interpolate(
          clock.frame,
          [startFrame + 2, startFrame + 8],
          [0, 1],
          {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
          }
        );
        const textX = interpolate(
          clock.frame,
          [startFrame + 2, startFrame + 8],
          [-16, 0],
          {
            easing: EASE_ENTER,
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
          }
        );

        // Dot radius: normal 18px (diameter 36), highlighted 26px (diameter 52)
        const dotRadius = isHighlighted ? 26 : 18;
        const dotDiameter = dotRadius * 2;

        return (
          <React.Fragment key={idx}>
            {/* Dot at (160, targetY) */}
            <div
              style={{
                position: "absolute",
                left: 160 - dotRadius,
                top: targetY - dotRadius,
                width: dotDiameter,
                height: dotDiameter,
                borderRadius: "50%",
                backgroundColor: isHighlighted
                  ? palette.highlight
                  : palette.bgRaised,
                border: isHighlighted
                  ? `4px solid ${palette.bgDeep}`
                  : `4px solid ${palette.inkMuted}`,
                boxSizing: "border-box",
                transform: `scale(${dotScale})`,
                boxShadow: isHighlighted
                  ? `0 0 ${glowRadius}px rgba(233, 196, 106, ${glowAlpha})`
                  : "none",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                zIndex: 2,
              }}
            />

            {/* Event text: left edge x 220, vertically centered at targetY */}
            <div
              style={{
                position: "absolute",
                left: 220,
                top: targetY - 32,
                width: 760,
                display: "flex",
                flexDirection: "column",
                gap: 6,
                opacity: textOpacity,
                transform: `translateX(${textX}px)`,
                zIndex: 1,
              }}
            >
              {/* Date label: display 800, highlighted in highlight, others ink */}
              <div>
                <FitText
                  slot={DATE_SLOT}
                  text={ev.date_label}
                  sceneId={sceneId}
                  template="timeline"
                  slotName="date"
                  debug={debug}
                  isGallery={isGallery}
                  style={{
                    color: isHighlighted ? palette.highlight : palette.ink,
                    fontWeight: 800,
                  }}
                />
              </div>

              {/* Event label directly below date, in inkMuted */}
              <div>
                <FitText
                  slot={LABEL_SLOT}
                  text={ev.label}
                  sceneId={sceneId}
                  template="timeline"
                  slotName="label"
                  debug={debug}
                  isGallery={isGallery}
                  style={{
                    color: palette.inkMuted,
                    fontWeight: 600,
                  }}
                />
              </div>
            </div>
          </React.Fragment>
        );
      })}
    </div>
  );
};
