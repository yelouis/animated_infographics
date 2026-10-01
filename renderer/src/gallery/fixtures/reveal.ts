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
    text: "The company blamed an anarchist bomb.",
  },
  max: {
    kicker: "SHOCKING HISTORIC TWIST",
    text: "MMMMWWWW TANK NEVER TESTED COMPREHENSIVELY SAFELY",
  },
};
