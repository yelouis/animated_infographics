import React from "react";
import { interpolate } from "remotion";
import { useSceneClock } from "../clock/SceneClockContext";
import { Avatar, type AvatarExpression } from "../components/Avatar";
import { FitText, type FitTextSlot } from "../components/FitText";
import { Icon } from "../components/Icon";
import type { EmotionBeatProps, TimelineSceneTiming } from "../generated/contracts";
import { useCast } from "../story/entities";
import { EASE_EXIT } from "../theme/motion";
import { palette } from "../theme/palette";

const CAPTION_SLOT: FitTextSlot = {
  font: "display",
  weight: 800,
  size_max: 64,
  size_min: 44,
  max_lines: 2,
  box_width: 900,
};

const GLYPH_MAP: Record<string, string> = {
  happy: "Smiley",
  sad: "SmileySad",
  angry: "SmileyAngry",
  shocked: "ExclamationMark",
  confused: "Question",
  smug: "SmileyWink",
  nervous: "SmileyNervous",
};

export interface EmotionBeatTemplateProps {
  sceneId: string;
  props: EmotionBeatProps;
  timing?: TimelineSceneTiming;
  debug?: boolean;
  isGallery?: boolean;
}

export const EmotionBeat: React.FC<EmotionBeatTemplateProps> = ({
  sceneId,
  props,
  debug = false,
  isGallery = false,
}) => {
  const clock = useSceneClock();
  const cast = useCast(props.cast_id);

  const castColor = cast?.color || palette.castSlots[0];
  const avatarConfig = cast?.avatar || {
    age: "adult",
    facial_hair: "none",
    glasses: false,
    hair_color: "brown",
    hair_style: "short",
    headwear: "none",
    skin: 1,
  };

  // Exit transforms
  const exitOpacity = interpolate(clock.exitProgress, [0, 1], [1, 0]);
  const exitY = interpolate(clock.exitProgress, [0, 1], [0, -24], {
    easing: EASE_EXIT,
  });

  // Avatar springs in at frame 0
  const avatarScale = interpolate(clock.frame, [0, 8, 14], [0, 1.15, 1], {
    extrapolateRight: "clamp",
  });
  const avatarOpacity = interpolate(clock.frame, [0, 6], [0, 1], {
    extrapolateRight: "clamp",
  });

  // Glyph bobs 8 px, period 36 frames
  const glyphBobY = Math.sin((clock.frame / 36) * 2 * Math.PI) * 8;
  const glyphScale = interpolate(clock.frame, [4, 12], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // Hold motion based on emotion
  let holdTransform = "";
  if (props.emotion === "angry") {
    const shake = Math.sin(clock.frame * 2.5) * 2;
    holdTransform = `translateX(${shake}px)`;
  } else if (props.emotion === "sad") {
    const sinkY = interpolate(
      clock.frame,
      [0, Math.max(1, clock.sceneFrames)],
      [0, 10],
      { extrapolateRight: "clamp" }
    );
    holdTransform = `translateY(${sinkY}px)`;
  } else {
    const floatY = Math.sin((clock.frame / 60) * 2 * Math.PI) * 4;
    holdTransform = `translateY(${floatY}px)`;
  }

  const iconName = GLYPH_MAP[props.emotion] || "Smiley";

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
      {/* Avatar 520 px, expression = emotion, centred at x 540, top y 200, ring in cast colour */}
      <div
        style={{
          position: "absolute",
          left: 280,
          top: 200,
          width: 520,
          height: 520,
          opacity: avatarOpacity,
          transform: `scale(${avatarScale}) ${holdTransform}`,
          transformOrigin: "center center",
        }}
      >
        <div
          style={{
            position: "relative",
            width: 520,
            height: 520,
            borderRadius: "50%",
            border: `12px solid ${castColor}`,
            boxSizing: "border-box",
            overflow: "hidden",
            backgroundColor: palette.bgRaised,
          }}
        >
          <Avatar
            avatar={avatarConfig}
            color={castColor}
            size={496}
            expression={props.emotion as AvatarExpression}
            style={{
              position: "absolute",
              left: 0,
              top: 0,
            }}
          />
        </div>
      </div>

      {/* Emotion glyph 140 px at (800, 220) */}
      <div
        style={{
          position: "absolute",
          left: 730,
          top: 150,
          width: 140,
          height: 140,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          transform: `translateY(${glyphBobY}px) scale(${glyphScale})`,
          filter: "drop-shadow(0 8px 16px rgba(0,0,0,0.35))",
        }}
      >
        <Icon name={iconName} size={140} color={palette.highlight} />
      </div>

      {/* Caption top y 800 */}
      {props.caption && (
        <div
          style={{
            position: "absolute",
            left: 90,
            top: 800,
            width: 900,
            display: "flex",
            justifyContent: "center",
          }}
        >
          <FitText
            slot={CAPTION_SLOT}
            text={props.caption}
            sceneId={sceneId}
            template="emotion_beat"
            slotName="caption"
            debug={debug}
            isGallery={isGallery}
            style={{
              textAlign: "center",
              color: palette.ink,
            }}
          />
        </div>
      )}
    </div>
  );
};
