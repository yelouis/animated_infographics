import React from "react";
import type { TimelineSceneTiming } from "../generated/contracts";
import { CauseEffect } from "./cause_effect";
import { CharacterIntro } from "./character_intro";
import { Comparison } from "./comparison";
import { Dialogue } from "./dialogue";
import { EmotionBeat } from "./emotion_beat";
import { IconList } from "./icon_list";
import { KineticQuote } from "./kinetic_quote";
import { Placeholder } from "./Placeholder";
import { RelationshipMap } from "./relationship_map";
import { Reveal } from "./reveal";
import { StatCallout } from "./stat_callout";
import { TextThread } from "./text_thread";
import { TitleCard } from "./title_card";

export interface TemplateComponentProps {
  sceneId: string;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  props: any;
  timing?: TimelineSceneTiming;
  debug?: boolean;
  isGallery?: boolean;
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
  location: () => <Placeholder templateName="location" />,
  set_piece: () => <Placeholder templateName="set_piece" />,
  map_focus: () => <Placeholder templateName="map_focus" />,
  timeline: () => <Placeholder templateName="timeline" />,
};

export const getTemplateComponent = (
  name: string
): React.FC<TemplateComponentProps> => {
  return TEMPLATES[name] || (() => <Placeholder templateName={name} />);
};

export * from "./cause_effect";
export * from "./character_intro";
export * from "./comparison";
export * from "./dialogue";
export * from "./emotion_beat";
export * from "./icon_list";
export * from "./kinetic_quote";
export * from "./Placeholder";
export * from "./relationship_map";
export * from "./reveal";
export * from "./stat_callout";
export * from "./text_thread";
export * from "./title_card";
