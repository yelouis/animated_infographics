import React from "react";
import { interpolate } from "remotion";
import { useSceneClock } from "../clock/SceneClockContext";
import { Avatar } from "../components/Avatar";
import { FitText, type FitTextSlot } from "../components/FitText";
import type { CharacterIntroProps, TimelineSceneTiming } from "../generated/contracts";
import { useCast } from "../story/entities";
import { EASE_ENTER, EASE_EXIT } from "../theme/motion";
import { palette } from "../theme/palette";

const NAME_SLOT: FitTextSlot = {
  font: "display",
  weight: 800,
  size_max: 96,
  size_min: 64,
  max_lines: 1,
  box_width: 900,
};

const DESCRIPTOR_SLOT: FitTextSlot = {
  font: "body",
  weight: 600,
  size_max: 44,
  size_min: 32,
  max_lines: 2,
  box_width: 860,
};

export interface CharacterIntroTemplateProps {
  sceneId: string;
  props: CharacterIntroProps;
  timing?: TimelineSceneTiming;
  debug?: boolean;
  isGallery?: boolean;
}

export const CharacterIntro: React.FC<CharacterIntroTemplateProps> = ({
  sceneId,
  props,
  debug = false,
  isGallery = false,
}) => {
  const clock = useSceneClock();
  const cast = useCast(props.cast_id);

  const castName = cast?.name || props.cast_id;
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

  // Name enters at frame 6
  const nameOpacity = interpolate(clock.frame, [6, 12], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const nameY = interpolate(clock.frame, [6, 12], [16, 0], {
    easing: EASE_ENTER,
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // Descriptor enters at frame 10
  const descOpacity = interpolate(clock.frame, [10, 16], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const descY = interpolate(clock.frame, [10, 16], [16, 0], {
    easing: EASE_ENTER,
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // Hold: avatar blinks at frames 45 and 135 (3 frames duration)
  const isBlinking =
    (clock.frame >= 45 && clock.frame <= 47) ||
    (clock.frame >= 135 && clock.frame <= 137);
  const eyeScaleY = isBlinking ? 0.1 : 1.0;

  // Hold motion: gentle breathing float across the scene (for hold-motion test between f60 and f105)
  const holdFloatY = Math.sin((clock.frame / 90) * 2 * Math.PI) * 5;

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
      {/* Avatar 440 px centred at x 540, top y 180, 12 px ring in cast colour */}
      <div
        style={{
          position: "absolute",
          left: 320,
          top: 180,
          width: 440,
          height: 440,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          opacity: avatarOpacity,
          transform: `scale(${avatarScale}) translateY(${holdFloatY}px)`,
          transformOrigin: "center center",
        }}
      >
        <div
          style={{
            position: "relative",
            width: 440,
            height: 440,
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
            size={416}
            eyeScaleY={eyeScaleY}
            style={{
              position: "absolute",
              left: 0,
              top: 0,
            }}
          />
        </div>
      </div>

      {/* Name top y 660, in the cast colour */}
      <div
        style={{
          position: "absolute",
          left: 90,
          top: 660,
          width: 900,
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          opacity: nameOpacity,
          transform: `translateY(${nameY}px)`,
        }}
      >
        <FitText
          slot={NAME_SLOT}
          text={castName}
          sceneId={sceneId}
          template="character_intro"
          slotName="name"
          debug={debug}
          isGallery={isGallery}
          style={{
            textAlign: "center",
            color: castColor,
          }}
        />

        {/* Descriptor 16 px below, ink */}
        <div
          style={{
            marginTop: 16,
            width: 860,
            opacity: descOpacity,
            transform: `translateY(${descY}px)`,
          }}
        >
          <FitText
            slot={DESCRIPTOR_SLOT}
            text={props.descriptor}
            sceneId={sceneId}
            template="character_intro"
            slotName="descriptor"
            debug={debug}
            isGallery={isGallery}
            style={{
              textAlign: "center",
              color: palette.ink,
            }}
          />
        </div>
      </div>
    </div>
  );
};
