import { describe, expect, it } from "vitest";
import React from "react";
import { renderToString } from "react-dom/server";
import { Avatar, type AvatarExpression } from "./Avatar";
import type { AvatarConfig } from "../generated/contracts";

const baseAvatar: AvatarConfig = {
  skin: 1,
  hair_style: "short",
  hair_color: "black",
  facial_hair: "none",
  headwear: "none",
  glasses: false,
  age: "adult",
};

describe("Avatar", () => {
  it("renders with default props", () => {
    const html = renderToString(<Avatar avatar={baseAvatar} />);
    expect(html).toContain("<svg");
    expect(html).toContain('viewBox="0 0 200 200"');
    // Skin tone 1: #EDB98A
    expect(html).toContain("#EDB98A");
  });

  it("applies elder rule: forces black or brown hair to gray", () => {
    const elderBlack = renderToString(
      <Avatar avatar={{ ...baseAvatar, age: "elder", hair_color: "black" }} />
    );
    // Gray is #9AA0A6
    expect(elderBlack).toContain("#9AA0A6");
    // Wrinkle lines present
    expect(elderBlack).toContain("stroke-width=\"3\"");

    const elderBrown = renderToString(
      <Avatar avatar={{ ...baseAvatar, age: "elder", hair_color: "brown" }} />
    );
    expect(elderBrown).toContain("#9AA0A6");

    // Blonde elder stays blonde (#E6C36A)
    const elderBlonde = renderToString(
      <Avatar avatar={{ ...baseAvatar, age: "elder", hair_color: "blonde" }} />
    );
    expect(elderBlonde).toContain("#E6C36A");
  });

  it("applies child scaling (head scale 1.12, body scale 0.8)", () => {
    const childHtml = renderToString(
      <Avatar avatar={{ ...baseAvatar, age: "child" }} />
    );
    expect(childHtml).toContain("scale(1.12)");
    expect(childHtml).toContain("scale(0.8)");
  });

  it("renders all 8 expressions without error", () => {
    const expressions: AvatarExpression[] = [
      "neutral",
      "happy",
      "sad",
      "angry",
      "shocked",
      "confused",
      "smug",
      "nervous",
    ];

    for (const expr of expressions) {
      const html = renderToString(
        <Avatar avatar={baseAvatar} expression={expr} />
      );
      expect(html).toContain("<svg");
      expect(html).toContain('stroke-width="5"');
    }
  });

  it("renders crown with highlight color", () => {
    const crownHtml = renderToString(
      <Avatar avatar={{ ...baseAvatar, headwear: "crown" }} />
    );
    // highlight color #FFD166
    expect(crownHtml).toContain("#FFD166");
  });

  it("renders glasses when glasses: true", () => {
    const glassesHtml = renderToString(
      <Avatar avatar={{ ...baseAvatar, glasses: true }} />
    );
    expect(glassesHtml).toContain('stroke-width="4"');
  });
});
