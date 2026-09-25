import React from "react";
import { interpolate } from "remotion";
import { useSceneClock } from "../clock/SceneClockContext";
import { FitText, type FitTextSlot } from "../components/FitText";
import { Icon } from "../components/Icon";
import type { TimelineSceneTiming, TitleCardProps } from "../generated/contracts";
import { EASE_ENTER, EASE_EXIT } from "../theme/motion";
import { palette } from "../theme/palette";

const TITLE_SLOT: FitTextSlot = {
  font: "display",
  weight: 800,
  size_max: 104,
  size_min: 64,
  max_lines: 3,
  box_width: 900,
};

const SUBTITLE_SLOT: FitTextSlot = {
  font: "body",
  weight: 600,
  size_max: 44,
  size_min: 32,
  max_lines: 2,
  box_width: 860,
};

export interface TitleCardTemplateProps {
  sceneId: string;
  props: TitleCardProps;
  timing?: TimelineSceneTiming;
  debug?: boolean;
  isGallery?: boolean;
}

export const TitleCard: React.FC<TitleCardTemplateProps> = ({
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

  // Icon motion: springs in at frame 0
  const iconScale = interpolate(clock.frame, [0, 8, 14], [0, 1.15, 1], {
    extrapolateRight: "clamp",
  });
  const iconOpacity = interpolate(clock.frame, [0, 6], [0, 1], {
    extrapolateRight: "clamp",
  });

  // Hold motion: title block scales 1.00 -> 1.03 across the scene
  const titleScale = interpolate(
    clock.frame,
    [0, Math.max(1, clock.sceneFrames)],
    [1.0, 1.03],
    { extrapolateRight: "clamp" }
  );

  // Subtitle enters at frame 12
  const subOpacity = interpolate(clock.frame, [12, 18], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const subY = interpolate(clock.frame, [12, 18], [16, 0], {
    easing: EASE_ENTER,
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const words = (props.title || "").split(/\s+/).filter(Boolean);

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
      {/* Icon: 200px centred at (540, 380) */}
      {props.icon && (
        <div
          style={{
            position: "absolute",
            left: 440,
            top: 280,
            width: 200,
            height: 200,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            opacity: iconOpacity,
            transform: `scale(${iconScale})`,
          }}
        >
          <Icon name={props.icon} size={200} color={palette.highlight} />
        </div>
      )}

      {/* Title block centred around y 640 */}
      <div
        style={{
          position: "absolute",
          left: 90,
          top: props.icon ? 520 : 440,
          width: 900,
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          transformOrigin: "center top",
          transform: `scale(${titleScale})`,
        }}
      >
        <FitText
          slot={TITLE_SLOT}
          sceneId={sceneId}
          template="title_card"
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

        {props.subtitle && (
          <div
            style={{
              marginTop: 32,
              width: 860,
              opacity: subOpacity,
              transform: `translateY(${subY}px)`,
            }}
          >
            <FitText
              slot={SUBTITLE_SLOT}
              text={props.subtitle}
              sceneId={sceneId}
              template="title_card"
              slotName="subtitle"
              debug={debug}
              isGallery={isGallery}
              style={{
                textAlign: "center",
                color: palette.inkMuted,
              }}
            />
          </div>
        )}
      </div>
    </div>
  );
};
