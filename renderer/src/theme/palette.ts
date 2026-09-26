// Theme palette tokens from design_visual_direction.md §2.
// All colours in the renderer must come from here.

export const palette = {
  bg: "#14213D",
  bgRaised: "#1F2F52",
  bgDeep: "#0B1326",
  ink: "#F8F4E9",
  inkMuted: "#B8C1D6",
  highlight: "#FFD166",
  danger: "#FF6B8B",
  mapSea: "#0B1326",
  mapLand: "#4466A0",
  mapRegion: "#7C9FDB",
  mapBorder: "#0B1326",
  castSlots: [
    "#F4A261",
    "#2A9D8F",
    "#E76F51",
    "#E9C46A",
    "#8AB17D",
    "#7B7FE0",
    "#F28482",
    "#4CC9F0",
  ],
} as const;

export type Palette = typeof palette;
