import type { TimelineProps } from "../../generated/contracts";

export const timelineFixtures: Record<"min" | "typical" | "max", TimelineProps> = {
  min: {
    highlight_index: 1,
    events: [
      { date_label: "1919", label: "The molasses flood" },
      { date_label: "1925", label: "Court judgment" },
      { date_label: "1930", label: "Final settlement" },
    ],
  },
  typical: {
    highlight_index: 2,
    events: [
      { date_label: "1915", label: "Purity builds tank" },
      { date_label: "Jan 15, 1919", label: "Molasses wave strikes" },
      { date_label: "1925", label: "Hugh Ogden report" },
      { date_label: "1926", label: "USIA pays damages" },
    ],
  },
  max: {
    highlight_index: 4,
    events: [
      { date_label: "Dec 1915", label: "Tank constructed in Boston" },
      { date_label: "Summer 1916", label: "Tank groans and leaks" },
      { date_label: "Jan 15, 1919", label: "Disaster strikes the city" },
      { date_label: "Feb 1919", label: "Harbor cleanup operation" },
      { date_label: "Apr 1925", label: "Master files guilt report" },
      { date_label: "Dec 1926", label: "Victims receive damages" },
    ],
  },
};
