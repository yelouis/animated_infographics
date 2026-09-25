import type { EmotionBeatProps } from "../../generated/contracts";

export const emotionBeatFixtures: Record<
  "min" | "typical" | "max",
  EmotionBeatProps
> = {
  min: {
    cast_id: "c1",
    emotion: "happy",
  },
  typical: {
    cast_id: "c2",
    emotion: "shocked",
    caption: "Danny stood completely frozen in disbelief",
  },
  max: {
    cast_id: "c1",
    emotion: "angry",
    caption: "MMMMWWWW Outraged by the audit findings",
  },
};
