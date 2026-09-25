import type { TitleCardProps } from "../../generated/contracts";

export const titleCardFixtures: Record<
  "min" | "typical" | "max",
  TitleCardProps
> = {
  min: {
    title: "Boston",
  },
  typical: {
    title: "The Great Molasses Flood",
    subtitle: "Boston, Massachusetts — January 15, 1919",
    icon: "Drop",
  },
  max: {
    title: "Twenty-One Victims: The Complete Story of the Boston Wave",
    subtitle: "Comprehensive investigation into the industrial catastrophe and legal aftermath.",
    icon: "Buildings",
  },
};
