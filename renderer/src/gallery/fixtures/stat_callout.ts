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
    icon: "Drop",
  },
  max: {
    value: 9999.9,
    decimals: 1,
    prefix: "$",
    display_scale: "billion",
    suffix: "WWWWWW MMMMMM",
    icon: "Coins",
  },
};
