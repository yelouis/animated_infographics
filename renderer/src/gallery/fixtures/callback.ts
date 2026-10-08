import type { CallbackProps, TimelineSceneTiming } from "../../generated/contracts";

export interface CallbackFixture {
  props: CallbackProps;
  timing: TimelineSceneTiming;
}

export const callbackFixtures: Record<"min" | "typical" | "max", CallbackFixture> = {
  min: {
    props: {
      motif_id: "m1",
      label: null,
      icon: "Sparkle",
    },
    timing: { item_frames: [20] },
  },
  typical: {
    props: {
      motif_id: "m1",
      label: "Old Key",
      icon: "Key",
    },
    timing: { item_frames: [15, 27] },
  },
  max: {
    props: {
      motif_id: "m1",
      label: "WWWWWWW MMMMMMM WWWWWWW",
      set_piece_id: "sp1",
      icon: "Sparkle",
    },
    timing: { item_frames: [10, 20, 30, 40, 50] },
  },
};
