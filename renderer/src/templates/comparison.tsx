import React from "react";
import { interpolate } from "remotion";
import { useSceneClock } from "../clock/SceneClockContext";
import { Avatar } from "../components/Avatar";
import { FitText, type FitTextSlot } from "../components/FitText";
import { Icon } from "../components/Icon";
import type {
  ComparisonPanel,
  ComparisonProps,
  TimelineSceneTiming,
} from "../generated/contracts";
import { useCast } from "../story/entities";
import { EASE_ENTER, EASE_EXIT } from "../theme/motion";
import { palette } from "../theme/palette";

const HEADING_SLOT: FitTextSlot = {
  font: "display",
  weight: 800,
  size_max: 56,
  size_min: 40,
  max_lines: 1,
  box_width: 760,
};

const POINT_SLOT: FitTextSlot = {
  font: "body",
  weight: 600,
  size_max: 38,
  size_min: 28,
  max_lines: 2,
  box_width: 820,
};

export interface ComparisonTemplateProps {
  sceneId: string;
  props: ComparisonProps;
  timing?: TimelineSceneTiming;
  debug?: boolean;
  isGallery?: boolean;
}

const SingleComparisonPanel: React.FC<{
  panel: ComparisonPanel;
  panelId: "a" | "b";
  top: number;
  startFrame: number;
  sceneId: string;
  clockFrame: number;
  defaultAccent: string;
  floatY?: number;
  debug: boolean;
  isGallery: boolean;
}> = ({
  panel,
  panelId,
  top,
  startFrame,
  sceneId,
  clockFrame,
  defaultAccent,
  floatY = 0,
  debug,
  isGallery,
}) => {
  const cast = useCast(panel.cast_id);
  const accentColor = cast?.color || defaultAccent;

  const panelOpacity = interpolate(
    clockFrame,
    [startFrame, startFrame + 10],
    [0, 1],
    {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    }
  );
  const panelY = interpolate(
    clockFrame,
    [startFrame, startFrame + 10],
    [30, 0],
    {
      easing: EASE_ENTER,
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    }
  );

  const points = panel.points || [];

  return (
    <div
      style={{
        position: "absolute",
        left: 60,
        top,
        width: 960,
        height: 460,
        borderRadius: 32,
        backgroundColor: palette.bgRaised,
        opacity: panelOpacity,
        transform: `translateY(${panelY + floatY}px)`,
        overflow: "hidden",
        boxSizing: "border-box",
        padding: "24px 36px",
      }}
    >
      {/* 10 px left accent bar */}
      <div
        style={{
          position: "absolute",
          left: 0,
          top: 0,
          width: 10,
          height: 460,
          backgroundColor: accentColor,
        }}
      />

      {/* Heading row */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          height: 96,
          marginBottom: 16,
        }}
      >
        {cast ? (
          <div
            style={{
              width: 96,
              height: 96,
              marginRight: 24,
              flexShrink: 0,
            }}
          >
            <Avatar avatar={cast.avatar} size={96} />
          </div>
        ) : panel.icon ? (
          <div
            style={{
              width: 80,
              height: 80,
              marginRight: 24,
              flexShrink: 0,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            <Icon name={panel.icon} size={80} color={accentColor} />
          </div>
        ) : null}

        <div style={{ flex: 1, maxWidth: 760 }}>
          <FitText
            slot={HEADING_SLOT}
            text={panel.heading}
            sceneId={sceneId}
            template="comparison"
            slotName={`heading_${panelId}`}
            debug={debug}
            isGallery={isGallery}
            style={{
              textAlign: "left",
              color: palette.ink,
            }}
          />
        </div>
      </div>

      {/* Points list */}
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          gap: 12,
        }}
      >
        {points.map((pt, pIdx) => {
          const ptStart = startFrame + 10 + pIdx * 4;
          const ptOpacity = interpolate(
            clockFrame,
            [ptStart, ptStart + 8],
            [0, 1],
            {
              extrapolateLeft: "clamp",
              extrapolateRight: "clamp",
            }
          );

          return (
            <div
              key={pIdx}
              style={{
                display: "flex",
                alignItems: "flex-start",
                opacity: ptOpacity,
                width: 860,
              }}
            >
              {/* Bullet dot */}
              <div
                style={{
                  width: 10,
                  height: 10,
                  borderRadius: "50%",
                  backgroundColor: palette.highlight,
                  marginTop: 14,
                  marginRight: 16,
                  flexShrink: 0,
                }}
              />
              <div style={{ width: 820 }}>
                <FitText
                  slot={POINT_SLOT}
                  text={pt}
                  sceneId={sceneId}
                  template="comparison"
                  slotName={`point_${panelId}_${pIdx}`}
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
    </div>
  );
};

export const Comparison: React.FC<ComparisonTemplateProps> = ({
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

  const panelBStart =
    timing?.item_frames?.[1] ?? Math.floor(clock.sceneFrames * 0.3);

  // Hold: VS badge rotates +/- 3 deg slowly; panels have gentle idle breathing/float (+/- 3 px)
  const vsRotation =
    Math.sin((clock.frame * 2 * Math.PI) / 90) * 3;
  const floatA =
    Math.sin((clock.frame * 2 * Math.PI) / 90) * 3;
  const floatB =
    Math.sin(((clock.frame + 45) * 2 * Math.PI) / 90) * 3;

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
      {/* Panel A: y 160-620 */}
      <SingleComparisonPanel
        panel={props.a}
        panelId="a"
        top={160}
        startFrame={0}
        sceneId={sceneId}
        clockFrame={clock.frame}
        defaultAccent={palette.castSlots[0]}
        floatY={floatA}
        debug={debug}
        isGallery={isGallery}
      />

      {/* Panel B: y 700-1160 */}
      <SingleComparisonPanel
        panel={props.b}
        panelId="b"
        top={700}
        startFrame={panelBStart}
        sceneId={sceneId}
        clockFrame={clock.frame}
        defaultAccent={palette.castSlots[1]}
        floatY={floatB}
        debug={debug}
        isGallery={isGallery}
      />

      {/* "VS" badge: 120 px highlight circle at (540, 660) with navy "VS" */}
      <div
        style={{
          position: "absolute",
          left: 480,
          top: 600,
          width: 120,
          height: 120,
          borderRadius: "50%",
          backgroundColor: palette.highlight,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          zIndex: 10,
          transform: `rotate(${vsRotation}deg)`,
          boxShadow: "0 8px 24px rgba(0, 0, 0, 0.4)",
        }}
      >
        <span
          style={{
            fontFamily: "Poppins, sans-serif",
            fontWeight: 900,
            fontSize: 48,
            color: palette.bg,
            lineHeight: 1,
          }}
        >
          VS
        </span>
      </div>
    </div>
  );
};
