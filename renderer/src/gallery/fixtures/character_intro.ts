import type { CharacterIntroProps } from "../../generated/contracts";

export const characterIntroFixtures: Record<
  "min" | "typical" | "max",
  CharacterIntroProps
> = {
  min: {
    cast_id: "c1",
    descriptor: "Lead character",
    traits: [],
  },
  typical: {
    cast_id: "c1",
    descriptor: "Matriarch and master baker from Duluth",
    traits: ["Warm", "Perfectionist"],
  },
  max: {
    cast_id: "c1",
    descriptor: "MMMMWWWW Chief Senior Historical Research Officer",
    traits: ["Hyper-Organized", "Relentless Focus", "Unflappable Grit"],
  },
};
