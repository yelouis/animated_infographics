import type { LocationProps } from "../../generated/contracts";

export const locationFixtures: Record<"min" | "typical" | "max" | "worst", LocationProps> = {
  min: {
    place_id: "p1",
  },
  typical: {
    place_id: "p1",
    era_label: "1961",
  },
  max: {
    place_id: "p1",
    era_label: "Circa 1961",
  },
  worst: {
    place_id: "p1",
  },
};

