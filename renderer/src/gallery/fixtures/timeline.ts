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
    highlight_index: 2,
    events: [
      { date_label: "WWWW MMM WWWW", label: "WWWWWWWW MMMMMMMM WWWWWWWW" },
      { date_label: "MMMM WWW MMMM", label: "MMMMMMMM WWWWWWWW MMMMMMMM" },
      { date_label: "WWWW MMM WWWW", label: "WWWWWWWW MMMMMMMM WWWWWWWW" },
      { date_label: "MMMM WWW MMMM", label: "MMMMMMMM WWWWWWWW MMMMMMMM" },
    ],
  },
};
