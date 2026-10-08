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

const COMMON_OVERLAYS_THOUGHT_PROP: SceneOverlay[] = [
  {
    kind: "motif_token",
    icon: "Sparkle",
    anchor: "top_right",
    motif_id: "m1",
  },
  {
    kind: "thought",
    text: "WW Old Relic",
    anchor: "top_left",
  },
  {
    kind: "prop",
    icon: "Coins",
    anchor: "bottom_left",
  },
];

const COMMON_OVERLAYS_LABEL: SceneOverlay[] = [
  {
    kind: "motif_token",
    icon: "Sparkle",
    anchor: "top_right",
    motif_id: "m1",
  },
  {
    kind: "label",
    text: "WW Old Relic",
    anchor: "top_left",
  },
];

export const overlaysFixtures: Record<AllowedOverlayTemplate, OverlayFixture> = {
  kinetic_quote: {
    props: kineticQuoteFixtures.max,
    overlays: COMMON_OVERLAYS_THOUGHT_PROP,
  },
  stat_callout: {
    props: statCalloutFixtures.max,
    overlays: COMMON_OVERLAYS_THOUGHT_PROP,
  },
  reveal: {
    props: revealFixtures.max,
    overlays: COMMON_OVERLAYS_THOUGHT_PROP,
  },
  cause_effect: {
    props: causeEffectFixtures.max,
    overlays: COMMON_OVERLAYS_THOUGHT_PROP,
  },
  character_intro: {
    props: characterIntroFixtures.max,
    overlays: COMMON_OVERLAYS_THOUGHT_PROP,
  },
  emotion_beat: {
    props: emotionBeatFixtures.max,
    overlays: COMMON_OVERLAYS_THOUGHT_PROP,
  },
  relationship_map: {
    props: relationshipMapFixtures.max,
    overlays: COMMON_OVERLAYS_THOUGHT_PROP,
  },
  location: {
    props: {
      place_id: "p1",
      era_label: null,
    },
    overlays: COMMON_OVERLAYS_THOUGHT_PROP,
  },
  set_piece: {
    props: setPieceFixtures.max,
    overlays: COMMON_OVERLAYS_THOUGHT_PROP,
  },
  metaphor: {
    props: metaphorFixtures.max,
    overlays: COMMON_OVERLAYS_THOUGHT_PROP,
  },
};

export const overlaysLabelFixtures: Record<AllowedOverlayTemplate, OverlayFixture> = {
  kinetic_quote: {
    props: kineticQuoteFixtures.max,
    overlays: COMMON_OVERLAYS_LABEL,
  },
  stat_callout: {
    props: statCalloutFixtures.max,
    overlays: COMMON_OVERLAYS_LABEL,
  },
  reveal: {
    props: revealFixtures.max,
    overlays: COMMON_OVERLAYS_LABEL,
  },
  cause_effect: {
    props: causeEffectFixtures.max,
    overlays: COMMON_OVERLAYS_LABEL,
  },
  character_intro: {
    props: characterIntroFixtures.max,
    overlays: COMMON_OVERLAYS_LABEL,
  },
  emotion_beat: {
    props: emotionBeatFixtures.max,
    overlays: COMMON_OVERLAYS_LABEL,
  },
  relationship_map: {
    props: relationshipMapFixtures.max,
    overlays: COMMON_OVERLAYS_LABEL,
  },
  location: {
    props: {
      place_id: "p1",
      era_label: null,
    },
    overlays: COMMON_OVERLAYS_LABEL,
  },
  set_piece: {
    props: setPieceFixtures.max,
    overlays: COMMON_OVERLAYS_LABEL,
  },
  metaphor: {
    props: metaphorFixtures.max,
    overlays: COMMON_OVERLAYS_LABEL,
  },
};
