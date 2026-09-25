import type { AvatarConfig } from "../../generated/contracts";
import type { AvatarExpression } from "../../components/Avatar";

export interface AvatarSheetEntry {
  id: string;
  label: string;
  avatar: AvatarConfig;
  colorSlot: number;
}

export interface AvatarSheetProps {
  title?: string;
  characters: AvatarSheetEntry[];
  expressions: AvatarExpression[];
}

export const ALL_EXPRESSIONS: AvatarExpression[] = [
  "neutral",
  "happy",
  "sad",
  "angry",
  "shocked",
  "confused",
  "smug",
  "nervous",
];

export const FOUR_CHARACTERS: AvatarSheetEntry[] = [
  {
    id: "child",
    label: "Child",
    colorSlot: 3, // #E9C46A
    avatar: {
      age: "child",
      skin: 0,
      hair_style: "curly",
      hair_color: "blonde",
      facial_hair: "none",
      headwear: "none",
      glasses: false,
    },
  },
  {
    id: "adult_glasses",
    label: "Adult (Glasses)",
    colorSlot: 0, // #F4A261
    avatar: {
      age: "adult",
      skin: 2,
      hair_style: "short",
      hair_color: "black",
      facial_hair: "beard",
      headwear: "hat",
      glasses: true,
    },
  },
  {
    id: "adult_headscarf",
    label: "Adult (Headscarf)",
    colorSlot: 1, // #2A9D8F
    avatar: {
      age: "adult",
      skin: 4,
      hair_style: "long",
      hair_color: "brown",
      facial_hair: "none",
      headwear: "headscarf",
      glasses: false,
    },
  },
  {
    id: "elder_crown",
    label: "Elder (Crown)",
    colorSlot: 5, // #7B7FE0
    avatar: {
      age: "elder",
      skin: 1,
      hair_style: "bun",
      hair_color: "black", // Elder rule forces to gray
      facial_hair: "mustache",
      headwear: "crown",
      glasses: false,
    },
  },
];

export const avatarSheetFixtures: Record<
  "min" | "typical" | "max",
  AvatarSheetProps
> = {
  min: {
    title: "Avatar Sheet (Min)",
    characters: FOUR_CHARACTERS.slice(0, 2),
    expressions: ["neutral", "happy", "sad", "angry"],
  },
  typical: {
    title: "Avatar Sheet — 8 Expressions × 4 Combinations",
    characters: FOUR_CHARACTERS,
    expressions: ALL_EXPRESSIONS,
  },
  max: {
    title: "Avatar Sheet — Maximum Detailed Cast Matrix",
    characters: FOUR_CHARACTERS,
    expressions: ALL_EXPRESSIONS,
  },
};
