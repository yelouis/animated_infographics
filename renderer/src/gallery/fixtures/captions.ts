import type { CaptionPage } from "../../generated/contracts";

export const captionFixtures: Record<string, CaptionPage[]> = {
  long_active: [
    {
      start_frame: 0,
      end_frame: 150,
      words: [
        {
          text: "the",
          start_frame: 0,
          end_frame: 30,
        },
        {
          text: "engagement",
          start_frame: 30,
          end_frame: 90,
        },
        {
          text: "fell",
          start_frame: 90,
          end_frame: 150,
        },
      ],
    },
  ],
};
