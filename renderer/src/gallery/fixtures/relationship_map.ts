import type { RelationshipMapProps } from "../../generated/contracts";

export const relationshipMapFixtures: Record<
  "min" | "typical" | "max",
  RelationshipMapProps
> = {
  min: {
    cast_ids: ["c1", "c2"],
    edges: [{ from_id: "c1", to_id: "c2", label: "Partners", style: "solid" }],
  },
  typical: {
    cast_ids: ["c1", "c2", "c3"],
    edges: [
      { from_id: "c1", to_id: "c2", label: "Grandmother", style: "solid" },
      { from_id: "c2", to_id: "c3", label: "Estranged Uncle", style: "broken" },
    ],
  },
  max: {
    cast_ids: ["c1", "c2", "c3", "c4", "c5"],
    edges: [
      { from_id: "c1", to_id: "c2", label: "Chief Advisor", style: "solid" },
      { from_id: "c2", to_id: "c3", label: "Covert Contact", style: "dashed" },
      { from_id: "c3", to_id: "c4", label: "Bitter Rival", style: "broken" },
      { from_id: "c4", to_id: "c5", label: "Alliance Partner", style: "solid" },
      { from_id: "c1", to_id: "c5", label: "Informal Envoy", style: "dashed" },
      { from_id: "c2", to_id: "c4", label: "Direct Informant", style: "solid" },
    ],
  },
};
