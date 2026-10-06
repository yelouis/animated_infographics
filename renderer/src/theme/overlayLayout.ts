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
  thought: { left: 720, top: 175, right: 960, bottom: 345 },
  label: { left: 680, top: 200, right: 1000, bottom: 260 },
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

/**
 * Slot / prominent element rectangles of the 10 allowed templates at max layout.
 * Every overlay rectangle in OVERLAY_BOUNDS must be disjoint from every rect here.
 */
export const TEMPLATE_SLOT_BOUNDS: Record<AllowedOverlayTemplate, Rect[]> = {
  kinetic_quote: [
    { left: 100, top: 380, right: 980, bottom: 960 }, // Quote text block at max layout
    { left: 240, top: 1000, right: 840, bottom: 1160 }, // Attribution container
  ],
  stat_callout: [
    { left: 460, top: 250, right: 620, bottom: 410 }, // Icon centred at (540, 330)
    { left: 70, top: 440, right: 1010, bottom: 750 }, // Value block
  ],
  reveal: [
    { left: 90, top: 410, right: 990, bottom: 490 }, // Kicker at y 410
    { left: 70, top: 520, right: 1010, bottom: 860 }, // Reveal text
  ],
  cause_effect: [
    { left: 120, top: 345, right: 960, bottom: 975 }, // 3 node cards stack
  ],
  character_intro: [
    { left: 90, top: 660, right: 990, bottom: 770 }, // Name text slot
    { left: 110, top: 790, right: 970, bottom: 880 }, // Descriptor text slot
  ],
  emotion_beat: [
    { left: 280, top: 400, right: 800, bottom: 920 }, // Avatar 520 px at top y 400
  ],
  relationship_map: [
    { left: 450, top: 220, right: 630, bottom: 400 }, // 12 o'clock top node
    { left: 210, top: 360, right: 870, bottom: 980 }, // Central circle area and other nodes
  ],
  location: [
    { left: 260, top: 920, right: 980, bottom: 1080 }, // Place name bottom-aligned at y 1080
  ],
  set_piece: [
    { left: 260, top: 920, right: 980, bottom: 1080 }, // Set piece name bottom-aligned at y 1080
  ],
  metaphor: [
    { left: 260, top: 920, right: 980, bottom: 1080 }, // Metaphor label bottom-aligned at y 1080
  ],
};
