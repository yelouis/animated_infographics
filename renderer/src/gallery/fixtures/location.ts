import type { LocationProps } from "../../generated/contracts";

export const locationFixtures: Record<"min" | "typical" | "max", LocationProps> = {
  min: {
    place_id: "p1",
  },
  typical: {
    place_id: "p1",
    caption: "Home of Grandma Rose",
    era_label: "1961",
  },
  max: {
    place_id: "p1",
    caption: "A rugged estate on the shore of Lake Superior",
    era_label: "Circa 1961",
  },
};
