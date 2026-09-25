import React from "react";
import { interpolate } from "remotion";
import { useSceneClock } from "../clock/SceneClockContext";
import { Avatar, type AvatarExpression } from "../components/Avatar";
import { Bubble } from "../components/Bubble";
import { FitText, type FitTextSlot } from "../components/FitText";
import type { DialogueProps, TimelineSceneTiming } from "../generated/contracts";
import { useCast } from "../story/entities";
import { EASE_ENTER, EASE_EXIT } from "../theme/motion";
import { palette } from "../theme/palette";

const LINE_SLOT: FitTextSlot = {
  font: "body",
  weight: 700,
  size_max: 44,
  size_min: 32,
  max_lines: 4,
  box_width: 628,
};

export interface DialogueTemplateProps {
  sceneId: string;
  props: DialogueProps;
  timing?: TimelineSceneTiming;
  debug?: boolean;
  isGallery?: boolean;
}

const TONE_TO_EXPRESSION: Record<string, AvatarExpression> = {
  neutral: "neutral",
  angry: "angry",
  happy: "happy",
  sad: "sad",
  shocked: "shocked",
  sarcastic: "smug",
};

export const Dialogue: React.FC<DialogueTemplateProps> = ({
  sceneId,
  props,
  timing,
  debug = false,
  isGallery = false,
}) => {
  const clock = useSceneClock();

  // Exit transforms
  const exitOpacity = interpolate(clock.exitProgress, [0, 1], [1, 0]);
  const exitY = interpolate(clock.exitProgress, [0, 1], [0, -24], {
    easing: EASE_EXIT,
  });

  // Calculate distinct speakers to alternate left / right
  const speakerOrder: string[] = [];
  props.lines.forEach((line) => {
    if (!speakerOrder.includes(line.cast_id)) {
      speakerOrder.push(line.cast_id);
    }
  });

  const itemFrames = timing?.item_frames || [];

  // Determine currently active latest speaker line
  let activeLineIdx = -1;
  props.lines.forEach((_, idx) => {
    const startFrame = itemFrames[idx] ?? idx * 15;
    if (clock.frame >= startFrame) {
      activeLineIdx = idx;
    }
  });

  // Hold motion: float across scene for hold motion verification
  const holdFloatY = Math.sin((clock.frame / 75) * 2 * Math.PI) * 4;

  let currentY = 200;

  return (
    <div
      style={{
        position: "absolute",
        top: 0,
        left: 0,
        width: 1080,
        height: 1920,
        opacity: exitOpacity,
        transform: `translateY(${exitY}px)`,
        pointerEvents: "none",
      }}
    >
      <div
        style={{
          position: "absolute",
          top: 0,
          left: 0,
          width: 1080,
          height: 1920,
          transform: `translateY(${holdFloatY}px)`,
        }}
      >
        {props.lines.map((line, idx) => {
          const speakerIdx = speakerOrder.indexOf(line.cast_id);
          const isLeft = speakerIdx % 2 === 0;
          const startFrame = itemFrames[idx] ?? idx * 15;
          const isVisible = clock.frame >= startFrame;

          const lineOpacity = interpolate(
            clock.frame,
            [startFrame, startFrame + 6],
            [0, 1],
            {
              extrapolateLeft: "clamp",
              extrapolateRight: "clamp",
            }
          );
          const bubbleScale = interpolate(
            clock.frame,
            [startFrame, startFrame + 6],
            [0.9, 1],
            {
              easing: EASE_ENTER,
              extrapolateLeft: "clamp",
              extrapolateRight: "clamp",
            }
          );

          // Speaker mouth animation on the active line
          const isSpeaking =
            activeLineIdx === idx &&
            Math.floor(clock.frame / 6) % 2 === 0;

          const rowY = currentY;
          currentY += 280; // row height + 40px gap

          return (
            <DialogueRow
              key={`${idx}-${line.cast_id}`}
              line={line}
              sceneId={sceneId}
              slotIndex={idx}
              isLeft={isLeft}
              y={rowY}
              opacity={isVisible ? lineOpacity : 0}
              bubbleScale={bubbleScale}
              isSpeaking={isSpeaking}
              debug={debug}
              isGallery={isGallery}
            />
          );
        })}
      </div>
    </div>
  );
};

interface DialogueRowProps {
  line: DialogueProps["lines"][number];
  sceneId: string;
  slotIndex: number;
  isLeft: boolean;
  y: number;
  opacity: number;
  bubbleScale: number;
  isSpeaking: boolean;
  debug?: boolean;
  isGallery?: boolean;
}

const DialogueRow: React.FC<DialogueRowProps> = ({
  line,
  sceneId,
  slotIndex,
  isLeft,
  y,
  opacity,
  bubbleScale,
  isSpeaking,
  debug,
  isGallery,
}) => {
  const cast = useCast(line.cast_id);
  const castColor = cast?.color || palette.castSlots[slotIndex % palette.castSlots.length];
  const avatarConfig = cast?.avatar || {
    age: "adult",
    facial_hair: "none",
    glasses: false,
    hair_color: "brown",
    hair_style: "short",
    headwear: "none",
    skin: 1,
  };

  const expression = TONE_TO_EXPRESSION[line.tone || "neutral"] || "neutral";

  return (
    <div
      style={{
        position: "absolute",
        left: 60,
        top: y,
        width: 960,
        display: "flex",
        flexDirection: isLeft ? "row" : "row-reverse",
        alignItems: "flex-start",
        gap: 24,
        opacity,
      }}
    >
      {/* 140px Avatar */}
      <div
        style={{
          width: 140,
          height: 140,
          borderRadius: "50%",
          border: `6px solid ${castColor}`,
          boxSizing: "border-box",
          overflow: "hidden",
          backgroundColor: palette.bgRaised,
          flexShrink: 0,
        }}
      >
        <Avatar
          avatar={avatarConfig}
          color={castColor}
          size={128}
          expression={expression}
          isMouthOpen={isSpeaking}
        />
      </div>

      {/* Speech bubble */}
      <div
        style={{
          maxWidth: 700,
          transform: `scale(${bubbleScale})`,
          transformOrigin: isLeft ? "left top" : "right top",
        }}
      >
        <Bubble
          color={castColor}
          textColor={palette.bg}
          tail={isLeft ? "left" : "right"}
          style={{
            borderRadius: 36,
            padding: "28px 36px",
          }}
        >
          <FitText
            slot={LINE_SLOT}
            text={line.text}
            sceneId={sceneId}
            template="dialogue"
            slotName={`line_${slotIndex}`}
            debug={debug}
            isGallery={isGallery}
            style={{
              color: palette.bg,
              lineHeight: 1.25,
            }}
          />
        </Bubble>
      </div>
    </div>
  );
};
