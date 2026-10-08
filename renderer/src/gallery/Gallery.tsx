import React, { useMemo } from "react";
import { staticFile } from "remotion";
import { RemotionGlobalClock } from "../clock/remotion/RemotionGlobalClock";
import { RemotionSceneClock } from "../clock/remotion/RemotionSceneClock";
import type {
  TimelineCastMember,
  TimelinePlace,
  TimelineSceneTiming,
  TimelineSetPiece,
} from "../generated/contracts";
import { Background } from "../story/Background";
import { EntitiesProvider } from "../story/entities";
import { getTemplateComponent, type TemplateComponentProps } from "../templates";
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
import { locationFixtures } from "./fixtures/location";
import { mapFocusFixtures } from "./fixtures/map_focus";
import { relationshipMapFixtures } from "./fixtures/relationship_map";
import { revealFixtures } from "./fixtures/reveal";
import { setPieceFixtures } from "./fixtures/set_piece";
import { statCalloutFixtures } from "./fixtures/stat_callout";
import { textThreadFixtures } from "./fixtures/text_thread";
import { captionFixtures } from "./fixtures/captions";
import { timelineFixtures } from "./fixtures/timeline";
import { titleCardFixtures } from "./fixtures/title_card";
import { metaphorFixtures } from "./fixtures/metaphor";
import { callbackFixtures } from "./fixtures/callback";
import { sectionTitleFixtures } from "./fixtures/section_title";
import { overlaysFixtures } from "./fixtures/overlays";
import type { AllowedOverlayTemplate } from "../theme/overlayLayout";
import { OverlayLayer } from "../story/OverlayLayer";
import { Captions } from "../story/Captions";

