import React from "react";
import { Img, interpolate, staticFile } from "remotion";
import { useSceneClock } from "../clock/SceneClockContext";
import { FitText, type FitTextSlot } from "../components/FitText";
import { Icon } from "../components/Icon";
import { ImageScrim } from "../components/ImageScrim";
import type { CallbackProps, TimelineSceneTiming } from "../generated/contracts";
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

export interface CallbackTemplateProps {
  sceneId: string;
  props: CallbackProps;
  timing?: TimelineSceneTiming;
  debug?: boolean;
  isGallery?: boolean;
}

export const Callback: React.FC<CallbackTemplateProps> = ({
  sceneId,
  props,
  timing,
  debug = false,
  isGallery = false,
}) => {
  const clock = useSceneClock();
  const setPiece = useSetPiece(props.set_piece_id);

  const setPieceImage = setPiece?.image;
  const motifIcon = props.icon || setPiece?.icon || "Sparkle";

  // Scene progress for continuous zoom 1.00 -> 1.12
  const sceneProgress =
    clock.sceneFrames > 0 ? clock.frame / clock.sceneFrames : 0;
  const zoom = interpolate(sceneProgress, [0, 1], [1.0, 1.12]);

  // Exit transforms
  const exitOpacity = interpolate(clock.exitProgress, [0, 1], [1, 0]);
  const exitY = interpolate(clock.exitProgress, [0, 1], [0, -24], {
    easing: EASE_EXIT,
  });

  // Entrance: media fades in over 12 frames
  const mediaOpacity = interpolate(clock.frame, [0, 12], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // Pulse for set piece highlight ring (period 45 frames)
  const ringPulse = 0.7 + 0.3 * Math.sin((clock.frame * 2 * Math.PI) / 45);

  // Label entrance at frame 8
  const textOpacity = interpolate(clock.frame, [8, 14], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const textY = interpolate(clock.frame, [8, 14], [20, 0], {
    easing: EASE_ENTER,
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // "Seen before" dots row: 24 px dots centred at y 1140 with 16 px gaps
  const itemFrames = timing?.item_frames ?? [];
  const dotCount = itemFrames.length;

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
      {setPieceImage ? (
        /* Motif with a set piece: that set piece's illustration fills the image box with a 12 px highlight ring pulsing */
        <div
          style={{
            position: "absolute",
            left: 60,
            top: 160,
            width: 960,
            height: 960,
            borderRadius: 32,
            border: `12px solid ${palette.highlight}`,
            boxSizing: "border-box",
            overflow: "hidden",
            opacity: mediaOpacity,
            backgroundColor: palette.bgRaised,
            boxShadow: `0 0 ${24 * ringPulse}px ${palette.highlight}`,
          }}
        >
          <Img
            src={
              setPieceImage.startsWith("/") || setPieceImage.startsWith("http")
                ? setPieceImage
                : staticFile(
                    setPieceImage.startsWith("job/")
                      ? setPieceImage
                      : `job/${setPieceImage}`
                  )
            }
            style={{
              width: "100%",
              height: "100%",
              objectFit: "cover",
              transform: `scale(${zoom})`,
              transformOrigin: "center center",
            }}
          />
          <ImageScrim />
        </div>
      ) : (
        /* Otherwise: the motif's icon, 360 px, in a 560 px highlight circle centred at (540, 560), drawn navy */
        <div
          style={{
            position: "absolute",
            left: 260,
            top: 280,
            width: 560,
            height: 560,
            borderRadius: "50%",
            backgroundColor: palette.highlight,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            opacity: mediaOpacity,
            transform: `scale(${zoom})`,
            transformOrigin: "center center",
            boxShadow: "0 12px 36px rgba(0, 0, 0, 0.4)",
          }}
        >
          <Icon
            name={motifIcon}
            size={360}
            color={palette.bgDeep}
            weight="fill"
          />
        </div>
      )}

      {/* Label in name slot: bottom-aligned at y 1080, left x 100, width 880 */}
      {props.label && (
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
            slot={NAME_SLOT}
            text={props.label}
            sceneId={sceneId}
            template="callback"
            slotName="label"
            debug={debug}
            isGallery={isGallery}
            style={{
              color: palette.ink,
              fontWeight: 800,
              textAlign: "center",
            }}
          />
        </div>
      )}

      {/* "Seen before" dots row: 24 px dots centred at y 1140 with 16 px gaps */}
      {dotCount > 0 && (
        <div
          style={{
            position: "absolute",
            left: 0,
            top: 1128,
            width: 1080,
            height: 24,
            display: "flex",
            justifyContent: "center",
            alignItems: "center",
            gap: 16,
            opacity: textOpacity,
          }}
        >
          {Array.from({ length: dotCount }).map((_, idx) => {
            const itemFrame = itemFrames[idx] ?? (15 + idx * 12);
            const isFilled = clock.frame >= itemFrame;
            const popProgress =
              clock.frame < itemFrame
                ? 0
                : interpolate(clock.frame, [itemFrame, itemFrame + 4], [0, 1], {
                    extrapolateRight: "clamp",
                  });
            const popScale = 1.0 + 0.3 * Math.sin(popProgress * Math.PI);

            return (
              <div
                key={idx}
                style={{
                  width: 24,
                  height: 24,
                  borderRadius: "50%",
                  border: `3px solid ${palette.highlight}`,
                  backgroundColor: isFilled ? palette.highlight : "transparent",
                  boxSizing: "border-box",
                  transform: `scale(${popScale})`,
                  boxShadow: isFilled
                    ? `0 0 10px ${palette.highlight}`
                    : "none",
                }}
              />
            );
          })}
        </div>
      )}
    </div>
  );
};
