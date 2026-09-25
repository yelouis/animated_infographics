import type { ComparisonProps } from "../../generated/contracts";

export const comparisonFixtures: Record<
  "min" | "typical" | "max",
  ComparisonProps
> = {
  min: {
    a: {
      heading: "North End",
      icon: "Buildings",
      points: ["Dense neighborhood"],
    },
    b: {
      heading: "Boston Harbor",
      icon: "Drop",
      points: ["Industrial shipping"],
    },
  },
  typical: {
    a: {
      heading: "Company Defense",
      icon: "Buildings",
      points: [
        "Blamed anarchist bomb plot",
        "Claimed wartime sabotage",
        "Denied structural defects",
      ],
    },
    b: {
      heading: "State Auditor",
      cast_id: "c1",
      points: [
        "Proved steel walls too thin",
        "Documented ignored leaks",
        "Found company fully liable",
      ],
    },
  },
  max: {
    a: {
      heading: "CORPORATE DEFENSE",
      icon: "Buildings",
      points: [
        "TOTAL DENIAL OF FAULTY MATERIALS",
        "ATTRIBUTED CRASH TO SABOTEURS",
        "REFUSED VOLUNTARY SETTLEMENTS",
        "APPEALED PRELIMINARY INJUNCTION",
      ],
    },
    b: {
      heading: "MUNICIPAL VICTIMS",
      cast_id: "c1",
      points: [
        "PROVED GROSS DESIGN NEGLIGENCE",
        "DOCUMENTED RIVET TEAR STRESSES",
        "PRESENTED METALLURGY EVIDENCE",
        "WON FULL RESTITUTION JUDGMENTS",
      ],
    },
  },
};
