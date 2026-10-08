import React from "react";
import { interpolate } from "remotion";
import { useSceneClock } from "../clock/SceneClockContext";
import { FitText, type FitTextSlot } from "../components/FitText";
import { Icon } from "../components/Icon";
import type { CauseEffectProps, TimelineSceneTiming } from "../generated/contracts";
import { EASE_ENTER, EASE_EXIT } from "../theme/motion";
import { palette } from "../theme/palette";

const LABEL_SLOT: FitTextSlot = {
  font: "body",
  weight: 700,
  size_max: 44,
  size_min: 32,
  max_lines: 2,
  box_width: 620,
};

export interface CauseEffectTemplateProps {
  sceneId: string;
  props: CauseEffectProps;
  timing?: TimelineSceneTiming;
  debug?: boolean;
  isGallery?: boolean;
}

export const CauseEffect: React.FC<CauseEffectTemplateProps> = ({
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

  const nodes = props.nodes || [];
  const n = nodes.length;
  const cardHeight = 150;
  const gap = 90;
  const totalHeight = n * cardHeight + (n - 1) * gap;
  const stackTop = 660 - totalHeight / 2;

  // Pulse for the last arrow's head
  const arrowPulse =
    1.0 + 0.15 * Math.sin((clock.frame * 2 * Math.PI) / 45);

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
      {nodes.map((node, idx) => {
        const itemFrame =
          timing?.item_frames?.[idx] ??
          Math.floor((idx * (clock.sceneFrames * 0.6)) / Math.max(1, n));

        const nodeOpacity = interpolate(
          clock.frame,
          [itemFrame, itemFrame + 8],
          [0, 1],
          {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
          }
        );
        const nodeScale = interpolate(
          clock.frame,
          [itemFrame, itemFrame + 8],
          [0.92, 1],
          {
            easing: EASE_ENTER,
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
          }
        );

        const cardTop = stackTop + idx * (cardHeight + gap);

        // Next arrow between card idx and idx + 1
        const hasArrow = idx < n - 1;
        const nextFrame =
          timing?.item_frames?.[idx + 1] ??
          Math.floor(((idx + 1) * (clock.sceneFrames * 0.6)) / Math.max(1, n));

        const arrowProgress = interpolate(
          clock.frame,
          [Math.max(0, nextFrame - 8), nextFrame],
          [0, 1],
          {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
          }
        );

        const isLastArrow = idx === n - 2;

        return (
          <React.Fragment key={idx}>
            {/* Card: 840x150, radius 28, bgRaised, centred at x 540 */}
            <div
              data-occupies={`card_${idx}`}
              style={{
                position: "absolute",
                left: 120,
                top: cardTop,
                width: 840,
                height: cardHeight,
                borderRadius: 28,
                backgroundColor: palette.bgRaised,
                opacity: nodeOpacity,
                transform: `scale(${nodeScale})`,
                boxSizing: "border-box",
                padding: "15px 30px",
                display: "flex",
                alignItems: "center",
              }}
            >
              {node.icon && (
                <div
                  style={{
                    width: 80,
                    height: 80,
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    marginRight: 30,
                    flexShrink: 0,
                  }}
                >
                  <Icon name={node.icon} size={80} color={palette.highlight} />
                </div>
              )}

              <div
                style={{
                  width: node.icon ? 620 : 780,
                  display: "flex",
                  alignItems: "center",
                }}
              >
                <FitText
                  slot={LABEL_SLOT}
                  text={node.label}
                  sceneId={sceneId}
                  template="cause_effect"
                  slotName={`label_${idx}`}
                  debug={debug}
                  isGallery={isGallery}
                  style={{
                    textAlign: node.icon ? "left" : "center",
                    color: palette.ink,
                    width: "100%",
                  }}
                />
              </div>
            </div>

            {/* Down-arrow: 8 px highlight stroke with a head */}
            {hasArrow && (
              <div
                style={{
                  position: "absolute",
                  left: 540 - 24,
                  top: cardTop + cardHeight + 4,
                  width: 48,
                  height: gap - 8,
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "center",
                  justifyContent: "space-between",
                  opacity: arrowProgress,
                }}
              >
                {/* Arrow stem */}
                <div
                  style={{
                    width: 8,
                    height: (gap - 28) * arrowProgress,
                    backgroundColor: palette.highlight,
                    borderRadius: 4,
                  }}
                />
                {/* Arrow head */}
                <div
                  style={{
                    width: 0,
                    height: 0,
                    borderLeft: "16px solid transparent",
                    borderRight: "16px solid transparent",
                    borderTop: `20px solid ${palette.highlight}`,
                    transform: isLastArrow
                      ? `scale(${arrowPulse})`
                      : undefined,
                    transformOrigin: "center top",
                  }}
                />
              </div>
            )}
          </React.Fragment>
        );
      })}
    </div>
  );
};
