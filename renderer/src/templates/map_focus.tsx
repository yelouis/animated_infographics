import React, { useMemo } from "react";
import { interpolate } from "remotion";
import { useSceneClock } from "../clock/SceneClockContext";
import { FitText, type FitTextSlot } from "../components/FitText";
import { MapView, type MapMarker } from "../components/MapView";
import type { MapFocusProps, TimelineSceneTiming } from "../generated/contracts";
import { usePlace } from "../story/entities";
import { EASE_ENTER, EASE_EXIT } from "../theme/motion";
import { palette } from "../theme/palette";

const MARKER_LABEL_SLOT: FitTextSlot = {
  font: "display",
  weight: 800,
  size_max: 40,
  size_min: 30,
  max_lines: 1,
  box_width: 360,
};

const CAPTION_SLOT: FitTextSlot = {
  font: "body",
  weight: 600,
  size_max: 40,
  size_min: 30,
  max_lines: 2,
  box_width: 900,
};

export interface MapFocusTemplateProps {
  sceneId: string;
  props: MapFocusProps;
  timing?: TimelineSceneTiming;
  debug?: boolean;
  isGallery?: boolean;
}

export const MapFocus: React.FC<MapFocusTemplateProps> = ({
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

  // Map panel entrance: fades in over 10 frames
  const mapOpacity = interpolate(clock.frame, [0, 10], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // Hold motion: subtle camera zoom (1.00 -> 1.04) across the scene
  const mapScale = interpolate(
    clock.frame,
    [0, Math.max(1, clock.sceneFrames)],
    [1.0, 1.04],
    { extrapolateRight: "clamp" }
  );

  // Caption entrance at frame 12
  const captionOpacity = interpolate(clock.frame, [12, 18], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const captionY = interpolate(clock.frame, [12, 18], [16, 0], {
    easing: EASE_ENTER,
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const itemFrames = timing?.item_frames || [];

  // Resolve marker coordinates using usePlace hook
  // In React we can map over markers calling usePlace
  const markers = props.markers || [];
  const p0 = usePlace(markers[0]?.place_id);
  const p1 = usePlace(markers[1]?.place_id);
  const p2 = usePlace(markers[2]?.place_id);
  const places = [p0, p1, p2];

  const resolvedMarkers: MapMarker[] = useMemo(() => {
    return markers.map((m, idx) => {
      const place = places[idx];
      return {
        placeId: m.place_id,
        label: m.label,
        lat: place?.lat ?? 0,
        lon: place?.lon ?? 0,
      };
    });
  }, [markers, places]);

  // Render marker label with FitText
  const renderMarkerLabel = (
    m: MapMarker & { x: number; y: number },
    idx: number
  ) => {
    const startFrame = itemFrames[idx] ?? idx * 12;
    const labelOpacity = interpolate(
      clock.frame,
      [startFrame, startFrame + 6],
      [0, 1],
      {
        extrapolateLeft: "clamp",
        extrapolateRight: "clamp",
      }
    );

    return (
      <div
        style={{
          backgroundColor: palette.bgRaised,
          borderRadius: 20,
          padding: "6px 16px",
          boxShadow: "0 4px 16px rgba(0, 0, 0, 0.4)",
          border: `1.5px solid ${palette.bgDeep}`,
          maxWidth: 360,
          opacity: labelOpacity,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        <FitText
          slot={MARKER_LABEL_SLOT}
          text={m.label}
          sceneId={sceneId}
          template="map_focus"
          slotName="marker_label"
          debug={debug}
          isGallery={isGallery}
          style={{
            color: palette.ink,
            fontWeight: 800,
            whiteSpace: "nowrap",
          }}
        />
      </div>
    );
  };

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
      {/* Map panel (60, 160) to (1020, 1060), width 960, height 900, radius 32 */}
      <div
        style={{
          position: "absolute",
          left: 60,
          top: 160,
          width: 960,
          height: 900,
          borderRadius: 32,
          overflow: "hidden",
          opacity: mapOpacity,
        }}
      >
        <div
          style={{
            width: "100%",
            height: "100%",
            transform: `scale(${mapScale})`,
            transformOrigin: "center center",
          }}
        >
          <MapView
            region={props.region}
            markers={resolvedMarkers}
            path={props.path}
            width={960}
            height={900}
            radius={32}
            frame={clock.frame}
            renderMarkerLabel={renderMarkerLabel}
          />
        </div>
      </div>

      {/* Caption below panel at y 1090 */}
      {props.caption && (
        <div
          style={{
            position: "absolute",
            left: 90,
            top: 1090,
            width: 900,
            display: "flex",
            justifyContent: "center",
            opacity: captionOpacity,
            transform: `translateY(${captionY}px)`,
          }}
        >
          <FitText
            slot={CAPTION_SLOT}
            text={props.caption}
            sceneId={sceneId}
            template="map_focus"
            slotName="caption"
            debug={debug}
            isGallery={isGallery}
            style={{
              color: palette.ink,
              fontWeight: 600,
              textAlign: "center",
            }}
          />
        </div>
      )}
    </div>
  );
};
