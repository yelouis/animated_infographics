import { staticFile } from "remotion";
import type { FitTextSlot } from "../components/FitText";

export const CAPTION_SLOT: FitTextSlot = {
  font: "display",
  weight: 800,
  size_max: 76,
  size_min: 60,
  max_lines: 2,
  box_width: 900,
};

export const typography = {
  fonts: {
    display: "Poppins",
    body: "Inter",
  },
  weights: {
    display: {
      bold: 700,
      extraBold: 800,
    },
    body: {
      medium: 500,
      semiBold: 600,
      bold: 700,
    },
  },
  lineHeights: {
    display: 1.12,
    body: 1.25,
  },
  letterSpacing: {
    normal: 0,
  },
} as const;

export const FONT_FILES = [
  {
    family: "Poppins",
    weight: "700",
    url: staticFile("fonts/Poppins-Bold.ttf"),
  },
  {
    family: "Poppins",
    weight: "800",
    url: staticFile("fonts/Poppins-ExtraBold.ttf"),
  },
  {
    family: "Inter",
    weight: "500",
    url: staticFile("fonts/Inter-Medium.ttf"),
  },
  {
    family: "Inter",
    weight: "600",
    url: staticFile("fonts/Inter-SemiBold.ttf"),
  },
  {
    family: "Inter",
    weight: "700",
    url: staticFile("fonts/Inter-Bold.ttf"),
  },
] as const;
