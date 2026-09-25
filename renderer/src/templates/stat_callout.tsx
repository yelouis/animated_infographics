import React from "react";
import { interpolate } from "remotion";
import { useSceneClock } from "../clock/SceneClockContext";
import { FitText, type FitTextSlot } from "../components/FitText";
import { Icon } from "../components/Icon";
import type { StatCalloutProps, TimelineSceneTiming } from "../generated/contracts";
import { EASE_EXIT } from "../theme/motion";
import { palette } from "../theme/palette";

const VALUE_SLOT: FitTextSlot = {
  font: "display",
  weight: 800,
  size_max: 200,
  size_min: 110,
  max_lines: 1,
  box_width: 940,
};

const SUFFIX_SLOT: FitTextSlot = {
  font: "display",
  weight: 700,
  size_max: 64,
  size_min: 44,
  max_lines: 1,
  box_width: 900,
};

const CAPTION_SLOT: FitTextSlot = {
  font: "body",
  weight: 600,
  size_max: 44,
  size_min: 32,
  max_lines: 3,
  box_width: 860,
};

export interface StatCalloutTemplateProps {
  sceneId: string;
  props: StatCalloutProps;
  timing?: TimelineSceneTiming;
  debug?: boolean;
  isGallery?: boolean;
}

export const StatCallout: React.FC<StatCalloutTemplateProps> = ({
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

  // Count-up timing
  const countFrames =
    timing?.count_frames ??
    Math.max(1, Math.min(24, Math.floor(0.4 * clock.sceneFrames)));

  const countProgress =
    countFrames > 0 ? Math.min(1, Math.max(0, clock.frame / countFrames)) : 1;
  // Ease-out cubic: 1 - (1 - t)^3
  const countEase = 1 - Math.pow(1 - countProgress, 3);
  const curValue = (props.value ?? 0) * countEase;

  const decimals = props.decimals ?? 0;
  const formattedNum = curValue.toLocaleString("en-US", {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });

  const displayScale =
    props.display_scale && props.display_scale !== "none"
      ? ` ${props.display_scale}`
      : "";
  const valueLine = `${props.prefix || ""}${formattedNum}${displayScale}`;

  // Hold motion: value scales 1.00 -> 1.04 across the scene
  const valueScale =
    1.0 + 0.04 * (clock.frame / Math.max(1, clock.sceneFrames));

  // Entrance opacity
  const enterOpacity = interpolate(clock.frame, [0, 8], [0, 1], {
    extrapolateRight: "clamp",
  });

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
      {/* Icon: 160 px centred at (540, 330) */}
      {props.icon && (
        <div
          style={{
            position: "absolute",
            left: 460,
            top: 250,
            width: 160,
            height: 160,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            opacity: enterOpacity,
          }}
        >
          <Icon name={props.icon} size={160} color={palette.highlight} />
        </div>
      )}

      {/* Value block: centred at y 560 */}
      <div
        style={{
          position: "absolute",
          left: 70,
          top: props.icon ? 440 : 380,
          width: 940,
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          opacity: enterOpacity,
          transformOrigin: "center top",
          transform: `scale(${valueScale})`,
        }}
      >
        <FitText
          slot={VALUE_SLOT}
          text={valueLine}
          sceneId={sceneId}
          template="stat_callout"
          slotName="value"
          debug={debug}
          isGallery={isGallery}
          style={{
            textAlign: "center",
            color: palette.ink,
          }}
        />

        {props.suffix && (
          <div
            style={{
              marginTop: 16,
              width: 900,
            }}
          >
            <FitText
              slot={SUFFIX_SLOT}
              text={props.suffix}
              sceneId={sceneId}
              template="stat_callout"
              slotName="suffix"
              debug={debug}
              isGallery={isGallery}
              style={{
                textAlign: "center",
                color: palette.highlight,
              }}
            />
          </div>
        )}

        {props.caption && (
          <div
            style={{
              marginTop: 32,
              width: 860,
            }}
          >
            <FitText
              slot={CAPTION_SLOT}
              text={props.caption}
              sceneId={sceneId}
              template="stat_callout"
              slotName="caption"
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
