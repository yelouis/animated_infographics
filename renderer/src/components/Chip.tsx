import React from "react";
import { palette } from "../theme/palette";
import { Icon } from "./Icon";

export interface ChipProps {
  label?: string;
  icon?: string;
  color?: string;
  textColor?: string;
  size?: "sm" | "md" | "lg";
  style?: React.CSSProperties;
  children?: React.ReactNode;
}

export const Chip: React.FC<ChipProps> = ({
  label,
  icon,
  color = palette.bgRaised,
  textColor = palette.ink,
  size = "md",
  style,
  children,
}) => {
  const padX = size === "sm" ? 12 : size === "lg" ? 24 : 16;
  const padY = size === "sm" ? 6 : size === "lg" ? 12 : 8;
  const fontSize = size === "sm" ? 24 : size === "lg" ? 36 : 28;
  const iconSize = size === "sm" ? 20 : size === "lg" ? 32 : 24;

  return (
    <div
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 8,
        backgroundColor: color,
        color: textColor,
        borderRadius: 9999,
        padding: `${padY}px ${padX}px`,
        fontSize,
        fontFamily: "Poppins, sans-serif",
        fontWeight: 700,
        lineHeight: 1.12,
        userSelect: "none",
        ...style,
      }}
    >
      {icon && <Icon name={icon} size={iconSize} color={textColor} />}
      {label && <span>{label}</span>}
      {children}
    </div>
  );
};
