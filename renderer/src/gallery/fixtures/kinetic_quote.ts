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
    text: "In three words I can sum up everything I've learned about life: it goes on.",
    emphasis: ["life", "goes", "on"],
    attribution_cast_id: "c1",
  },
  max: {
    text: "The only limit to our realization of tomorrow will be our doubts of today. Move.",
    emphasis: ["tomorrow", "doubts", "Move"],
    attribution_cast_id: "c1",
  },
};
