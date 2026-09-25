import type { StatCalloutProps } from "../../generated/contracts";

export const statCalloutFixtures: Record<
  "min" | "typical" | "max",
  StatCalloutProps
> = {
  min: {
    value: 5,
    decimals: 0,
    prefix: "",
    display_scale: "none",
    suffix: "",
  },
  typical: {
    value: 2.3,
    decimals: 1,
    prefix: "",
    display_scale: "million",
    suffix: "gallons",
    caption: "of molasses swept through the streets at 35 miles per hour",
    icon: "Drop",
  },
  max: {
    value: 9999.9,
    decimals: 1,
    prefix: "$",
    display_scale: "billion",
    suffix: "TOTAL VALUATION",
    caption: "Maximum estimated cumulative liability assessed across all historic regional claims",
    icon: "Coins",
  },
};
