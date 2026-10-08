import React from "react";
import { interpolate } from "remotion";
import { useSceneClock } from "../clock/SceneClockContext";
import { Avatar } from "../components/Avatar";
import { FitText, type FitTextSlot } from "../components/FitText";
import type { KineticQuoteProps, SceneOverlay } from "../generated/contracts";
import { useCast } from "../story/entities";
import { EASE_ENTER, EASE_EXIT, ENTER_FRAMES } from "../theme/motion";
import { palette } from "../theme/palette";

const TEXT_SLOT: FitTextSlot = {
  font: "display",
  weight: 800,
  size_max: 84,
  size_min: 56,
  max_lines: 5,
  box_width: 920,
};

const ATTRIBUTION_SLOT: FitTextSlot = {
  font: "body",
  weight: 700,
  size_max: 36,
  size_min: 28,
  max_lines: 1,
  box_width: 600,
};

export interface KineticQuoteTemplateProps {
  sceneId: string;
  props: KineticQuoteProps;
  debug?: boolean;
  isGallery?: boolean;
  overlays?: SceneOverlay[];
}

export const KineticQuote: React.FC<KineticQuoteTemplateProps> = ({
  sceneId,
  props,
  debug = false,
  isGallery = false,
  overlays,
}) => {
  const clock = useSceneClock();
  const hasToken = overlays?.some((o) => o.kind === "motif_token");
  const hasThought = overlays?.some((o) => o.kind === "thought");
  const containerTop = hasThought ? 290 : hasToken ? 254 : 240;
  const cast = useCast(props.attribution_cast_id);

  // Entrance & Exit transforms
  const enterOpacity = interpolate(clock.frame, [0, ENTER_FRAMES], [0, 1], {
    extrapolateRight: "clamp",
  });
  const enterY = interpolate(clock.frame, [0, ENTER_FRAMES], [40, 0], {
    easing: EASE_ENTER,
    extrapolateRight: "clamp",
  });

  const exitOpacity = interpolate(clock.exitProgress, [0, 1], [1, 0]);
  const exitY = interpolate(clock.exitProgress, [0, 1], [0, -24], {
    easing: EASE_EXIT,
  });

  // Hold motion: gentle 6 px float, period 90 frames
  const floatY = Math.sin((clock.frame * 2 * Math.PI) / 90) * 6;

  const totalOpacity = enterOpacity * exitOpacity;
  const totalY = enterY + exitY + floatY;

  // Split text into words and identify emphasis words
  const words = (props.text || "").split(/\s+/).filter(Boolean);
  const emphasisSet = new Set(
    (props.emphasis || []).map((e) => e.trim().toLowerCase().replace(/[^\w]/g, ""))
  );

  const castColor = cast?.color || palette.highlight;

  return (
    <div
      style={{
        position: "absolute",
        left: 80,
        top: containerTop,
        width: 920,
        height: 840,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        opacity: totalOpacity,
        transform: `translateY(${totalY}px)`,
      }}
    >
      <FitText
        slot={TEXT_SLOT}
        sceneId={sceneId}
        template="kinetic_quote"
        slotName="text"
        debug={debug}
        isGallery={isGallery}
        style={{
          textAlign: "center",
          color: palette.ink,
        }}
      >
        {words.map((word, idx) => {
          const clean = word.toLowerCase().replace(/[^\w]/g, "");
          const isEmphasized = emphasisSet.has(clean);

          // Stagger 2 frames per word
          const wordStartFrame = idx * 2;
          const wordOpacity = interpolate(
            clock.frame,
            [wordStartFrame, wordStartFrame + 6],
            [0, 1],
            {
              extrapolateLeft: "clamp",
              extrapolateRight: "clamp",
            }
          );
          const wordTranslateY = interpolate(
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
                margin: isEmphasized ? "0 0.42em" : "0 0.18em",
                opacity: wordOpacity,
                transform: `translateY(${wordTranslateY}px) scale(${isEmphasized ? 1.15 : 1.0})`,
                color: isEmphasized ? palette.highlight : palette.ink,
                transformOrigin: "bottom center",
              }}
            >
              {word}
            </span>
          );
        })}
      </FitText>

      {cast && (
        <div
          style={{
            marginTop: 40,
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            gap: 16,
          }}
        >
          {/* 120 px parametric avatar component */}
          <Avatar
            avatar={cast.avatar}
            size={120}
            color={castColor}
            expression="neutral"
          />

          <div
            style={{
              backgroundColor: castColor,
              borderRadius: 999,
              padding: "6px 20px",
              display: "inline-flex",
              alignItems: "center",
              justifyContent: "center",
              maxWidth: 600,
            }}
          >
            <FitText
              slot={ATTRIBUTION_SLOT}
              text={cast.name}
              sceneId={sceneId}
              template="kinetic_quote"
              slotName="attribution_name"
              debug={debug}
              isGallery={isGallery}
              style={{
                textAlign: "center",
                color: palette.bg,
                whiteSpace: "nowrap",
              }}
            />
          </div>
        </div>
      )}

    </div>
  );
};

