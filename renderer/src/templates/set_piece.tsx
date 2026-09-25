import React from "react";
import { Img, interpolate, staticFile } from "remotion";
import { useSceneClock } from "../clock/SceneClockContext";
import { FitText, type FitTextSlot } from "../components/FitText";
import { Icon } from "../components/Icon";
import type { SetPieceProps, TimelineSceneTiming } from "../generated/contracts";
import { useSetPiece } from "../story/entities";
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

const CAPTION_SLOT: FitTextSlot = {
  font: "body",
  weight: 600,
  size_max: 40,
  size_min: 30,
  max_lines: 2,
  box_width: 880,
};

export interface SetPieceTemplateProps {
  sceneId: string;
  props: SetPieceProps;
  timing?: TimelineSceneTiming;
  debug?: boolean;
  isGallery?: boolean;
}

export const SetPiece: React.FC<SetPieceTemplateProps> = ({
  sceneId,
  props,
  debug = false,
  isGallery = false,
}) => {
  const clock = useSceneClock();
  const setPiece = useSetPiece(props.set_piece_id);

  const name = setPiece?.name || "Unknown Object";
  const icon = setPiece?.icon || "Package";
  const image = setPiece?.image;

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
      {image ? (
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
              image.startsWith("/") || image.startsWith("http")
                ? image
                : staticFile(
                    image.startsWith("job/") ? image : `job/${image}`
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
          {/* Bottom scrim 320 px (bg from 0% to 85% alpha) */}
          <div
            style={{
              position: "absolute",
              bottom: 0,
              left: 0,
              width: "100%",
              height: 320,
              background:
                "linear-gradient(to bottom, rgba(10, 15, 30, 0) 0%, rgba(10, 15, 30, 0.85) 100%)",
            }}
          />
        </div>
      ) : (
        /* Fallback: set piece icon at 360 px in a 560 px bgRaised circle centred at (540, 560) */
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
          <Icon name={icon} size={360} weight="fill" color={palette.highlight} />
        </div>
      )}

      {/* Name bottom-aligned at y 1080, left x 100; caption directly above name */}
      <div
        style={{
          position: "absolute",
          left: 100,
          top: 840,
          width: 880,
          height: 240,
          display: "flex",
          flexDirection: "column",
          justifyContent: "flex-end",
          opacity: textOpacity,
          transform: `translateY(${textY}px)`,
        }}
      >
        {props.caption && (
          <div style={{ marginBottom: 12 }}>
            <FitText
              slot={CAPTION_SLOT}
              text={props.caption}
              sceneId={sceneId}
              template="set_piece"
              slotName="caption"
              debug={debug}
              isGallery={isGallery}
              style={{
                color: palette.inkMuted,
                fontWeight: 600,
              }}
            />
          </div>
        )}

        <div>
          <FitText
            slot={NAME_SLOT}
            text={name}
            sceneId={sceneId}
            template="set_piece"
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
