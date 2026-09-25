import type { CauseEffectProps } from "../../generated/contracts";

export const causeEffectFixtures: Record<
  "min" | "typical" | "max",
  CauseEffectProps
> = {
  min: {
    nodes: [
      { label: "Pressure built inside", icon: "Drop" },
      { label: "Steel rivets sheared", icon: "ShieldWarning" },
    ],
  },
  typical: {
    nodes: [
      { label: "Rapid temperature swing to 43°F", icon: "Thermometer" },
      { label: "Fermentation released carbon dioxide", icon: "Fire" },
      { label: "Catastrophic structural failure", icon: "Buildings" },
    ],
  },
  max: {
    nodes: [
      {
        label: "EXCESSIVE UNTESTED CHEMICAL PRESSURE",
        icon: "Drop",
      },
      {
        label: "SYSTEMIC METALLURGICAL WALL FATIGUE",
        icon: "Hammer",
      },
      {
        label: "CATASTROPHIC RIVET BURSTING WAVE",
        icon: "ShieldWarning",
      },
      {
        label: "UNPRECEDENTED URBAN MOLASSES FLOOD",
        icon: "Buildings",
      },
    ],
  },
};
