import type { KineticQuoteProps } from "../../generated/contracts";

export const kineticQuoteFixtures: Record<
  "min" | "typical" | "max",
  KineticQuoteProps
> = {
  min: {
    text: "Never give up.",
    emphasis: ["Never"],
  },
  typical: {
    text: "Everything I have learned about life can be summed up: it goes on.",
    emphasis: ["life", "goes", "on"],
    attribution_cast_id: "c1",
  },
  max: {
    text: "The only limit to our realization of tomorrow will be doubts of today.",
    emphasis: ["tomorrow", "doubts", "today"],
    attribution_cast_id: "c1",
  },
};
