import type { DialogueProps } from "../../generated/contracts";

export const dialogueFixtures: Record<
  "min" | "typical" | "max",
  DialogueProps
> = {
  min: {
    lines: [
      {
        cast_id: "c1",
        text: "We must leave now before the road closes.",
        tone: "neutral",
      },
    ],
  },
  typical: {
    lines: [
      {
        cast_id: "c1",
        text: "Did you find Grandma Rose's recipe box in the cellar?",
        tone: "happy",
      },
      {
        cast_id: "c2",
        text: "Yes! It was tucked behind the old cedar chest.",
        tone: "shocked",
      },
    ],
  },
  max: {
    lines: [
      {
        cast_id: "c1",
        text: "MMMMWWWW We examined every single historical container and logged reports.",
        tone: "angry",
      },
      {
        cast_id: "c2",
        text: "MMMMWWWW The regional inspector verified unauthorized structural alterations across levels.",
        tone: "shocked",
      },
    ],
  },
};
