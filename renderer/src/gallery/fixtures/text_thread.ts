import type { TextThreadProps } from "../../generated/contracts";

export const textThreadFixtures: Record<
  "min" | "typical" | "max",
  TextThreadProps
> = {
  min: {
    contact_name: "Dispatch",
    messages: [
      { from: "them", text: "Are you on the road yet?" },
      { from: "me", text: "Heading north on Route 61 now." },
    ],
  },
  typical: {
    contact_name: "Danny",
    contact_cast_id: "c2",
    messages: [
      { from: "them", text: "Look what I uncovered behind Grandma's trunk!" },
      { from: "me", text: "Is that the tin recipe box with brass?" },
      { from: "them", text: "Every single handwritten card is intact inside." },
    ],
  },
  max: {
    contact_name: "MMMMWWWW Dispatch Op",
    contact_cast_id: "c1",
    messages: [
      {
        from: "them",
        text: "MMMMWWWW Initial status alert: report indicates major structural deviations.",
      },
      {
        from: "me",
        text: "MMMMWWWW Confirmed receipt of preliminary structural audit documents today.",
      },
      {
        from: "them",
        text: "MMMMWWWW Secure all maintenance perimeter zones and log visitors now.",
      },
    ],
  },
};
