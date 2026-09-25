import type { DialogueProps } from "../../generated/contracts";

export const dialogueFixtures: Record<
  "min" | "typical" | "max",
  DialogueProps
> = {
  min: {
    lines: [
      {
        cast_id: "c1",
        text: "We have to leave now before the winter storms close the road.",
        tone: "neutral",
      },
    ],
  },
  typical: {
    lines: [
      {
        cast_id: "c1",
        text: "Did you find Grandma Rose's missing recipe box in the cellar?",
        tone: "happy",
      },
      {
        cast_id: "c2",
        text: "Yes! It was tucked behind the old cedar chest all along.",
        tone: "shocked",
      },
    ],
  },
  max: {
    lines: [
      {
        cast_id: "c1",
        text: "MMMMWWWW We examined every single historical container and logged comprehensive reports.",
        tone: "angry",
      },
      {
        cast_id: "c2",
        text: "MMMMWWWW The regional inspector verified unauthorized structural alterations across levels.",
        tone: "shocked",
      },
      {
        cast_id: "c1",
        text: "MMMMWWWW All official regulatory documentation confirms zero compliance from management.",
        tone: "sarcastic",
      },
    ],
  },
};
