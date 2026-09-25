import type { IconListProps } from "../../generated/contracts";

export const iconListFixtures: Record<
  "min" | "typical" | "max",
  IconListProps
> = {
  min: {
    items: [
      { icon: "Drop", label: "Pressure" },
      { icon: "ShieldWarning", label: "Failure" },
    ],
  },
  typical: {
    heading: "Key Factors in the Disaster",
    items: [
      { icon: "Buildings", label: "Substandard Steel Tank" },
      { icon: "Thermometer", label: "Rapid Temperature Swing" },
      { icon: "ShieldWarning", label: "Neglected Leak Warnings" },
    ],
  },
  max: {
    heading: "MAXIMUM INDUSTRIAL CASUALTY DEMANDS",
    items: [
      { icon: "Buildings", label: "EXCESSIVE UNTESTED MOLASSES LOAD" },
      { icon: "Hammer", label: "CRITICAL STRUCTURAL DEFICIENCIES" },
      { icon: "ShieldWarning", label: "IMMEDIATE EMERGENCY SYSTEM CRASH" },
      { icon: "Scales", label: "COMPREHENSIVE MUNICIPAL LAWSUITS" },
    ],
  },
};
