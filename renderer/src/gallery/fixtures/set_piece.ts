import type { SetPieceProps } from "../../generated/contracts";

export const setPieceFixtures: Record<"min" | "typical" | "max", SetPieceProps> = {
  min: {
    set_piece_id: "sp1",
  },
  typical: {
    set_piece_id: "sp1",
    caption: "Found tucked behind the cedar trunk",
  },
  max: {
    set_piece_id: "sp1",
    caption: "Hundreds of handwritten recipes and secret notes",
  },
};
