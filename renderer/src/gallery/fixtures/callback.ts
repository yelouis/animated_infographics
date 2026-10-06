import type { CallbackProps } from "../../generated/contracts";

export const callbackFixtures: Record<"min" | "typical" | "max", CallbackProps> = {
  min: {
    motif_id: "m1",
    label: null,
    icon: "Sparkle",
  },
  typical: {
    motif_id: "m1",
    label: "Old Key",
    icon: "Key",
  },
  max: {
    motif_id: "m1",
    label: "WWWWWWW MMMMMMM WWWWWWW",
    set_piece_id: "sp1",
    icon: "Sparkle",
  },
};
