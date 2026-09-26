// Canvas and layout zones from design_visual_direction.md §1.

export const CANVAS = {
  width: 1080,
  height: 1920,
  fps: 30,
} as const;

export const ZONES = {
  topReserve: { x0: 0, y0: 0, x1: 1080, y1: 140 },
  stage: { x0: 60, y0: 140, x1: 1020, y1: 1180, width: 960, height: 1040 },
  captionBand: {
    x0: 90,
    y0: 1220,
    x1: 990,
    y1: 1460,
    width: 900,
    height: 240,
    centerY: 1340,
  },
  bottomReserve: { x0: 0, y0: 1500, x1: 1080, y1: 1920 },
} as const;

export const IMAGE_SCRIM = {
  stops: [
    [640, 0],
    [800, 0.85],
    [1120, 0.92],
  ],
} as const;

export const IMAGE_TEXT_MIN_TOP = 807;
