import type { ComparisonProps } from "../../generated/contracts";

export const comparisonFixtures: Record<
  "min" | "typical" | "max",
  ComparisonProps
> = {
  min: {
    a: {
      heading: "North End",
      icon: "Buildings",
      points: ["Dense neighborhood"],
    },
    b: {
      heading: "Boston Harbor",
      icon: "Drop",
      points: ["Industrial shipping"],
    },
  },
  typical: {
    a: {
      heading: "Company Defense",
      icon: "Buildings",
      points: [
        "Blamed bomb plot",
        "Denied structural defects",
      ],
    },
    b: {
      heading: "State Auditor",
      cast_id: "c1",
      points: [
        "Proved thin walls",
        "Found full liability",
      ],
    },
  },
  max: {
    a: {
      heading: "WWWWWW MMMMMM WWWWWW",
      icon: "Buildings",
      points: [
        "WWWWWWWW MMMMMMMM WWWWWWWW",
        "MMMMMMMM WWWWWWWW MMMMMMMM",
      ],
    },
    b: {
      heading: "MMMMMM WWWWWW MMMMMM",
      cast_id: "c1",
      points: [
        "WWWWWWWW MMMMMMMM WWWWWWWW",
        "MMMMMMMM WWWWWWWW MMMMMMMM",
      ],
    },
  },
};
