import React from "react";
import { useSceneClock } from "../clock/SceneClockContext";
import { Avatar } from "../components/Avatar";
import { Chip } from "../components/Chip";
import { palette } from "../theme/palette";
import type { AvatarSheetProps } from "./fixtures/avatar_sheet";

export interface AvatarSheetComponentProps {
  sceneId: string;
  props: AvatarSheetProps;
  isGallery?: boolean;
}

export const AvatarSheet: React.FC<AvatarSheetComponentProps> = ({
  props,
}) => {
  const clock = useSceneClock();

  // Subtle hold motion: floatY +- 4px with 90-frame period
  const floatY = Math.sin((clock.frame * 2 * Math.PI) / 90) * 4;

  const characters = props.characters;
  const expressions = props.expressions;

  // 4 columns: centered around 200, 430, 660, 890
  const colWidth = 230;
  const leftStart = 80;

  return (
    <div
      style={{
        position: "absolute",
        top: 0,
        left: 0,
        width: 1080,
        height: 1920,
        color: palette.ink,
        fontFamily: "Poppins, sans-serif",
        boxSizing: "border-box",
        transform: `translateY(${floatY}px)`,
      }}
    >
      {/* Title */}
      <div
        style={{
          position: "absolute",
          top: 140,
          left: 60,
          right: 60,
          textAlign: "center",
        }}
      >
        <div style={{ fontSize: 36, fontWeight: 800, color: palette.ink }}>
          {props.title || "Avatar Sheet — 8 Expressions × 4 Combinations"}
        </div>
        <div style={{ fontSize: 20, color: palette.inkMuted, marginTop: 4 }}>
          140px Dialogue Avatar Size · 8 Expressions · Age & Headwear Rules
        </div>
      </div>

      {/* Column Headers */}
      <div
        style={{
          position: "absolute",
          top: 220,
          left: leftStart + 90,
          right: 60,
          display: "flex",
          justifyContent: "space-around",
        }}
      >
        {characters.map((c) => (
          <div
            key={c.id}
            style={{
              width: colWidth,
              textAlign: "center",
              fontSize: 20,
              fontWeight: 700,
              color: palette.castSlots[c.colorSlot % palette.castSlots.length],
            }}
          >
            {c.label}
          </div>
        ))}
      </div>

      {/* Expression Rows */}
      <div
        style={{
          position: "absolute",
          top: 260,
          left: leftStart,
          right: 60,
          display: "flex",
          flexDirection: "column",
          gap: 16,
        }}
      >
        {expressions.map((expr) => (
          <div
            key={expr}
            style={{
              display: "flex",
              alignItems: "center",
              height: 155,
            }}
          >
            {/* Expression label */}
            <div style={{ width: 110, flexShrink: 0 }}>
              <Chip
                label={expr}
                color={palette.bgRaised}
                textColor={palette.inkMuted}
                size="sm"
                style={{ fontSize: 18, padding: "4px 10px" }}
              />
            </div>

            {/* Avatars in row */}
            <div
              style={{
                display: "flex",
                flex: 1,
                justifyContent: "space-around",
              }}
            >
              {characters.map((c) => (
                <div
                  key={`${c.id}-${expr}`}
                  style={{
                    width: colWidth,
                    display: "flex",
                    justifyContent: "center",
                    alignItems: "center",
                  }}
                >
                  <Avatar
                    avatar={c.avatar}
                    colorSlot={c.colorSlot}
                    expression={expr}
                    size={140}
                  />
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
