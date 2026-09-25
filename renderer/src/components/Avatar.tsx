import React from "react";
import type { AvatarConfig } from "../generated/contracts";
import { palette } from "../theme/palette";

export type AvatarExpression =
  | "neutral"
  | "happy"
  | "sad"
  | "angry"
  | "shocked"
  | "confused"
  | "smug"
  | "nervous";

export interface AvatarProps {
  avatar: AvatarConfig;
  colorSlot?: number;
  color?: string;
  expression?: AvatarExpression;
  size?: number;
  style?: React.CSSProperties;
  className?: string;
}

const SKIN_TONES = [
  "#F9D7C0", // 0
  "#EDB98A", // 1
  "#D08B5B", // 2
  "#AE5D29", // 3
  "#7B4A2E", // 4
  "#4A2F22", // 5
] as const;

const HAIR_COLORS: Record<string, string> = {
  black: "#1C1C1C",
  brown: "#5A3825",
  blonde: "#E6C36A",
  red: "#B5462B",
  gray: "#9AA0A6",
  white: "#E8E8E8",
};

export const Avatar: React.FC<AvatarProps> = ({
  avatar,
  colorSlot = 0,
  color,
  expression = "neutral",
  size = 200,
  style,
  className,
}) => {
  const castColor =
    color || palette.castSlots[colorSlot % palette.castSlots.length];
  const skinColor = SKIN_TONES[Math.max(0, Math.min(5, avatar.skin))] || SKIN_TONES[0];

  // Elder rule: forces hair to gray if black or brown
  let resolvedHairColorName = avatar.hair_color;
  if (avatar.age === "elder" && (resolvedHairColorName === "black" || resolvedHairColorName === "brown")) {
    resolvedHairColorName = "gray";
  }
  const hairColor = HAIR_COLORS[resolvedHairColorName] || HAIR_COLORS.black;

  // Age scaling
  const isChild = avatar.age === "child";
  const isElder = avatar.age === "elder";

  // Head center: (100, 84), r=48
  // Body: half-ellipse at bottom
  return (
    <svg
      viewBox="0 0 200 200"
      width={size}
      height={size}
      className={className}
      style={{ display: "block", overflow: "visible", ...style }}
    >
      {/* --- Body Group (scaled down for child) --- */}
      <g
        transform={
          isChild ? "translate(100, 200) scale(0.8) translate(-100, -200)" : undefined
        }
      >
        {/* Shirt / Torso (half-ellipse at bottom) */}
        <path
          d="M 30 200 A 70 55 0 0 1 170 200 Z"
          fill={castColor}
        />
        {/* Neck */}
        <rect x="88" y="120" width="24" height="26" fill={skinColor} rx="6" />
      </g>

      {/* --- Head and Features Group (scaled up for child) --- */}
      <g
        transform={
          isChild ? "translate(100, 84) scale(1.12) translate(-100, -84)" : undefined
        }
      >
        {/* Hair - Back (for long hair / ponytail) */}
        {avatar.headwear !== "headscarf" && (
          <>
            {avatar.hair_style === "long" && (
              <path
                d="M 46 84 C 42 120 40 160 55 180 C 60 186 70 186 72 170 C 65 140 60 110 60 84 Z"
                fill={hairColor}
              />
            )}
            {avatar.hair_style === "long" && (
              <path
                d="M 154 84 C 158 120 160 160 145 180 C 140 186 130 186 128 170 C 135 140 140 110 140 84 Z"
                fill={hairColor}
              />
            )}
            {avatar.hair_style === "ponytail" && (
              <path
                d="M 144 80 C 165 85 185 110 180 145 C 175 150 168 145 168 135 C 170 115 155 96 142 90 Z"
                fill={hairColor}
              />
            )}
            {avatar.hair_style === "bun" && (
              <circle cx="100" cy="30" r="20" fill={hairColor} />
            )}
          </>
        )}

        {/* Head Circle */}
        <circle cx="100" cy="84" r="48" fill={skinColor} />

        {/* Ears */}
        <circle cx="51" cy="86" r="10" fill={skinColor} />
        <circle cx="149" cy="86" r="10" fill={skinColor} />

        {/* Hair - Front / Top */}
        {avatar.headwear !== "headscarf" && avatar.hair_style !== "bald" && (
          <g fill={hairColor}>
            {avatar.hair_style === "short" && (
              <path d="M 52 84 C 52 46 72 36 100 36 C 128 36 148 46 148 84 C 144 68 130 52 100 52 C 70 52 56 68 52 84 Z" />
            )}
            {avatar.hair_style === "long" && (
              <path d="M 52 84 C 52 46 72 36 100 36 C 128 36 148 46 148 84 C 144 66 128 50 100 50 C 72 50 56 66 52 84 Z" />
            )}
            {avatar.hair_style === "bun" && (
              <path d="M 52 84 C 52 46 72 36 100 36 C 128 36 148 46 148 84 C 144 66 128 52 100 52 C 72 52 56 66 52 84 Z" />
            )}
            {avatar.hair_style === "curly" && (
              <path d="M 50 86 C 44 76 46 60 56 54 C 54 42 66 34 78 36 C 88 28 104 28 114 34 C 126 30 140 40 142 50 C 152 56 156 72 148 84 C 140 62 122 50 100 50 C 78 50 60 62 50 86 Z" />
            )}
            {avatar.hair_style === "ponytail" && (
              <path d="M 52 84 C 52 46 72 36 100 36 C 128 36 148 46 148 84 C 144 66 128 50 100 50 C 72 50 56 66 52 84 Z" />
            )}
          </g>
        )}

        {/* Headscarf (covers hair, in cast color) */}
        {avatar.headwear === "headscarf" && (
          <path
            d="M 48 88 C 46 44 68 34 100 34 C 132 34 154 44 152 88 C 150 120 142 148 132 154 C 124 140 114 136 100 136 C 86 136 76 140 68 154 C 58 148 50 120 48 88 Z"
            fill={castColor}
          />
        )}

        {/* Elder Wrinkles (two 3px inkMuted lines) */}
        {isElder && (
          <g stroke={palette.inkMuted} strokeWidth="3" strokeLinecap="round" opacity={0.85}>
            <line x1="84" y1="58" x2="116" y2="58" />
            <line x1="88" y1="65" x2="112" y2="65" />
          </g>
        )}

        {/* Eyes (two r 5 dots at (82, 86) and (118, 86)) */}
        <circle cx="82" cy="86" r="5" fill="#1C1C1C" />
        <circle cx="118" cy="86" r="5" fill="#1C1C1C" />

        {/* Brows and Mouth by Expression (5px round-cap strokes) */}
        <g stroke="#1C1C1C" strokeWidth="5" strokeLinecap="round" fill="none">
          {expression === "neutral" && (
            <>
              {/* Brows */}
              <path d="M 73 75 Q 82 72 91 75" />
              <path d="M 109 75 Q 118 72 127 75" />
              {/* Mouth */}
              <line x1="91" y1="114" x2="109" y2="114" />
            </>
          )}

          {expression === "happy" && (
            <>
              {/* High arched brows */}
              <path d="M 73 73 Q 82 68 91 73" />
              <path d="M 109 73 Q 118 68 127 73" />
              {/* Big smile curve */}
              <path d="M 88 110 Q 100 124 112 110" />
            </>
          )}

          {expression === "sad" && (
            <>
              {/* Angled up in the center */}
              <path d="M 73 77 Q 82 74 91 71" />
              <path d="M 109 71 Q 118 74 127 77" />
              {/* Frown curve */}
              <path d="M 89 118 Q 100 108 111 118" />
            </>
          )}

          {expression === "angry" && (
            <>
              {/* Steep downward slant toward center */}
              <path d="M 73 70 L 91 77" />
              <path d="M 109 77 L 127 70" />
              {/* Tight straight mouth */}
              <line x1="91" y1="115" x2="109" y2="115" />
            </>
          )}

          {expression === "shocked" && (
            <>
              {/* Very high brows */}
              <path d="M 73 67 Q 82 62 91 67" />
              <path d="M 109 67 Q 118 62 127 67" />
              {/* Open round O mouth */}
              <ellipse cx="100" cy="114" rx="8" ry="10" stroke="#1C1C1C" strokeWidth="5" fill="#1C1C1C" />
            </>
          )}

          {expression === "confused" && (
            <>
              {/* One raised, one flat/furrowed brow */}
              <path d="M 73 68 Q 82 63 91 68" />
              <path d="M 109 76 L 127 73" />
              {/* Asymmetric / wavy mouth */}
              <path d="M 90 114 Q 96 110 100 114 T 110 114" />
            </>
          )}

          {expression === "smug" && (
            <>
              {/* One slightly arched brow */}
              <path d="M 73 71 Q 82 68 91 72" />
              <path d="M 109 73 Q 118 71 127 74" />
              {/* Half-smirk tilted up on one side */}
              <path d="M 90 115 Q 100 116 112 108" />
            </>
          )}

          {expression === "nervous" && (
            <>
              {/* Worried brows */}
              <path d="M 73 76 Q 82 73 91 72" />
              <path d="M 109 72 Q 118 73 127 76" />
              {/* Jittery zigzag / wavy mouth */}
              <path d="M 89 114 Q 94 117 98 113 Q 102 117 106 113 Q 109 116 112 113" />
            </>
          )}
        </g>

        {/* Facial Hair (beard / mustache in hairColor) */}
        {avatar.facial_hair === "mustache" && (
          <path
            d="M 86 106 Q 100 102 114 106 Q 100 111 86 106 Z"
            fill={hairColor}
          />
        )}
        {avatar.facial_hair === "beard" && (
          <path
            d="M 68 96 C 68 132 82 142 100 142 C 118 142 132 132 132 96 C 124 104 114 108 100 108 C 86 108 76 104 68 96 Z"
            fill={hairColor}
          />
        )}

        {/* Glasses (two 18px round rims, 4px #1C1C1C) */}
        {avatar.glasses && (
          <g stroke="#1C1C1C" strokeWidth="4" fill="none">
            <circle cx="82" cy="86" r="16" />
            <circle cx="118" cy="86" r="16" />
            <line x1="98" y1="86" x2="102" y2="86" />
            <line x1="56" y1="84" x2="66" y2="86" />
            <line x1="134" y1="86" x2="144" y2="84" />
          </g>
        )}

        {/* Headwear */}
        {avatar.headwear === "hat" && (
          <g>
            {/* Brim */}
            <path d="M 40 50 Q 100 42 160 50 L 152 56 Q 100 48 48 56 Z" fill="#2A3A5E" />
            {/* Crown */}
            <path d="M 66 52 C 66 26 80 22 100 22 C 120 22 134 26 134 52 Z" fill="#2A3A5E" />
            {/* Hat band in castColor */}
            <path d="M 66 48 Q 100 44 134 48 L 134 52 Q 100 48 66 52 Z" fill={castColor} />
          </g>
        )}

        {avatar.headwear === "crown" && (
          <g fill={palette.highlight}>
            {/* Royal crown with 3 peaks */}
            <path d="M 70 48 L 74 24 L 88 38 L 100 20 L 112 38 L 126 24 L 130 48 Z" />
            <circle cx="74" cy="22" r="3" fill="#FFF" />
            <circle cx="100" cy="18" r="3.5" fill="#FFF" />
            <circle cx="126" cy="22" r="3" fill="#FFF" />
          </g>
        )}

        {avatar.headwear === "military_cap" && (
          <g>
            {/* Crown */}
            <path d="M 62 48 C 62 26 80 24 100 24 C 120 24 138 26 138 48 Z" fill="#3D4A3E" />
            {/* Visor */}
            <path d="M 58 48 Q 100 42 142 48 L 138 54 Q 100 48 62 54 Z" fill="#1C1C1C" />
            {/* Gold badge */}
            <circle cx="100" cy="36" r="5" fill={palette.highlight} />
          </g>
        )}

        {avatar.headwear === "helmet" && (
          <g fill="#7A8B99">
            {/* Dome shell */}
            <path d="M 52 80 C 50 36 70 30 100 30 C 130 30 150 36 148 80 C 146 64 126 50 100 50 C 74 50 54 64 52 80 Z" />
            {/* Rim band */}
            <path d="M 50 78 Q 100 68 150 78 L 148 84 Q 100 74 52 84 Z" fill="#5F6F7C" />
          </g>
        )}
      </g>
    </svg>
  );
};
