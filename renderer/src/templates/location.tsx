import React from "react";
import { Img, interpolate, staticFile } from "remotion";
import { useSceneClock } from "../clock/SceneClockContext";
import { FitText, type FitTextSlot } from "../components/FitText";
import { Icon } from "../components/Icon";
import { ImageScrim } from "../components/ImageScrim";
import type { LocationProps, TimelineSceneTiming } from "../generated/contracts";
import { usePlace } from "../story/entities";
import { EASE_ENTER, EASE_EXIT } from "../theme/motion";
import { palette } from "../theme/palette";

const NAME_SLOT: FitTextSlot = {
  font: "display",
  weight: 800,
  size_max: 72,
  size_min: 48,
  max_lines: 2,
  box_width: 880,
};

const ERA_SLOT: FitTextSlot = {
  font: "display",
  weight: 800,
  size_max: 44,
  size_min: 32,
  max_lines: 1,
  box_width: 240,
};

export interface LocationTemplateProps {
  sceneId: string;
  props: LocationProps;
  timing?: TimelineSceneTiming;
  debug?: boolean;
  isGallery?: boolean;
}

export const Location: React.FC<LocationTemplateProps> = ({
  sceneId,
  props,
  debug = false,
  isGallery = false,
}) => {
  const clock = useSceneClock();
  const place = usePlace(props.place_id);

  const placeName = place?.name || "Unknown Location";
  const placeIcon = place?.icon || "MapPin";
  const placeImage = place?.image;

  // Scene progress for Ken Burns
  const sceneProgress =
    clock.sceneFrames > 0 ? clock.frame / clock.sceneFrames : 0;

  // Exit transforms
  const exitOpacity = interpolate(clock.exitProgress, [0, 1], [1, 0]);
  const exitY = interpolate(clock.exitProgress, [0, 1], [0, -24], {
    easing: EASE_EXIT,
  });

  // Entrance: image/panel fades in over 12 frames
  const mediaOpacity = interpolate(clock.frame, [0, 12], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // Hold: Ken Burns scale 1.00 -> 1.08, pan x -20 -> +20 across scene
  const kbScale = interpolate(sceneProgress, [0, 1], [1.0, 1.08]);
  const kbPanX = interpolate(sceneProgress, [0, 1], [-20, 20]);

  // Name entrance: slides up at frame 8
  const textOpacity = interpolate(clock.frame, [8, 14], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const textY = interpolate(clock.frame, [8, 14], [20, 0], {
    easing: EASE_ENTER,
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // Era stamp entrance: frame 10
  const eraOpacity = interpolate(clock.frame, [10, 16], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const eraScale = interpolate(clock.frame, [10, 16], [0.8, 1.0], {
    easing: EASE_ENTER,
    extrapolateLeft: "clamp",
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
      {/* Visual content: Image or Fallback Circle */}
      {placeImage ? (
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
            src={
              placeImage.startsWith("/") || placeImage.startsWith("http")
                ? placeImage
                : staticFile(
                    placeImage.startsWith("job/")
                      ? placeImage
                      : `job/${placeImage}`
                  )
            }
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
        /* Fallback: place icon at 360 px in a 560 px bgRaised circle centred at (540, 560) */
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
            opacity: mediaOpacity,
            transform: `scale(${kbScale}) translateX(${kbPanX}px)`,
            transformOrigin: "center center",
          }}
        >
          <Icon
            name={placeIcon}
            size={360}
            weight="fill"
            color={palette.highlight}
          />
        </div>
      )}

      {/* Era stamp: highlight text on a bgDeep pill, rotated -6 deg, centred at (880, 220) */}
      {props.era_label && (
        <div
          style={{
            position: "absolute",
            left: 744,
            top: 190,
            width: 272,
            height: 60,
            borderRadius: 30,
            backgroundColor: palette.bgDeep,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            padding: "0 16px",
            boxSizing: "border-box",
            border: `2px solid ${palette.highlight}`,
            transform: `rotate(-6deg) scale(${eraScale})`,
            opacity: eraOpacity,
            boxShadow: "0 8px 24px rgba(0, 0, 0, 0.4)",
          }}
        >
          <FitText
            slot={ERA_SLOT}
            text={props.era_label}
            sceneId={sceneId}
            template="location"
            slotName="era"
            debug={debug}
            isGallery={isGallery}
            style={{
              color: palette.highlight,
              fontWeight: 800,
              textAlign: "center",
            }}
          />
        </div>
      )}

      {/* place name bottom-aligned at y 1080; no caption (removed in D1) */}
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

        <div>
          <FitText
            slot={NAME_SLOT}
            text={placeName}
            sceneId={sceneId}
            template="location"
            slotName="name"
            debug={debug}
            isGallery={isGallery}
            style={{
              color: palette.ink,
              fontWeight: 800,
            }}
          />
        </div>
      </div>
    </div>
  );
};
