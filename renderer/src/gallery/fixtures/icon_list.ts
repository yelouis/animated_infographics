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
    heading: "Three Disaster Factors",
    items: [
      { icon: "Buildings", label: "Substandard Steel Tank" },
      { icon: "Thermometer", label: "Rapid Temperature Swing" },
      { icon: "ShieldWarning", label: "Neglected Leak Warnings" },
    ],
  },
  max: {
    heading: "WWWWWWWWWW MMMMMMMMMM WWWWWWWWWW",
    items: [
      { icon: "Buildings", label: "WWWWWWWW MMMMMMMM WWWWWWWW" },
      { icon: "Hammer", label: "MMMMMMMM WWWWWWWW MMMMMMMM" },
      { icon: "ShieldWarning", label: "WWWWWWWW MMMMMMMM WWWWWWWW" },
    ],
  },
};
