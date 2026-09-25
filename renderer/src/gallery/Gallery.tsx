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
import { characterIntroFixtures } from "./fixtures/character_intro";
import { comparisonFixtures } from "./fixtures/comparison";
import { dialogueFixtures } from "./fixtures/dialogue";
import { emotionBeatFixtures } from "./fixtures/emotion_beat";
import { iconListFixtures } from "./fixtures/icon_list";
import { kineticQuoteFixtures } from "./fixtures/kinetic_quote";
import { relationshipMapFixtures } from "./fixtures/relationship_map";
import { revealFixtures } from "./fixtures/reveal";
import { statCalloutFixtures } from "./fixtures/stat_callout";
import { textThreadFixtures } from "./fixtures/text_thread";
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
      hair_color: "brown",
      hair_style: "long",
      headwear: "none",
      skin: 1,
    },
    color: "#F4A261",
    name: "Rose",
  },
  c2: {
    avatar: {
      age: "adult",
      facial_hair: "none",
      glasses: false,
      hair_color: "black",
      hair_style: "short",
      headwear: "none",
      skin: 2,
    },
    color: "#E76F51",
    name: "Danny",
  },
  c3: {
    avatar: {
      age: "elder",
      facial_hair: "beard",
      glasses: true,
      hair_color: "gray",
      hair_style: "short",
      headwear: "none",
      skin: 0,
    },
    color: "#2A9D8F",
    name: "Walt",
  },
  c4: {
    avatar: {
      age: "adult",
      facial_hair: "none",
      glasses: false,
      hair_color: "blonde",
      hair_style: "ponytail",
      headwear: "none",
      skin: 1,
    },
    color: "#E9C46A",
    name: "Deb",
  },
  c5: {
    avatar: {
      age: "adult",
      facial_hair: "none",
      glasses: false,
      hair_color: "black",
      hair_style: "curly",
      headwear: "none",
      skin: 4,
    },
    color: "#9B5DE5",
    name: "Sofia",
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
  } else if (template === "character_intro") {
    props = characterIntroFixtures[variant] || characterIntroFixtures.typical;
  } else if (template === "dialogue") {
    props = dialogueFixtures[variant] || dialogueFixtures.typical;
  } else if (template === "text_thread") {
    props = textThreadFixtures[variant] || textThreadFixtures.typical;
  } else if (template === "emotion_beat") {
    props = emotionBeatFixtures[variant] || emotionBeatFixtures.typical;
  } else if (template === "relationship_map") {
    props = relationshipMapFixtures[variant] || relationshipMapFixtures.typical;
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
