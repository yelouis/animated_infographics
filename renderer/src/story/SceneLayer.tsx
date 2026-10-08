import React from "react";
import { RemotionSceneClock } from "../clock/remotion/RemotionSceneClock";
import type { Scenes } from "../generated/contracts";
import { getTemplateComponent } from "../templates";
import { EXIT_FRAMES } from "../theme/motion";
import { OverlayLayer } from "./OverlayLayer";
import { SyncProbe } from "./SyncProbe";

export interface SceneLayerProps {
  scenes: Scenes;
  durationFrames: number;
  debug?: boolean;
}

export const SceneLayer: React.FC<SceneLayerProps> = ({
  scenes,
  durationFrames,
  debug = false,
}) => {
  return (
    <div
      style={{
        position: "absolute",
        top: 0,
        left: 0,
        width: 1080,
        height: 1920,
      }}
    >
      {scenes.map((scene, idx) => {
        const startFrame = scene.start_frame;
        const sceneFrames = scene.end_frame - scene.start_frame;
        const totalDuration =
          Math.min(scene.end_frame + EXIT_FRAMES, durationFrames) - startFrame;
        const Component = getTemplateComponent(scene.template || "placeholder");

        return (
          <RemotionSceneClock
            key={scene.id || `scene-${idx}`}
            startFrame={startFrame}
            durationFrames={totalDuration}
            sceneFrames={sceneFrames}
          >
            <div
              style={{
                position: "absolute",
                top: 0,
                left: 0,
                width: 1080,
                height: 1920,
                zIndex: idx,
              }}
            >
              <Component
                sceneId={scene.id}
                props={scene.props}
                timing={scene.timing}
                debug={debug}
                overlays={scene.overlays}
              />
              {scene.overlays && scene.overlays.length > 0 && (
                <OverlayLayer
                  overlays={scene.overlays}
                  sceneId={scene.id}
                  debug={debug}
                />
              )}
              {debug && <SyncProbe sceneIndex={idx} />}
            </div>
          </RemotionSceneClock>
        );
      })}
    </div>
  );
};
