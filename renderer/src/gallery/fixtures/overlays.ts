import type { SceneOverlay } from "../../generated/contracts";
import type { AllowedOverlayTemplate } from "../../theme/overlayLayout";
import { causeEffectFixtures } from "./cause_effect";
import { characterIntroFixtures } from "./character_intro";
import { emotionBeatFixtures } from "./emotion_beat";
import { kineticQuoteFixtures } from "./kinetic_quote";
import { metaphorFixtures } from "./metaphor";
import { relationshipMapFixtures } from "./relationship_map";
import { revealFixtures } from "./reveal";
import { setPieceFixtures } from "./set_piece";
import { statCalloutFixtures } from "./stat_callout";

export interface OverlayFixture {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  props: any;
  overlays: SceneOverlay[];
}

const COMMON_OVERLAYS: SceneOverlay[] = [
  {
    kind: "motif_token",
    icon: "Sparkle",
    anchor: "top_right",
    motif_id: "m1",
  },
  {
    kind: "label",
    text: "WW Old Relic",
    anchor: "top_right",
  },
];

export const overlaysFixtures: Record<AllowedOverlayTemplate, OverlayFixture> = {
  kinetic_quote: {
    props: kineticQuoteFixtures.max,
    overlays: COMMON_OVERLAYS,
  },
  stat_callout: {
    props: statCalloutFixtures.max,
    overlays: COMMON_OVERLAYS,
  },
  reveal: {
    props: revealFixtures.max,
    overlays: COMMON_OVERLAYS,
  },
  cause_effect: {
    props: causeEffectFixtures.max,
    overlays: COMMON_OVERLAYS,
  },
  character_intro: {
    props: characterIntroFixtures.max,
    overlays: COMMON_OVERLAYS,
  },
  emotion_beat: {
    props: emotionBeatFixtures.max,
    overlays: COMMON_OVERLAYS,
  },
  relationship_map: {
    props: relationshipMapFixtures.max,
    overlays: COMMON_OVERLAYS,
  },
  location: {
    props: {
      place_id: "p1",
      era_label: null,
    },
    overlays: COMMON_OVERLAYS,
  },
  set_piece: {
    props: setPieceFixtures.max,
    overlays: COMMON_OVERLAYS,
  },
  metaphor: {
    props: metaphorFixtures.max,
    overlays: COMMON_OVERLAYS,
  },
};
