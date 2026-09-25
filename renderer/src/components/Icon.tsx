import React from "react";
import { ICON_MAP } from "../generated/iconMap";
import { palette } from "../theme/palette";

export type IconName = keyof typeof ICON_MAP;

export interface IconProps {
  name: string;
  size?: number;
  color?: string;
  weight?: "thin" | "light" | "regular" | "bold" | "fill" | "duotone";
  style?: React.CSSProperties;
  className?: string;
}

export const Icon: React.FC<IconProps> = ({
  name,
  size = 32,
  color = palette.ink,
  weight = "fill",
  style,
  className,
}) => {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const IconComponent = (ICON_MAP as Record<string, React.ComponentType<any>>)[name];
  if (!IconComponent) {
    console.warn(`Icon "${name}" not found in ICON_MAP`);
    return null;
  }

  return (
    <IconComponent
      size={size}
      color={color}
      weight={weight}
      style={style}
      className={className}
    />
  );
};
