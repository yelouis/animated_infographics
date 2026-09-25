import type { RevealProps } from "../../generated/contracts";

export const revealFixtures: Record<
  "min" | "typical" | "max",
  RevealProps
> = {
  min: {
    kicker: "VERDICT",
    text: "Guilty.",
  },
  typical: {
    kicker: "PLOT TWIST",
    text: "The company blamed anarchists for planting a bomb.",
  },
  max: {
    kicker: "SHOCKING HISTORIC TWIST",
    text: "THE TANK HAD NEVER ONCE BEEN TESTED SAFELY WITH FULL WATER.",
  },
};
