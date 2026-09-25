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
      { from: "them", text: "Look what I uncovered behind Grandma Rose's trunk!" },
      { from: "me", text: "Is that the tin recipe box with the brass latch?" },
      { from: "them", text: "Every single handwritten index card is intact inside." },
    ],
  },
  max: {
    contact_name: "MMMMWWWW Dispatch Ops",
    contact_cast_id: "c1",
    messages: [
      {
        from: "them",
        text: "MMMMWWWW Initial status alert: structural report indicates major deviations.",
      },
      {
        from: "me",
        text: "MMMMWWWW Confirmed receipt of preliminary structural audit documents from regional team.",
      },
      {
        from: "them",
        text: "MMMMWWWW Emergency committee summoned to inspect commercial facility premises today.",
      },
      {
        from: "me",
        text: "MMMMWWWW We will arrive on site with qualified engineering specialists by noon.",
      },
      {
        from: "them",
        text: "MMMMWWWW Secure all maintenance perimeter zones and log visitor access immediately.",
      },
    ],
  },
};
