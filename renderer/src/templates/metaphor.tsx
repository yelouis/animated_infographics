import React from "react";
import { Img, interpolate, spring, staticFile } from "remotion";
import { useSceneClock } from "../clock/SceneClockContext";
import { Avatar } from "../components/Avatar";
import { FitText, type FitTextSlot } from "../components/FitText";
import { ImageScrim } from "../components/ImageScrim";
import type { MetaphorProps, TimelineSceneTiming } from "../generated/contracts";
import { useCast, useSetPiece } from "../story/entities";
import { EASE_ENTER, EASE_EXIT, SPRING_POP_CONFIG } from "../theme/motion";
import { palette } from "../theme/palette";

const LABEL_SLOT: FitTextSlot = {
  font: "display",
  weight: 800,
  size_max: 72,
  size_min: 48,
  max_lines: 2,
  box_width: 880,
};

const NO_IMAGE_LABEL_SLOT: FitTextSlot = {
  font: "display",
  weight: 800,
  size_max: 64,
  size_min: 40,
  max_lines: 2,
  box_width: 480,
};

export interface MetaphorTemplateProps {
  sceneId: string;
  props: MetaphorProps;
  timing?: TimelineSceneTiming;
  debug?: boolean;
  isGallery?: boolean;
}

export const Metaphor: React.FC<MetaphorTemplateProps> = ({
  sceneId,
  props,
  debug = false,
  isGallery = false,
}) => {
  const clock = useSceneClock();
  const setPiece = useSetPiece(props.image_entity);

  // Resolve image from set_pieces context or direct entity path
  let rawImage: string | null = setPiece?.image || null;
  if (!rawImage && props.image_entity && props.image_entity !== "none" && props.image_entity !== "") {
    if (props.image_entity.startsWith("/") || props.image_entity.startsWith("http") || props.image_entity.includes(".")) {
      rawImage = props.image_entity;
    }
  }

  const imageUrl = rawImage
    ? rawImage.startsWith("/") || rawImage.startsWith("http")
      ? rawImage
      : staticFile(
          rawImage.startsWith("job/") ? rawImage : `job/${rawImage}`
        )
    : null;

  // Scene progress for Ken Burns
  const sceneProgress =
    clock.sceneFrames > 0 ? clock.frame / clock.sceneFrames : 0;

  // Exit transforms
  const exitOpacity = interpolate(clock.exitProgress, [0, 1], [1, 0]);
  const exitY = interpolate(clock.exitProgress, [0, 1], [0, -24], {
    easing: EASE_EXIT,
  });

  // Entrance: media panel fades in over 12 frames
  const mediaOpacity = interpolate(clock.frame, [0, 12], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // Hold: Ken Burns scale 1.00 -> 1.08, pan x -20 -> +20 across scene
  const kbScale = interpolate(sceneProgress, [0, 1], [1.0, 1.08]);
  const kbPanX = interpolate(sceneProgress, [0, 1], [-20, 20]);

  // Label entrance: slides up at frame 8
  const textOpacity = interpolate(clock.frame, [8, 14], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const textY = interpolate(clock.frame, [8, 14], [20, 0], {
    easing: EASE_ENTER,
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const castIds = props.cast_ids || [];

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
      {imageUrl ? (
        /* Image: 960x960 at (60, 160), radius 32, with location scrim and Ken Burns */
        <div
          style={{
            position: "absolute",
            left: 60,
            top: 160,
            width: 960,
            height: 960,
            borderRadius: 32,
            overflow: "hidden",
            opacity: mediaOpacity,
            backgroundColor: palette.bgRaised,
          }}
        >
          <Img
            src={imageUrl}
            style={{
              width: "100%",
              height: "100%",
              objectFit: "cover",
              transform: `scale(${kbScale}) translateX(${kbPanX}px)`,
              transformOrigin: "center center",
            }}
          />
          <ImageScrim />
        </div>
      ) : (
        /* No image fallback: label centred in 560 px bgRaised circle centred at (540, 560) */
        <div
          style={{
            position: "absolute",
            left: 260,
            top: 280,
            width: 560,
            height: 560,
            borderRadius: "50%",
            backgroundColor: palette.bgRaised,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            padding: 40,
            boxSizing: "border-box",
            opacity: mediaOpacity,
            transform: `scale(${kbScale}) translateX(${kbPanX}px)`,
            transformOrigin: "center center",
          }}
        >
          {props.label && (
            <FitText
              slot={NO_IMAGE_LABEL_SLOT}
              text={props.label}
              sceneId={sceneId}
              template="metaphor"
              slotName="label"
              debug={debug}
              isGallery={isGallery}
              style={{
                color: palette.ink,
                fontWeight: 800,
                textAlign: "center",
              }}
            />
          )}
        </div>
      )}

      {/* Up to two cast avatars, 200 px, centred at (240, 1000) and (840, 1000), 10 px ring in cast colour */}
      {imageUrl &&
        castIds.slice(0, 2).map((castId, idx) => {
          const xCenter = idx === 0 ? 240 : 840;
          const entranceStartFrame = idx === 0 ? 6 : 10;
          const avatarSpring =
            clock.frame < entranceStartFrame
              ? 0
              : spring({
                  frame: clock.frame - entranceStartFrame,
                  fps: 30,
                  config: SPRING_POP_CONFIG,
                });

          return (
            <AvatarRing
              key={castId}
              castId={castId}
              xCenter={xCenter}
              yCenter={1000}
              springProgress={avatarSpring}
            />
          );
        })}

      {/* Label in location name slot: bottom-aligned at y 1080, left x 100, width 880 (when image is present) */}
      {imageUrl && props.label && (
        <div
          style={{
            position: "absolute",
            left: 100,
            top: 760,
            width: 880,
            height: 320,
            display: "flex",
            flexDirection: "column",
            justifyContent: "flex-end",
            opacity: textOpacity,
            transform: `translateY(${textY}px)`,
          }}
        >
          <FitText
            slot={LABEL_SLOT}
            text={props.label}
            sceneId={sceneId}
            template="metaphor"
            slotName="label"
            debug={debug}
            isGallery={isGallery}
            style={{
              color: palette.ink,
              fontWeight: 800,
              textAlign: "left",
            }}
          />
        </div>
      )}
    </div>
  );
};

interface AvatarRingProps {
  castId: string;
  xCenter: number;
  yCenter: number;
  springProgress: number;
}

const AvatarRing: React.FC<AvatarRingProps> = ({
  castId,
  xCenter,
  yCenter,
  springProgress,
}) => {
  const cast = useCast(castId);
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

  const left = xCenter - 100;
  const top = yCenter - 100;

  return (
    <div
      style={{
        position: "absolute",
        left,
        top,
        width: 200,
        height: 200,
        borderRadius: "50%",
        border: `10px solid ${castColor}`,
        boxSizing: "border-box",
        overflow: "hidden",
        backgroundColor: palette.bgRaised,
        boxShadow: "0 8px 24px rgba(0, 0, 0, 0.4)",
        transform: `scale(${springProgress})`,
        opacity: Math.min(1, Math.max(0, springProgress)),
      }}
    >
      <Avatar
        avatar={avatarConfig}
        color={castColor}
        size={180}
        style={{
          position: "absolute",
          left: 0,
          top: 0,
        }}
      />
    </div>
  );
};
