import React, { useRef, useState, useLayoutEffect } from "react";
import { interpolate } from "remotion";
import { useSceneClock } from "../clock/SceneClockContext";
import { Avatar } from "../components/Avatar";
import { FitText, type FitTextSlot } from "../components/FitText";
import type { TextThreadProps, TimelineSceneTiming } from "../generated/contracts";
import { useCast } from "../story/entities";
import { EASE_ENTER, EASE_EXIT } from "../theme/motion";
import { palette } from "../theme/palette";

const CONTACT_SLOT: FitTextSlot = {
  font: "body",
  weight: 700,
  size_max: 40,
  size_min: 30,
  max_lines: 1,
  box_width: 560,
};

const MESSAGE_SLOT: FitTextSlot = {
  font: "body",
  weight: 600,
  size_max: 38,
  size_min: 30,
  max_lines: 4,
  box_width: 476,
};

export interface TextThreadTemplateProps {
  sceneId: string;
  props: TextThreadProps;
  timing?: TimelineSceneTiming;
  debug?: boolean;
  isGallery?: boolean;
}

export const TextThread: React.FC<TextThreadTemplateProps> = ({
  sceneId,
  props,
  timing,
  debug = false,
  isGallery = false,
}) => {
  const clock = useSceneClock();
  const contactCast = useCast(props.contact_cast_id);

  // Exit transforms
  const exitOpacity = interpolate(clock.exitProgress, [0, 1], [1, 0]);
  const exitY = interpolate(clock.exitProgress, [0, 1], [0, -24], {
    easing: EASE_EXIT,
  });

  // Hold motion: phone floats 6px, period 90 frames
  const floatY = Math.sin((clock.frame / 90) * 2 * Math.PI) * 6;

  const itemFrames = timing?.item_frames || [];

  // Measurement for scrolling container
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const [scrollY, setScrollY] = useState(0);

  useLayoutEffect(() => {
    if (scrollContainerRef.current) {
      const el = scrollContainerRef.current;
      const maxHeight = 780; // available vertical space in phone body (top 140 to 920)
      if (el.scrollHeight > maxHeight) {
        setScrollY(el.scrollHeight - maxHeight);
      } else {
        setScrollY(0);
      }
    }
  }, [clock.frame, props.messages]);

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
      {/* Phone Body 760x1000 at (160, 160), radius 64, fill #0E1830, 6px bgRaised border */}
      <div
        style={{
          position: "absolute",
          left: 160,
          top: 160,
          width: 760,
          height: 1000,
          borderRadius: 64,
          backgroundColor: "#0E1830",
          border: `6px solid ${palette.bgRaised}`,
          boxSizing: "border-box",
          overflow: "hidden",
          transform: `translateY(${floatY}px)`,
          display: "flex",
          flexDirection: "column",
        }}
      >
        {/* Header bar 120px */}
        <div
          style={{
            height: 120,
            borderBottom: `2px solid ${palette.bgRaised}`,
            padding: "0 32px",
            display: "flex",
            alignItems: "center",
            gap: 20,
            backgroundColor: "#0B1327",
            zIndex: 10,
          }}
        >
          {props.contact_cast_id && (
            <div
              style={{
                width: 64,
                height: 64,
                borderRadius: "50%",
                overflow: "hidden",
                border: `3px solid ${contactCast?.color || palette.castSlots[0]}`,
                backgroundColor: palette.bgRaised,
                flexShrink: 0,
              }}
            >
              <Avatar
                avatar={
                  contactCast?.avatar || {
                    age: "adult",
                    facial_hair: "none",
                    glasses: false,
                    hair_color: "brown",
                    hair_style: "short",
                    headwear: "none",
                    skin: 1,
                  }
                }
                color={contactCast?.color || palette.castSlots[0]}
                size={58}
              />
            </div>
          )}

          <div style={{ flex: 1 }}>
            <FitText
              slot={CONTACT_SLOT}
              text={props.contact_name}
              sceneId={sceneId}
              template="text_thread"
              slotName="contact"
              debug={debug}
              isGallery={isGallery}
              style={{
                color: palette.ink,
                fontWeight: 700,
              }}
            />
          </div>
        </div>

        {/* Message Container with scroll */}
        <div
          style={{
            flex: 1,
            position: "relative",
            overflow: "hidden",
            padding: "24px 32px",
          }}
        >
          <div
            ref={scrollContainerRef}
            style={{
              display: "flex",
              flexDirection: "column",
              gap: 24,
              transform: `translateY(-${scrollY}px)`,
            }}
          >
            {props.messages.map((msg, idx) => {
              const startFrame = itemFrames[idx] ?? idx * 18;
              const isThem = msg.from === "them";

              // Typing indicator precedes "them" messages by 12 frames
              const showTyping =
                isThem &&
                clock.frame >= startFrame - 12 &&
                clock.frame < startFrame;
              const showMessage = clock.frame >= startFrame;

              const msgOpacity = interpolate(
                clock.frame,
                [startFrame, startFrame + 6],
                [0, 1],
                {
                  extrapolateLeft: "clamp",
                  extrapolateRight: "clamp",
                }
              );
              const msgY = interpolate(
                clock.frame,
                [startFrame, startFrame + 6],
                [16, 0],
                {
                  easing: EASE_ENTER,
                  extrapolateLeft: "clamp",
                  extrapolateRight: "clamp",
                }
              );

              return (
                <div
                  key={`${idx}-${msg.text.slice(0, 10)}`}
                  style={{
                    display: "flex",
                    justifyContent: isThem ? "flex-start" : "flex-end",
                  }}
                >
                  {showTyping && (
                    <div
                      style={{
                        backgroundColor: palette.bgRaised,
                        borderRadius: 24,
                        padding: "16px 24px",
                        display: "flex",
                        alignItems: "center",
                        gap: 8,
                      }}
                    >
                      <TypingDot delay={0} clockFrame={clock.frame} />
                      <TypingDot delay={4} clockFrame={clock.frame} />
                      <TypingDot delay={8} clockFrame={clock.frame} />
                    </div>
                  )}

                  {showMessage && (
                    <div
                      style={{
                        maxWidth: 540,
                        backgroundColor: isThem
                          ? palette.bgRaised
                          : palette.castSlots[7], // slot 7 (sky)
                        borderRadius: 24,
                        padding: "18px 24px",
                        boxSizing: "border-box",
                        opacity: msgOpacity,
                        transform: `translateY(${msgY}px)`,
                      }}
                    >
                      <FitText
                        slot={MESSAGE_SLOT}
                        text={msg.text}
                        sceneId={sceneId}
                        template="text_thread"
                        slotName={`message_${idx}`}
                        debug={debug}
                        isGallery={isGallery}
                        style={{
                          color: isThem ? palette.ink : palette.bg,
                          lineHeight: 1.25,
                        }}
                      />
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
};

const TypingDot: React.FC<{ delay: number; clockFrame: number }> = ({
  delay,
  clockFrame,
}) => {
  const dotProgress = (clockFrame + delay) % 18;
  const bounceY = dotProgress < 9 ? -4 : 0;

  return (
    <div
      style={{
        width: 10,
        height: 10,
        borderRadius: "50%",
        backgroundColor: palette.inkMuted,
        transform: `translateY(${bounceY}px)`,
      }}
    />
  );
};
