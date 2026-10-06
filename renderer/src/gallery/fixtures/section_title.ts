import type { SectionTitleProps } from "../../generated/contracts";

export const sectionTitleFixtures: Record<"min" | "typical" | "max", SectionTitleProps> = {
  min: {
    title: "Intro",
    index: 0,
    count: 1,
  },
  typical: {
    title: "The Great Stink of London",
    index: 2,
    count: 7,
  },
  max: {
    title: "MMMMWWWW TANK NEVER TESTED COMPREHENSIVELY SAFE",
    index: 9,
    count: 10,
  },
};
