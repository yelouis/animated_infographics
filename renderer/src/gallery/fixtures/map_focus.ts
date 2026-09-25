import type { MapFocusProps } from "../../generated/contracts";

export const mapFocusFixtures: Record<"min" | "typical" | "max", MapFocusProps> = {
  min: {
    region: "USA",
    markers: [
      {
        place_id: "p1",
        label: "Duluth",
      },
    ],
  },
  typical: {
    region: "CAN",
    markers: [
      {
        place_id: "p1",
        label: "Duluth",
      },
      {
        place_id: "p2",
        label: "Thunder Bay",
      },
    ],
    path: true,
    caption: "190 miles north along the rocky shoreline",
  },
  max: {
    region: "world",
    markers: [
      {
        place_id: "p1",
        label: "Duluth Station HQ",
      },
      {
        place_id: "p2",
        label: "Thunder Bay Harbor",
      },
      {
        place_id: "p3",
        label: "Boston Distilling Co",
      },
    ],
    path: true,
    caption: "From the Great Lakes across the border down to the coast",
  },
};
