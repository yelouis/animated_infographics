import React from "react";
import { RemotionGlobalClock } from "../clock/remotion/RemotionGlobalClock";
import type { Timeline } from "../generated/contracts";
import { AudioLayer } from "./AudioLayer";
import { Background } from "./Background";
import { Captions } from "./Captions";
import { EntitiesProvider } from "./entities";
import { SceneLayer } from "./SceneLayer";

export const Story: React.FC<Timeline | { timeline: Timeline }> = (props) => {
  const timeline = "duration_frames" in props ? props : props.timeline;
  const durationFrames = timeline.duration_frames;
  const isSyncProbe = Boolean(timeline.debug?.sync_probe);

  return (
    <EntitiesProvider
      value={{
        cast: timeline.cast || {},
        places: timeline.places || {},
        setPieces: timeline.set_pieces || {},
      }}
    >
      <RemotionGlobalClock>
        {/* Layer 1: Background */}
        <Background />

        {/* Layer 2: Scenes */}
        <SceneLayer
          scenes={timeline.scenes || []}
          durationFrames={durationFrames}
          debug={isSyncProbe}
        />

        {/* Layer 3: Captions */}
        <Captions
          pages={timeline.captions?.pages || []}
          scenes={timeline.scenes || []}
        />

        {/* Layer 4: Audio */}
        {timeline.audio && (
          <AudioLayer
            audio={timeline.audio}
            durationFrames={durationFrames}
          />
        )}
      </RemotionGlobalClock>
    </EntitiesProvider>
  );
};