export interface GalleryProps {
  template: string;
  variant: string;
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

const GALLERY_PLACES: Record<string, TimelinePlace> = {
  p1: {
    country_iso3: "USA",
    icon: "House",
    lat: 46.78,
    lon: -92.11,
    name: "Duluth",
    image: null,
  },
  p2: {
    country_iso3: "CAN",
    icon: "MapPin",
    lat: 48.38,
    lon: -89.25,
    name: "Thunder Bay",
    image: null,
  },
  p3: {
    country_iso3: "USA",
    icon: "Buildings",
    lat: 42.36,
    lon: -71.06,
    name: "Boston",
    image: null,
  },
  p4: {
    country_iso3: "CAN",
    icon: "Snowflake",
    lat: 75.0,
    lon: -75.0,
    name: "Arctic Outpost",
    image: null,
  },
  p5: {
    country_iso3: "ECU",
    icon: "Boat",
    lat: 0.0,
    lon: -78.46,
    name: "Equator Terminal",
    image: null,
  },

};


const GALLERY_SET_PIECES: Record<string, TimelineSetPiece> = {
  sp1: {
    icon: "Package",
    name: "Grandma Rose's Recipe Box",
    image: null,
  },
  sp2: {
    icon: "Drop",
    name: "Purity Distilling Tank",
    image: null,
  },
};

export const Gallery: React.FC<GalleryProps> = ({ template, variant }) => {
  const standardVariant = (variant === "worst" ? "typical" : variant) as "min" | "typical" | "max";
  let props: unknown = {};
  let customTiming: TimelineSceneTiming | undefined;
  if (template === "kinetic_quote") {
    props = kineticQuoteFixtures[standardVariant] || kineticQuoteFixtures.typical;
  } else if (template === "avatar_sheet") {
    props = avatarSheetFixtures[standardVariant] || avatarSheetFixtures.typical;
  } else if (template === "title_card") {
    props = titleCardFixtures[standardVariant] || titleCardFixtures.typical;
  } else if (template === "stat_callout") {
    props = statCalloutFixtures[standardVariant] || statCalloutFixtures.typical;
  } else if (template === "icon_list") {
    props = iconListFixtures[standardVariant] || iconListFixtures.typical;
  } else if (template === "reveal") {
    props = revealFixtures[standardVariant] || revealFixtures.typical;
  } else if (template === "cause_effect") {
    props = causeEffectFixtures[standardVariant] || causeEffectFixtures.typical;
  } else if (template === "comparison") {
    props = comparisonFixtures[standardVariant] || comparisonFixtures.typical;
  } else if (template === "character_intro") {
    props = characterIntroFixtures[standardVariant] || characterIntroFixtures.typical;
  } else if (template === "dialogue") {
    props = dialogueFixtures[standardVariant] || dialogueFixtures.typical;
  } else if (template === "text_thread") {
    props = textThreadFixtures[standardVariant] || textThreadFixtures.typical;
  } else if (template === "emotion_beat") {
    props = emotionBeatFixtures[standardVariant] || emotionBeatFixtures.typical;
  } else if (template === "relationship_map") {
    props = relationshipMapFixtures[standardVariant] || relationshipMapFixtures.typical;
  } else if (template === "location") {
    const locVariant = variant === "worst" ? "worst" : standardVariant;
    props = locationFixtures[locVariant] || locationFixtures.typical;
  } else if (template === "set_piece") {
    props = setPieceFixtures[standardVariant] || setPieceFixtures.typical;
  } else if (template === "map_focus") {
    props = mapFocusFixtures[standardVariant] || mapFocusFixtures.typical;
  } else if (template === "timeline") {
    props = timelineFixtures[standardVariant] || timelineFixtures.typical;
  } else if (template === "metaphor") {
    props = metaphorFixtures[standardVariant] || metaphorFixtures.typical;
  } else if (template === "callback") {
    const fixture = callbackFixtures[standardVariant] || callbackFixtures.typical;
    props = fixture.props;
    customTiming = fixture.timing;
  } else if (template === "section_title") {
    props =
      sectionTitleFixtures[standardVariant] || sectionTitleFixtures.typical;
  } else if (template === "overlays") {
    const overlayFixture =
      overlaysFixtures[variant as AllowedOverlayTemplate] ||
      overlaysFixtures.location;
    props = overlayFixture.props;
  }

  if (template === "captions") {
    const pages = captionFixtures[variant] || captionFixtures.long_active;
    return (
      <EntitiesProvider
        value={{
          cast: GALLERY_CAST,
          places: GALLERY_PLACES,
          setPieces: GALLERY_SET_PIECES,
        }}
      >
        <RemotionGlobalClock>
          <Background static={true} />
          <Captions pages={pages} scenes={[]} />
        </RemotionGlobalClock>
      </EntitiesProvider>
    );
  }

  const actualTemplate = template === "overlays" ? variant : template;
  const timing = customTiming ?? getDefaultTiming(actualTemplate, props, 150);

  const Component =
    template === "avatar_sheet"
      ? (AvatarSheet as unknown as React.FC<TemplateComponentProps>)
      : getTemplateComponent(actualTemplate);

  const places = useMemo(() => {
    if (variant === "worst") {
      return {
        ...GALLERY_PLACES,
        p1: {
          ...GALLERY_PLACES.p1,
          name: "MMMMWWWW Duluth Northern Historic Estate",
          image: staticFile("gallery/white.png"),
        },
      };
    }
    if (
      variant === "typical" ||
      (template === "overlays" && variant === "location")
    ) {
      return {
        ...GALLERY_PLACES,
        p1: {
          ...GALLERY_PLACES.p1,
          image: staticFile("gallery/duluth.png"),
        },
      };
    }
    return GALLERY_PLACES;
  }, [template, variant]);

  const setPieces = useMemo(() => {
    if (
      (template === "set_piece" && variant === "typical") ||
      (template === "metaphor" && (variant === "typical" || variant === "max")) ||
      (template === "callback" && variant === "max") ||
      (template === "overlays" && (variant === "set_piece" || variant === "metaphor"))
    ) {
      return {
        ...GALLERY_SET_PIECES,
        sp1: {
          ...GALLERY_SET_PIECES.sp1,
          image: staticFile("gallery/recipe_box.png"),
        },
      };
    }
    return GALLERY_SET_PIECES;
  }, [template, variant]);

  const currentOverlays =
    template === "overlays"
      ? (
          overlaysFixtures[variant as AllowedOverlayTemplate] ||
          overlaysFixtures.location
        ).overlays
      : undefined;

  return (
    <EntitiesProvider
      value={{
        cast: GALLERY_CAST,
        places,
        setPieces,
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
            {currentOverlays && currentOverlays.length > 0 && (
              <OverlayLayer
                overlays={currentOverlays}
                sceneId={`gallery-${template}-${variant}`}
              />
            )}
          </div>
        </RemotionSceneClock>
      </RemotionGlobalClock>
    </EntitiesProvider>
  );
};
