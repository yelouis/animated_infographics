import { loadFont } from "@remotion/fonts";
import React from "react";
import { Composition } from "remotion";
import { Gallery, type GalleryProps } from "./gallery/Gallery";
import type { Timeline } from "./generated/contracts";
import { calculateStoryMetadata } from "./story/calculateMetadata";
import { Story } from "./story/Story";
import { FONT_FILES } from "./theme/type";

FONT_FILES.forEach((f) => {
  loadFont({
    family: f.family,
    url: f.url,
    weight: f.weight,
  });
});

// Minimal default timeline to allow Root to mount if no inputProps passed in Remotion preview
const DEFAULT_TIMELINE: Timeline = {
  schema_version: 1,
  fps: 30,
  width: 1080,
  height: 1920,
  duration_frames: 150,
  plan_sha256: "0000000000000000000000000000000000000000000000000000000000000000",
  audio: {
    narration: { src: "fixtures/music/test_bed.wav" },
    music: null,
    sfx: [],
  },
  cast: {},
  places: {},
  set_pieces: {},
  scenes: [
    {
      id: "s001",
      template: "kinetic_quote",
      start_frame: 0,
      end_frame: 150,
      props: {
        text: "The only limit to our realization of tomorrow will be our doubts of today.",
        emphasis: ["tomorrow"],
      },
    },
  ],
  captions: {
    pages: [],
  },
};

const DEFAULT_GALLERY_PROPS: GalleryProps = {
  template: "kinetic_quote",
  variant: "typical",
};

export const Root: React.FC = () => {
  return (
    <>
      <Composition
        id="Story"
        component={Story as unknown as React.FC<Record<string, unknown>>}
        fps={30}
        width={1080}
        height={1920}
        durationInFrames={150}
        calculateMetadata={calculateStoryMetadata}
        defaultProps={DEFAULT_TIMELINE as unknown as Record<string, unknown>}
      />
      <Composition
        id="Gallery"
        component={Gallery as unknown as React.FC}
        durationInFrames={150}
        fps={30}
        width={1080}
        height={1920}
        defaultProps={DEFAULT_GALLERY_PROPS}
      />
    </>
  );
};
