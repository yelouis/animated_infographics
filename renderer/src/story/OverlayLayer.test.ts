import { describe, expect, it } from "vitest";
import registry from "../generated/templateRegistry.json";
import {
  ALLOWED_OVERLAY_TEMPLATES,
  FORBIDDEN_OVERLAY_TEMPLATES,
  OVERLAY_BOUNDS,
  TEMPLATE_SLOT_BOUNDS,
  isRectDisjoint,
  type Rect,
} from "../theme/overlayLayout";

describe("Overlay clearance and slot disjointness", () => {
  it("covers all 10 allowed templates and asserts every overlay is disjoint from max layout slots", () => {
    expect(ALLOWED_OVERLAY_TEMPLATES.length).toBe(10);

    const overlayKinds = Object.keys(OVERLAY_BOUNDS) as Array<
      keyof typeof OVERLAY_BOUNDS
    >;

    for (const template of ALLOWED_OVERLAY_TEMPLATES) {
      const slots = TEMPLATE_SLOT_BOUNDS[template];
      expect(
        slots.length,
        `Template ${template} must define at least one slot/element bound`
      ).toBeGreaterThan(0);

      for (const slot of slots) {
        for (const kind of overlayKinds) {
          const overlayRect = OVERLAY_BOUNDS[kind];
          const disjoint = isRectDisjoint(overlayRect, slot);
          expect(
            disjoint,
            `Overlay '${kind}' [${overlayRect.left}, ${overlayRect.top}, ${overlayRect.right}, ${overlayRect.bottom}] overlaps template '${template}' slot [${slot.left}, ${slot.top}, ${slot.right}, ${slot.bottom}]`
          ).toBe(true);
        }
      }
    }
  });

  it("falsification: moving motif token to (540, 240) collides with character_intro or kinetic_quote slots", () => {
    // A 120 px circle centred at (540, 240) has bounds [480, 180, 600, 300]
    const falsifiedMotifToken: Rect = {
      left: 480,
      top: 180,
      right: 600,
      bottom: 300,
    };

    // 1. Collides with character_intro avatar element [320, 180, 760, 620]
    const charIntroAvatarSlot: Rect = { left: 320, top: 180, right: 760, bottom: 620 };
    const disjointCharIntro = isRectDisjoint(
      falsifiedMotifToken,
      charIntroAvatarSlot
    );
    expect(
      disjointCharIntro,
      "Falsified motif token at (540, 240) must collide with character_intro avatar slot"
    ).toBe(false);

    // 2. Collides with stat_callout icon slot [460, 250, 620, 410]
    const statCalloutIconSlot = TEMPLATE_SLOT_BOUNDS.stat_callout[0];
    const disjointStatCallout = isRectDisjoint(
      falsifiedMotifToken,
      statCalloutIconSlot
    );
    expect(
      disjointStatCallout,
      "Falsified motif token at (540, 240) must collide with stat_callout icon slot"
    ).toBe(false);

    // 3. Collides with kinetic_quote container [80, 240, 1000, 1080]
    const kineticQuoteSlot: Rect = { left: 80, top: 240, right: 1000, bottom: 1080 };
    const disjointKineticQuote = isRectDisjoint(
      falsifiedMotifToken,
      kineticQuoteSlot
    );
    expect(
      disjointKineticQuote,
      "Falsified motif token at (540, 240) must collide with kinetic_quote slot"
    ).toBe(false);
  });

  it("allowed and forbidden overlay template partitions cover all 18 registry templates", () => {
    const registryTemplates = Object.keys(registry).filter(
      (k) => !k.startsWith("$")
    );
    expect(registryTemplates.length).toBe(18);

    expect(ALLOWED_OVERLAY_TEMPLATES.length).toBe(10);
    expect(FORBIDDEN_OVERLAY_TEMPLATES.length).toBe(8);

    const unionSet = new Set<string>([
      ...ALLOWED_OVERLAY_TEMPLATES,
      ...FORBIDDEN_OVERLAY_TEMPLATES,
    ]);
    expect(unionSet.size).toBe(18);

    for (const name of registryTemplates) {
      expect(
        unionSet.has(name),
        `Template ${name} must be either allowed or forbidden for overlays`
      ).toBe(true);
    }
  });
});
