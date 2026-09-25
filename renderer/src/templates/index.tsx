import React from "react";
import { KineticQuote } from "./kinetic_quote";
import { Placeholder } from "./Placeholder";

export interface TemplateComponentProps {
  sceneId: string;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  props: any;
  debug?: boolean;
  isGallery?: boolean;
}

export const TEMPLATES: Record<string, React.FC<TemplateComponentProps>> = {
  title_card: () => <Placeholder templateName="title_card" />,
  kinetic_quote: KineticQuote as unknown as React.FC<TemplateComponentProps>,
  stat_callout: () => <Placeholder templateName="stat_callout" />,
  icon_list: () => <Placeholder templateName="icon_list" />,
  reveal: () => <Placeholder templateName="reveal" />,
  cause_effect: () => <Placeholder templateName="cause_effect" />,
  comparison: () => <Placeholder templateName="comparison" />,
  character_intro: () => <Placeholder templateName="character_intro" />,
  dialogue: () => <Placeholder templateName="dialogue" />,
  text_thread: () => <Placeholder templateName="text_thread" />,
  emotion_beat: () => <Placeholder templateName="emotion_beat" />,
  relationship_map: () => <Placeholder templateName="relationship_map" />,
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

export * from "./kinetic_quote";
export * from "./Placeholder";
