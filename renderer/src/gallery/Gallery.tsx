import React from "react";
import { RemotionGlobalClock } from "../clock/remotion/RemotionGlobalClock";
import { RemotionSceneClock } from "../clock/remotion/RemotionSceneClock";
import type { TimelineCastMember } from "../generated/contracts";
import { Background } from "../story/Background";
import { EntitiesProvider } from "../story/entities";
import { getTemplateComponent } from "../templates";
import { getDefaultTiming } from "../story/timing";
import { AvatarSheet } from "./AvatarSheet";
import { avatarSheetFixtures } from "./fixtures/avatar_sheet";
import { causeEffectFixtures } from "./fixtures/cause_effect";
import { comparisonFixtures } from "./fixtures/comparison";
import { iconListFixtures } from "./fixtures/icon_list";
import { kineticQuoteFixtures } from "./fixtures/kinetic_quote";
import { revealFixtures } from "./fixtures/reveal";
import { statCalloutFixtures } from "./fixtures/stat_callout";
import { titleCardFixtures } from "./fixtures/title_card";

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
  } else if (template === "avatar_sheet") {
    props = avatarSheetFixtures[variant] || avatarSheetFixtures.typical;
  } else if (template === "title_card") {
    props = titleCardFixtures[variant] || titleCardFixtures.typical;
  } else if (template === "stat_callout") {
    props = statCalloutFixtures[variant] || statCalloutFixtures.typical;
  } else if (template === "icon_list") {
    props = iconListFixtures[variant] || iconListFixtures.typical;
  } else if (template === "reveal") {
    props = revealFixtures[variant] || revealFixtures.typical;
  } else if (template === "cause_effect") {
    props = causeEffectFixtures[variant] || causeEffectFixtures.typical;
  } else if (template === "comparison") {
    props = comparisonFixtures[variant] || comparisonFixtures.typical;
  }

  const timing = getDefaultTiming(template, props, 150);

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const Component = template === "avatar_sheet" ? (AvatarSheet as unknown as React.FC<any>) : getTemplateComponent(template);

  return (
    <EntitiesProvider
      value={{
        cast: GALLERY_CAST,
        places: {},
        setPieces: {},
      }}
    >
      <RemotionGlobalClock>
        <Background static={true} />
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
              timing={timing}
              isGallery={true}
            />
          </div>
        </RemotionSceneClock>
      </RemotionGlobalClock>
    </EntitiesProvider>
  );
};
