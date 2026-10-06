import type { MetaphorProps } from "../../generated/contracts";

export const metaphorFixtures: Record<"min" | "typical" | "max", MetaphorProps> = {
  min: {
    image_entity: "none",
    label: null,
    cast_ids: [],
  },
  typical: {
    image_entity: "sp1",
    label: "Brewing Storm",
    cast_ids: ["c1"],
  },
  max: {
    image_entity: "sp1",
    label: "WWWWWWW MMMMMMM WWWWWWW",
    cast_ids: ["c1", "c2"],
  },
};
