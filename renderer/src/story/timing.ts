import type { TimelineSceneTiming } from "../generated/contracts";

export function getDefaultTiming(
  template: string,
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  props: any,
  sceneFrames = 150
): TimelineSceneTiming {
  const STAGGER_FRAMES = 4;
  const MAX_COUNT_FRAMES = 24;

  if (template === "stat_callout") {
    const countFrames = Math.max(
      0,
      Math.min(MAX_COUNT_FRAMES, Math.floor(0.4 * sceneFrames))
    );
    return { count_frames: countFrames, item_frames: [] };
  }

  let n = 0;
  let spread = 0.0;
  if (template === "icon_list") {
    n = props?.items?.length || 0;
    spread = 0.5;
  } else if (template === "cause_effect") {
    n = props?.nodes?.length || 0;
    spread = 0.6;
  } else if (template === "comparison") {
    n = 2;
    spread = 0.3;
  } else if (template === "dialogue") {
    n = props?.lines?.length || 0;
    spread = 0.6;
  } else if (template === "text_thread") {
    n = props?.messages?.length || 0;
    spread = 0.7;
  } else if (template === "map_focus") {
    n = props?.markers?.length || 0;
    spread = 0.3;
  } else if (template === "timeline") {
    n = props?.events?.length || 0;
    spread = 0.6;
  }

  if (n > 0 && spread > 0) {
    const step = Math.max(
      STAGGER_FRAMES,
      Math.floor((sceneFrames * spread) / n)
    );
    const itemFrames = Array.from({ length: n }, (_, i) => i * step);
    return { item_frames: itemFrames };
  }

  return { item_frames: [] };
}
