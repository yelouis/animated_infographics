import { describe, expect, it } from "vitest";
import React from "react";
import { renderToString } from "react-dom/server";
import { Callback } from "./callback";
import type { CallbackProps } from "../generated/contracts";
import { SceneClockProvider } from "../clock/SceneClockContext";
import type { SceneClock } from "../clock/types";

describe("Callback seen-before dots", () => {
  const props: CallbackProps = {
    motif_id: "m1",
    label: "Test Callback",
    icon: "Key",
  };

  const clockValue: SceneClock = {
    frame: 60,
    fps: 30,
    sceneFrames: 150,
    phase: "hold",
    enterProgress: 1,
    exitProgress: 0,
  };

  it("draws 0 dots when item_frames is empty", () => {
    const html = renderToString(
      <SceneClockProvider value={clockValue}>
        <Callback sceneId="s001" props={props} timing={{ item_frames: [] }} />
      </SceneClockProvider>
    );
    // Should have no dot elements (width:24px;height:24px;border-radius:50%)
    // and no dots container (top:1128px)
    expect(html).not.toContain("top:1128px");
    expect(html).not.toContain("width:24px;height:24px;border-radius:50%");
  });

  it("draws 3 dots when item_frames has 3 frames", () => {
    const html = renderToString(
      <SceneClockProvider value={clockValue}>
        <Callback sceneId="s001" props={props} timing={{ item_frames: [15, 25, 35] }} />
      </SceneClockProvider>
    );
    const dotMatches = html.match(/width:24px;height:24px;border-radius:50%/g);
    expect(dotMatches?.length).toBe(3);
    expect(html).toContain("top:1128px");
  });
});
