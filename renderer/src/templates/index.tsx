import React from "react";
import type { SceneOverlay, TimelineSceneTiming } from "../generated/contracts";
import { Callback } from "./callback";
import { CauseEffect } from "./cause_effect";
import { CharacterIntro } from "./character_intro";
import { Comparison } from "./comparison";
import { Dialogue } from "./dialogue";
import { EmotionBeat } from "./emotion_beat";
import { IconList } from "./icon_list";
import { KineticQuote } from "./kinetic_quote";
import { Location } from "./location";
import { MapFocus } from "./map_focus";
import { Metaphor } from "./metaphor";
import { RelationshipMap } from "./relationship_map";
import { Reveal } from "./reveal";
import { SectionTitle } from "./section_title";
import { SetPiece } from "./set_piece";
import { StatCallout } from "./stat_callout";
import { TextThread } from "./text_thread";
import { Timeline } from "./timeline";
import { TitleCard } from "./title_card";

export interface TemplateComponentProps {
  sceneId: string;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  props: any;
  timing?: TimelineSceneTiming;
  debug?: boolean;
  isGallery?: boolean;
  overlays?: SceneOverlay[];
}

export const TEMPLATES: Record<string, React.FC<TemplateComponentProps>> = {
  title_card: TitleCard as unknown as React.FC<TemplateComponentProps>,
  kinetic_quote: KineticQuote as unknown as React.FC<TemplateComponentProps>,
  stat_callout: StatCallout as unknown as React.FC<TemplateComponentProps>,
  icon_list: IconList as unknown as React.FC<TemplateComponentProps>,
  reveal: Reveal as unknown as React.FC<TemplateComponentProps>,
  cause_effect: CauseEffect as unknown as React.FC<TemplateComponentProps>,
  comparison: Comparison as unknown as React.FC<TemplateComponentProps>,
  character_intro: CharacterIntro as unknown as React.FC<TemplateComponentProps>,
  dialogue: Dialogue as unknown as React.FC<TemplateComponentProps>,
  text_thread: TextThread as unknown as React.FC<TemplateComponentProps>,
  emotion_beat: EmotionBeat as unknown as React.FC<TemplateComponentProps>,
  relationship_map: RelationshipMap as unknown as React.FC<TemplateComponentProps>,
  location: Location as unknown as React.FC<TemplateComponentProps>,
  set_piece: SetPiece as unknown as React.FC<TemplateComponentProps>,
  map_focus: MapFocus as unknown as React.FC<TemplateComponentProps>,
  timeline: Timeline as unknown as React.FC<TemplateComponentProps>,
  metaphor: Metaphor as unknown as React.FC<TemplateComponentProps>,
  callback: Callback as unknown as React.FC<TemplateComponentProps>,
  section_title: SectionTitle as unknown as React.FC<TemplateComponentProps>,
};

export const getTemplateComponent = (
  name: string
): React.FC<TemplateComponentProps> => {
  const component = TEMPLATES[name];
  if (!component) {
    throw new Error(`Unknown template: ${name}`);
  }
  return component;
};

export * from "./callback";
export * from "./cause_effect";
export * from "./character_intro";
export * from "./comparison";
export * from "./dialogue";
export * from "./emotion_beat";
export * from "./icon_list";
export * from "./kinetic_quote";
export * from "./location";
export * from "./map_focus";
export * from "./metaphor";
export * from "./relationship_map";
export * from "./reveal";
export * from "./section_title";
export * from "./set_piece";
export * from "./stat_callout";
export * from "./text_thread";
export * from "./timeline";
export * from "./title_card";
