import React from "react";
import { interpolate, spring } from "remotion";
import { useSceneClock } from "../clock/SceneClockContext";
import { FitText, type FitTextSlot } from "../components/FitText";
import { Icon } from "../components/Icon";
import type { SceneOverlay } from "../generated/contracts";
import { EASE_EXIT, SPRING_POP_CONFIG } from "../theme/motion";
import { palette } from "../theme/palette";

export interface OverlayLayerProps {
  overlays?: SceneOverlay[];
  sceneId: string;
  debug?: boolean;
}

const THOUGHT_SLOT: FitTextSlot = {
  font: "body",
  weight: 700,
  size_max: 36,
  size_min: 28,
  max_lines: 2,
  box_width: 200,
};

const LABEL_SLOT: FitTextSlot = {
  font: "body",
  weight: 700,
  size_max: 34,
  size_min: 26,
  max_lines: 2,
  box_width: 240,
};

export const OverlayLayer: React.FC<OverlayLayerProps> = ({
  overlays,
  sceneId,
  debug = false,
}) => {
  const clock = useSceneClock();

  if (!overlays || overlays.length === 0) {
    return null;
  }

  // Entrance spring at scene frame 15
  const enterSpring =
    clock.frame < 15
      ? 0
      : spring({
          frame: clock.frame - 15,
          fps: 30,
          config: SPRING_POP_CONFIG,
        });

  // Bob 4 px with a period of 60 frames after entrance
  const bob =
    clock.frame >= 15
      ? 4 * Math.sin(((clock.frame - 15) / 60) * 2 * Math.PI)
      : 0;

  // Scene exit fade and translate
  const exitOpacity = interpolate(clock.exitProgress, [0, 1], [1, 0]);
  const exitY = interpolate(clock.exitProgress, [0, 1], [0, -24], {
    easing: EASE_EXIT,
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
        zIndex: 5,
      }}
    >
      {overlays.map((overlay, idx) => {
        const key = `${sceneId}-overlay-${idx}-${overlay.kind}`;
        const itemTransform = `translateY(${bob}px) scale(${enterSpring})`;
        const itemOpacity = Math.min(1, Math.max(0, enterSpring));

        if (overlay.kind === "motif_token") {
          // 120 px bgRaised circle with a 4 px highlight ring and a 72 px highlight icon, centred at (900, 240)
          return (
            <div
              key={key}
              data-overlay="motif_token"
              style={{
                position: "absolute",
                left: 840,
                top: 180,
                width: 120,
                height: 120,
                borderRadius: "50%",
                backgroundColor: palette.bgRaised,
                border: `4px solid ${palette.highlight}`,
                boxSizing: "border-box",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                boxShadow: "0 8px 24px rgba(0, 0, 0, 0.4)",
                transform: itemTransform,
                opacity: itemOpacity,
              }}
            >
              <Icon
                name={overlay.icon || "Sparkle"}
                size={72}
                color={palette.highlight}
                weight="fill"
              />
            </div>
          );
        }

        if (overlay.kind === "thought") {
          // Cloud 240x170 centred at (180, 250), fill ink at 0.92; 84 px navy icon or <=3 words in body 700 36->28
          return (
            <div
              key={key}
              data-overlay="thought"
              style={{
                position: "absolute",
                left: 60,
                top: 165,
                width: 240,
                height: 170,
                borderRadius: 50,
                backgroundColor: palette.ink,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                padding: "16px 20px",
                boxSizing: "border-box",
                boxShadow: "0 8px 24px rgba(0, 0, 0, 0.4)",
                transform: itemTransform,
                opacity: 0.92 * itemOpacity,
              }}
            >
              {overlay.text ? (
                <FitText
                  slot={THOUGHT_SLOT}
                  text={overlay.text}
                  sceneId={sceneId}
                  template="overlays"
                  slotName={`thought_${idx}`}
                  debug={debug}
                  style={{
                    color: palette.bgDeep,
                    textAlign: "center",
                    fontWeight: 700,
                  }}
                />
              ) : (
                <Icon
                  name={overlay.icon || "ChatCircleDots"}
                  size={84}
                  color={palette.bgDeep}
                  weight="fill"
                />
              )}
            </div>
          );
        }

        if (overlay.kind === "label") {
          // Chip bgDeep / ink, body 700 34->26 * 2 lines * 240 px, within [60, 200, 300, 302]
          return (
            <div
              key={key}
              data-overlay="label"
              style={{
                position: "absolute",
                left: 60,
                top: 200,
                width: 240,
                height: 102,
                borderRadius: 24,
                backgroundColor: palette.bgDeep,
                border: `2px solid ${palette.highlight}`,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                boxSizing: "border-box",
                boxShadow: "0 8px 24px rgba(0, 0, 0, 0.35)",
                transform: itemTransform,
                opacity: itemOpacity,
              }}
            >
              <FitText
                slot={LABEL_SLOT}
                text={overlay.text || "Aside"}
                sceneId={sceneId}
                template="overlays"
                slotName={`label_${idx}`}
                debug={debug}
                style={{
                  color: palette.ink,
                  textAlign: "center",
                  fontWeight: 700,
                  padding: "0 8px",
                  boxSizing: "border-box",
                }}
              />
            </div>
          );
        }

        if (overlay.kind === "prop") {
          // 140 px icon in inkMuted, centred at (170, 1090)
          return (
            <div
              key={key}
              data-overlay="prop"
              style={{
                position: "absolute",
                left: 100,
                top: 1020,
                width: 140,
                height: 140,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                transform: itemTransform,
                opacity: itemOpacity,
              }}
            >
              <Icon
                name={overlay.icon || "Package"}
                size={140}
                color={palette.inkMuted}
                weight="fill"
              />
            </div>
          );
        }

        return null;
      })}
    </div>
  );
};
