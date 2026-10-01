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
      { label: "Rapid temperature swing", icon: "Thermometer" },
      { label: "Fermentation gas buildup", icon: "Fire" },
      { label: "Catastrophic structural failure", icon: "Buildings" },
    ],
  },
  max: {
    nodes: [
      {
        label: "MMMMWWWW UNTESTED MOLASSES",
        icon: "Drop",
      },
      {
        label: "CRITICAL STRUCTURAL DEFICIENCIES",
        icon: "Hammer",
      },
      {
        label: "COMPREHENSIVE MUNICIPAL LAWSUITS",
        icon: "ShieldWarning",
      },
    ],
  },
};
