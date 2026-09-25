import React from "react";
import { useGlobalClock } from "../clock/GlobalClockContext";
import { palette } from "../theme/palette";

export const Background: React.FC = () => {
  const clock = useGlobalClock();
  const frame = clock.frame;

  // Circle 1: starting (260, 520), r=520, period 12s (360 frames), amp 40px
  const t1 = (frame * 2 * Math.PI) / (12 * 30);
  const cx1 = 260 + 40 * Math.sin(t1);
  const cy1 = 520 + 40 * Math.cos(t1);

  // Circle 2: starting (860, 1320), r=380, period 17s (510 frames), amp 40px
  const t2 = (frame * 2 * Math.PI) / (17 * 30);
  const cx2 = 860 + 40 * Math.sin(t2);
  const cy2 = 1320 + 40 * Math.cos(t2);

  return (
    <div
      style={{
        position: "absolute",
        top: 0,
        left: 0,
        width: 1080,
        height: 1920,
        overflow: "hidden",
        backgroundColor: palette.bg,
        pointerEvents: "none",
      }}
    >
      <svg
        width={1080}
        height={1920}
        viewBox="0 0 1080 1920"
        style={{ position: "absolute", top: 0, left: 0 }}
      >
        <defs>
          <radialGradient id="bg-vignette" cx="50%" cy="50%" r="70%">
            <stop offset="0%" stopColor="#1A2A4A" />
            <stop offset="100%" stopColor={palette.bgDeep} />
          </radialGradient>
          <filter id="soft-blur" x="-50%" y="-50%" width="200%" height="200%">
            <feGaussianBlur stdDeviation="80" />
          </filter>
        </defs>

        <rect width={1080} height={1920} fill="url(#bg-vignette)" />

        <circle
          cx={cx1}
          cy={cy1}
          r={520}
          fill={palette.bgRaised}
          opacity={0.55}
          filter="url(#soft-blur)"
        />

        <circle
          cx={cx2}
          cy={cy2}
          r={380}
          fill={palette.bgRaised}
          opacity={0.55}
          filter="url(#soft-blur)"
        />
      </svg>
    </div>
  );
};
