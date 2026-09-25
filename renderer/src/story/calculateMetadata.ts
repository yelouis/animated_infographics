import Ajv from "ajv";
import type { CalculateMetadataFunction } from "remotion";
import schema from "../../../schema/timeline.schema.json";
import type { Timeline } from "../generated/contracts";

const ajv = new Ajv({ allErrors: true, strict: false });
ajv.addKeyword({ keyword: "discriminator" });
const validateTimeline = ajv.compile(schema);

export const calculateStoryMetadata: CalculateMetadataFunction<
  Record<string, unknown>
> = async ({ props }) => {
  const valid = validateTimeline(props);
  if (!valid) {
    const errors = validateTimeline.errors || [];
    const errorMessages = errors
      .slice(0, 10)
      .map((err) => `${err.instancePath || "/"}: ${err.message}`)
      .join("\n");
    throw new Error(
      `Timeline failed schema validation (${errors.length} errors):\n${errorMessages}`
    );
  }

  const timeline = props as unknown as Timeline;
  return {
    durationInFrames: timeline.duration_frames,
    fps: 30,
    width: 1080,
    height: 1920,
  };
};
