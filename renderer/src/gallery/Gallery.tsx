import React from "react";
import { RemotionGlobalClock } from "../clock/remotion/RemotionGlobalClock";
import { RemotionSceneClock } from "../clock/remotion/RemotionSceneClock";
import type { TimelineCastMember } from "../generated/contracts";
import { Background } from "../story/Background";
import { EntitiesProvider } from "../story/entities";
import { getTemplateComponent } from "../templates";
import { kineticQuoteFixtures } from "./fixtures/kinetic_quote";

export interface GalleryProps {
  template: string;
  variant: "min" | "typical" | "max";
}

const GALLERY_CAST: Record<string, TimelineCastMember> = {
  c1: {
    avatar: {
      age: "adult",
      facial_hair: "none",
      glasses: false,
      hair_color: "black",
      hair_style: "short",
      headwear: "none",
      skin: 1,
    },
    color: "#F4A261",
    name: "Robert Frost",
  },
};

export const Gallery: React.FC<GalleryProps> = ({ template, variant }) => {
  let props: unknown = {};
  if (template === "kinetic_quote") {
    props = kineticQuoteFixtures[variant] || kineticQuoteFixtures.typical;
  }

  const Component = getTemplateComponent(template);

  return (
    <EntitiesProvider
      value={{
        cast: GALLERY_CAST,
        places: {},
        setPieces: {},
      }}
    >
      <RemotionGlobalClock>
        <Background />
        <RemotionSceneClock
          startFrame={0}
          durationFrames={150}
          sceneFrames={150}
        >
          <div
            style={{
              position: "absolute",
              top: 0,
              left: 0,
              width: 1080,
              height: 1920,
            }}
          >
            <Component
              sceneId={`gallery-${template}-${variant}`}
              props={props}
              isGallery={true}
            />
          </div>
        </RemotionSceneClock>
      </RemotionGlobalClock>
    </EntitiesProvider>
  );
};
