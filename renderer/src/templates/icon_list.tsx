import React from "react";
import { interpolate } from "remotion";
import { useSceneClock } from "../clock/SceneClockContext";
import { FitText, type FitTextSlot } from "../components/FitText";
import { Icon } from "../components/Icon";
import type { IconListProps, TimelineSceneTiming } from "../generated/contracts";
import { EASE_ENTER, EASE_EXIT } from "../theme/motion";
import { palette } from "../theme/palette";

const HEADING_SLOT: FitTextSlot = {
  font: "display",
  weight: 800,
  size_max: 64,
  size_min: 44,
  max_lines: 2,
  box_width: 900,
};

const LABEL_SLOT: FitTextSlot = {
  font: "body",
  weight: 700,
  size_max: 48,
  size_min: 34,
  max_lines: 2,
  box_width: 700,
};

export interface IconListTemplateProps {
  sceneId: string;
  props: IconListProps;
  timing?: TimelineSceneTiming;
  debug?: boolean;
  isGallery?: boolean;
}

export const IconList: React.FC<IconListTemplateProps> = ({
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

  const headingOpacity = interpolate(clock.frame, [0, 10], [0, 1], {
    extrapolateRight: "clamp",
  });

  const items = props.items || [];
  const startY = props.heading ? 400 : 260;
  const rowGap = 20;
  const rowHeight = 150;

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
      {/* Optional heading top y 200 */}
      {props.heading && (
        <div
          style={{
            position: "absolute",
            left: 90,
            top: 200,
            width: 900,
            opacity: headingOpacity,
          }}
        >
          <FitText
            slot={HEADING_SLOT}
            text={props.heading}
            sceneId={sceneId}
            template="icon_list"
            slotName="heading"
            debug={debug}
            isGallery={isGallery}
            style={{
              textAlign: "left",
              color: palette.ink,
            }}
          />
        </div>
      )}

      {/* Rows 150 px tall */}
      {items.map((item, idx) => {
        const itemFrame =
          timing?.item_frames?.[idx] ??
          Math.floor((idx * (clock.sceneFrames * 0.5)) / Math.max(1, items.length));

        const rowOpacity = interpolate(
          clock.frame,
          [itemFrame, itemFrame + 10],
          [0, 1],
          {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
          }
        );
        const rowX = interpolate(
          clock.frame,
          [itemFrame, itemFrame + 10],
          [-30, 0],
          {
            easing: EASE_ENTER,
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
          }
        );

        // Hold: circles pulse 1.00 -> 1.05, period 60 frames, phase-offset by row
        const circlePulse =
          1.0 +
          0.05 *
            Math.sin(((clock.frame + idx * 15) * 2 * Math.PI) / 60);

        const rowTop = startY + idx * (rowHeight + rowGap);
        const castColor = palette.castSlots[idx % 4];

        return (
          <div
            key={idx}
            style={{
              position: "absolute",
              left: 0,
              top: rowTop,
              width: 1080,
              height: rowHeight,
              opacity: rowOpacity,
              transform: `translateX(${rowX}px)`,
            }}
          >
            {/* 132 px circle in cast slot colour holding 96 px navy icon centred at x 190 */}
            <div
              style={{
                position: "absolute",
                left: 124,
                top: 9,
                width: 132,
                height: 132,
                borderRadius: "50%",
                backgroundColor: castColor,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                transform: `scale(${circlePulse})`,
                transformOrigin: "center center",
              }}
            >
              <Icon name={item.icon} size={96} color={palette.bg} />
            </div>

            {/* Label: left edge at x 290, width 700 */}
            <div
              style={{
                position: "absolute",
                left: 290,
                top: 25,
                width: 700,
                height: 100,
                display: "flex",
                alignItems: "center",
              }}
            >
              <FitText
                slot={LABEL_SLOT}
                text={item.label}
                sceneId={sceneId}
                template="icon_list"
                slotName={`label_${idx}`}
                debug={debug}
                isGallery={isGallery}
                style={{
                  textAlign: "left",
                  color: palette.ink,
                }}
              />
            </div>
          </div>
        );
      })}
    </div>
  );
};
