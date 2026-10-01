import type { CharacterIntroProps } from "../../generated/contracts";

export const characterIntroFixtures: Record<
  "min" | "typical" | "max",
  CharacterIntroProps
> = {
  min: {
    cast_id: "c1",
    descriptor: "Lead character",
  },
  typical: {
    cast_id: "c1",
    descriptor: "Master baker from Duluth",
  },
  max: {
    cast_id: "c1",
    descriptor: "WWWWWWWWWW MMMMMMMMMM WWWWWWWWWW MMMMMMMMMM",
  },
};
