// Motion tokens from design_visual_direction.md §4.
import { Easing } from "remotion";

export const ENTER_FRAMES = 12; // 400 ms
export const EXIT_FRAMES = 8; // 267 ms
export const STAGGER_FRAMES = 4;

export const EASE_ENTER = Easing.bezier(0.16, 1, 0.3, 1);
export const EASE_EXIT = Easing.bezier(0.7, 0, 0.84, 0);

export const SPRING_POP_CONFIG = {
  damping: 14,
  stiffness: 180,
  mass: 0.8,
} as const;
