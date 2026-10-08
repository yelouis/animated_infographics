/**
 * Overlay layout bounds and clearance contracts.
 * Per design_styles.md §3.5-3.6 and agent_execution_guide.md §G4.
 */

export interface Rect {
  left: number;
  top: number;
  right: number;
  bottom: number;
}

export function isRectDisjoint(a: Rect, b: Rect): boolean {
  return a.right <= b.left || a.left >= b.right || a.bottom <= b.top || a.top >= b.bottom;
}

/**
 * Overlay bounding boxes (screen coordinates, 1080x1920 canvas).
 * - motif_token: 120 px circle centred at (900, 240)
 * - thought: cloud 240x170 centred at (840, 260)
 * - label: chip 320 px wide, top-right at (1000, 200)
 * - prop: 140 px icon centred at (170, 1090)
 */
export const OVERLAY_BOUNDS: Record<"motif_token" | "thought" | "label" | "prop", Rect> = {
  motif_token: { left: 840, top: 180, right: 960, bottom: 300 },
  thought: { left: 60, top: 165, right: 300, bottom: 335 },
  label: { left: 60, top: 200, right: 300, bottom: 302 },
  prop: { left: 100, top: 1020, right: 240, bottom: 1160 },
};

/**
 * 10 templates allowed to carry overlays (design_styles.md §3.5).
 */
export const ALLOWED_OVERLAY_TEMPLATES = [
  "kinetic_quote",
  "stat_callout",
  "reveal",
  "cause_effect",
  "character_intro",
  "emotion_beat",
  "relationship_map",
  "location",
  "set_piece",
  "metaphor",
] as const;

export type AllowedOverlayTemplate = (typeof ALLOWED_OVERLAY_TEMPLATES)[number];

/**
 * 8 templates forbidden from carrying overlays.
 */
export const FORBIDDEN_OVERLAY_TEMPLATES = [
  "title_card",
  "callback",
  "icon_list",
  "comparison",
  "timeline",
  "text_thread",
  "dialogue",
  "map_focus",
  "section_title",
] as const;

