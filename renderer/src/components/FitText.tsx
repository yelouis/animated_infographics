import React, { useEffect, useLayoutEffect, useRef, useState } from "react";
import { continueRender, delayRender } from "remotion";
import { palette } from "../theme/palette";

export interface FitTextSlot {
  font: "display" | "body";
  weight: number;
  size_max: number;
  size_min: number;
  max_lines: number;
  box_width: number;
}

export interface FitTextProps {
  slot: FitTextSlot;
  text?: string;
  children?: React.ReactNode;
  sceneId: string;
  template: string;
  slotName: string;
  debug?: boolean;
  isGallery?: boolean;
  style?: React.CSSProperties;
  className?: string;
}

export const FitText: React.FC<FitTextProps> = ({
  slot,
  text,
  children,
  sceneId,
  template,
  slotName,
  debug = false,
  isGallery = false,
  style,
  className,
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const [currentSize, setCurrentSize] = useState<number>(slot.size_max);
  const [overflow, setOverflow] = useState<boolean>(false);
  const [fontsLoaded, setFontsLoaded] = useState<boolean>(false);

  const [renderHandle] = useState<number | null>(() => {
    if (typeof window !== "undefined" && typeof document !== "undefined") {
      return delayRender(`FitText sizing: ${template}:${slotName}`);
    }
    return null;
  });
  const hasContinuedRef = useRef<boolean>(false);

  useEffect(() => {
    let mounted = true;
    if (typeof document !== "undefined" && document.fonts) {
      document.fonts.ready.then(() => {
        if (mounted) {
          setFontsLoaded(true);
        }
      });
    } else {
      setFontsLoaded(true);
    }
    return () => {
      mounted = false;
      if (renderHandle !== null && !hasContinuedRef.current) {
        hasContinuedRef.current = true;
        continueRender(renderHandle);
      }
    };
  }, [renderHandle]);

  const isSingleLine = slot.max_lines === 1;
  const lineHeightMultiplier = slot.font === "display" ? 1.12 : 1.25;
  // Multi-line boxes allow 0.35 line height tolerance for font glyph metrics / ascenders
  const boxHeight = Math.ceil(
    (slot.max_lines + (isSingleLine ? 0 : 0.35)) *
      lineHeightMultiplier *
      currentSize
  );
  const fontFamily =
    slot.font === "display" ? "Poppins, sans-serif" : "Inter, sans-serif";

  useLayoutEffect(() => {
    if (!fontsLoaded || !containerRef.current) return;

    const el = containerRef.current;
    const isOverflowing = isSingleLine
      ? el.scrollWidth > el.clientWidth
      : el.scrollHeight > el.clientHeight || el.scrollWidth > el.clientWidth;

    if (isOverflowing && currentSize > slot.size_min) {
      setCurrentSize((prev) => Math.max(slot.size_min, prev - 2));
    } else {
      if (isOverflowing) {
        setOverflow(true);
        console.error(
          `OVERFLOW scene=${sceneId} template=${template} slot=${slotName}`
        );
      }
      if (renderHandle !== null && !hasContinuedRef.current) {
        hasContinuedRef.current = true;
        continueRender(renderHandle);
      }
    }
  }, [
    currentSize,
    fontsLoaded,
    text,
    children,
    sceneId,
    template,
    slotName,
    slot.size_min,
    isSingleLine,
    renderHandle,
  ]);

  const showBorder = overflow && (debug || isGallery);

  return (
    <div
      ref={containerRef}
      data-overflow={overflow ? "true" : undefined}
      data-slot={slotName}
      className={className}
      style={{
        width: slot.box_width,
        height: isSingleLine ? undefined : boxHeight,
        maxHeight: isSingleLine ? undefined : boxHeight,
        overflow: "hidden",
        whiteSpace: isSingleLine ? "nowrap" : "normal",
        fontFamily,
        fontWeight: slot.weight,
        fontSize: currentSize,
        lineHeight: lineHeightMultiplier,
        border: showBorder ? `6px solid ${palette.danger}` : undefined,
        boxSizing: "border-box",
        wordBreak: isSingleLine ? "normal" : "break-word",
        ...style,
      }}
    >
      {children !== undefined ? children : text}
    </div>
  );
};
