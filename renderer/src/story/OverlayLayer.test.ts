import { describe, expect, it } from "vitest";
import registry from "../generated/templateRegistry.json";
import {
  ALLOWED_OVERLAY_TEMPLATES,
  FORBIDDEN_OVERLAY_TEMPLATES,
  OVERLAY_BOUNDS,
  isRectDisjoint,
} from "../theme/overlayLayout";

describe("Overlay bounds and clearance", () => {
  it("defines the four OVERLAY_BOUNDS boxes equal to the specification", () => {
    expect(OVERLAY_BOUNDS.motif_token).toEqual({
      left: 840,
      top: 180,
      right: 960,
      bottom: 300,
    });
    expect(OVERLAY_BOUNDS.thought).toEqual({
      left: 60,
      top: 165,
      right: 300,
      bottom: 335,
    });
    expect(OVERLAY_BOUNDS.label).toEqual({
      left: 60,
      top: 200,
      right: 300,
      bottom: 302,
    });
    expect(OVERLAY_BOUNDS.prop).toEqual({
      left: 100,
      top: 1020,
      right: 240,
      bottom: 1160,
    });
  });

  it("asserts every pair drawn together is disjoint", () => {
    // token × thought
    expect(
      isRectDisjoint(OVERLAY_BOUNDS.motif_token, OVERLAY_BOUNDS.thought)
    ).toBe(true);

    // token × label
    expect(
      isRectDisjoint(OVERLAY_BOUNDS.motif_token, OVERLAY_BOUNDS.label)
    ).toBe(true);

    // token × prop
    expect(
      isRectDisjoint(OVERLAY_BOUNDS.motif_token, OVERLAY_BOUNDS.prop)
    ).toBe(true);

    // thought × prop
    expect(
      isRectDisjoint(OVERLAY_BOUNDS.thought, OVERLAY_BOUNDS.prop)
    ).toBe(true);
  });

  it("allowed and forbidden overlay template partitions cover all registry templates", () => {
    const registryTemplates = Object.keys(registry).filter(
      (k) => !k.startsWith("$")
    );
    expect(registryTemplates.length).toBe(19);

    expect(ALLOWED_OVERLAY_TEMPLATES.length).toBe(10);
    expect(FORBIDDEN_OVERLAY_TEMPLATES.length).toBe(9);

    const unionSet = new Set<string>([
      ...ALLOWED_OVERLAY_TEMPLATES,
      ...FORBIDDEN_OVERLAY_TEMPLATES,
    ]);
    expect(unionSet.size).toBe(19);

    for (const name of registryTemplates) {
      expect(
        unionSet.has(name),
        `Template ${name} must be either allowed or forbidden for overlays`
      ).toBe(true);
    }
  });
});
