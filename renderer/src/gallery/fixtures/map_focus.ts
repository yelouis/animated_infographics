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
  },
  max: {
    region: "world",
    markers: [
      {
        place_id: "p4",
        label: "Arctic Station Alert",
      },
      {
        place_id: "p3",
        label: "Boston Distilling Co",
      },
      {
        place_id: "p5",
        label: "Equator Station",
      },
    ],

    path: true,
  },
};

