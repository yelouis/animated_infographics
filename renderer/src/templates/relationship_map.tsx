import React from "react";
import { interpolate } from "remotion";
import { useSceneClock } from "../clock/SceneClockContext";
import { Avatar } from "../components/Avatar";
import { FitText, type FitTextSlot } from "../components/FitText";
import type { RelationshipMapProps, TimelineSceneTiming } from "../generated/contracts";
import { useCast } from "../story/entities";
import { EASE_ENTER, EASE_EXIT } from "../theme/motion";
import { palette } from "../theme/palette";

const NAME_SLOT: FitTextSlot = {
  font: "body",
  weight: 700,
  size_max: 32,
  size_min: 24,
  max_lines: 1,
  box_width: 220,
};

const EDGE_LABEL_SLOT: FitTextSlot = {
  font: "body",
  weight: 700,
  size_max: 30,
  size_min: 24,
  max_lines: 1,
  box_width: 260,
};

export interface RelationshipMapTemplateProps {
  sceneId: string;
  props: RelationshipMapProps;
  timing?: TimelineSceneTiming;
  debug?: boolean;
  isGallery?: boolean;
}

interface NodePosition {
  x: number;
  y: number;
}

function getNodePositions(count: number): NodePosition[] {
  if (count === 2) {
    return [
      { x: 240, y: 640 },
      { x: 840, y: 640 },
    ];
  }

  const cx = 540;
  const cy = 640;
  const r = 330;
  const positions: NodePosition[] = [];

  for (let i = 0; i < count; i++) {
    // 12 o'clock (-PI / 2), clockwise
    const angle = -Math.PI / 2 + (i / count) * 2 * Math.PI;
    positions.push({
      x: cx + r * Math.cos(angle),
      y: cy + r * Math.sin(angle),
    });
  }

  return positions;
}

export const RelationshipMap: React.FC<RelationshipMapTemplateProps> = ({
  sceneId,
  props,
  debug = false,
  isGallery = false,
}) => {
  const clock = useSceneClock();

  // Exit transforms
  const exitOpacity = interpolate(clock.exitProgress, [0, 1], [1, 0]);
  const exitY = interpolate(clock.exitProgress, [0, 1], [0, -24], {
    easing: EASE_EXIT,
  });

  const positions = getNodePositions(props.cast_ids.length);
  const nodeMap = new Map<string, { pos: NodePosition; index: number }>();
  props.cast_ids.forEach((id, idx) => {
    nodeMap.set(id, { pos: positions[idx], index: idx });
  });

  const lastNodeFrame = (props.cast_ids.length - 1) * 4;

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
      {/* SVG Layer for edges */}
      <svg
        style={{
          position: "absolute",
          top: 0,
          left: 0,
          width: 1080,
          height: 1920,
          overflow: "visible",
        }}
      >
        {props.edges.map((edge, idx) => {
          const fromNode = nodeMap.get(edge.from_id);
          const toNode = nodeMap.get(edge.to_id);
          if (!fromNode || !toNode) return null;

          const edgeStart = lastNodeFrame + 4 + idx * 4;
          const drawProgress = interpolate(
            clock.frame,
            [edgeStart, edgeStart + 8],
            [0, 1],
            {
              extrapolateLeft: "clamp",
              extrapolateRight: "clamp",
            }
          );

          if (drawProgress <= 0) return null;

          const dx = toNode.pos.x - fromNode.pos.x;
          const dy = toNode.pos.y - fromNode.pos.y;
          const dist = Math.hypot(dx, dy);
          if (dist === 0) return null;

          const ux = dx / dist;
          const uy = dy / dist;

          // Trim by avatar radius (90px)
          const startX = fromNode.pos.x + ux * 90;
          const startY = fromNode.pos.y + uy * 90;
          const endX = toNode.pos.x - ux * 90;
          const endY = toNode.pos.y - uy * 90;

          // Current drawn line end
          const curEndX = startX + (endX - startX) * drawProgress;
          const curEndY = startY + (endY - startY) * drawProgress;

          const isDashed = edge.style === "dashed";
          const isBroken = edge.style === "broken";

          const midX = (startX + endX) / 2;
          const midY = (startY + endY) / 2;

          return (
            <g key={`edge-${idx}-${edge.from_id}-${edge.to_id}`}>
              <line
                x1={startX}
                y1={startY}
                x2={curEndX}
                y2={curEndY}
                stroke={palette.inkMuted}
                strokeWidth={6}
                strokeDasharray={isDashed ? "18 12" : undefined}
                strokeLinecap="round"
              />

              {isBroken && drawProgress >= 0.5 && (
                <path
                  d={`M ${midX - 12} ${midY - 12} L ${midX + 4} ${midY - 2} L ${midX - 4} ${midY + 4} L ${midX + 12} ${midY + 12}`}
                  stroke={palette.danger}
                  strokeWidth={6}
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  fill="none"
                />
              )}
            </g>
          );
        })}
      </svg>

      {/* Edge label chips */}
      {props.edges.map((edge, idx) => {
        const fromNode = nodeMap.get(edge.from_id);
        const toNode = nodeMap.get(edge.to_id);
        if (!fromNode || !toNode) return null;

        const edgeStart = lastNodeFrame + 4 + idx * 4;
        const labelOpacity = interpolate(
          clock.frame,
          [edgeStart + 4, edgeStart + 10],
          [0, 1],
          {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
          }
        );

        const midX = (fromNode.pos.x + toNode.pos.x) / 2;
        const midY = (fromNode.pos.y + toNode.pos.y) / 2;

        return (
          <div
            key={`label-${idx}`}
            style={{
              position: "absolute",
              left: midX - 130,
              top: midY - 24,
              width: 260,
              display: "flex",
              justifyContent: "center",
              opacity: labelOpacity,
            }}
          >
            <div
              style={{
                backgroundColor: palette.bgRaised,
                borderRadius: 999,
                padding: "8px 18px",
                border: `2px solid ${palette.bgDeep}`,
                boxSizing: "border-box",
                display: "inline-flex",
                alignItems: "center",
                justifyContent: "center",
              }}
            >
              <FitText
                slot={EDGE_LABEL_SLOT}
                text={edge.label}
                sceneId={sceneId}
                template="relationship_map"
                slotName={`edge_${idx}`}
                debug={debug}
                isGallery={isGallery}
                style={{
                  color: palette.ink,
                  textAlign: "center",
                  whiteSpace: "nowrap",
                }}
              />
            </div>
          </div>
        );
      })}

      {/* Nodes (Avatars + Names) */}
      {props.cast_ids.map((castId, idx) => {
        const pos = positions[idx];
        const nodeStart = idx * 4;
        const nodeOpacity = interpolate(
          clock.frame,
          [nodeStart, nodeStart + 6],
          [0, 1],
          {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
          }
        );
        const nodeScale = interpolate(
          clock.frame,
          [nodeStart, nodeStart + 8],
          [0.8, 1],
          {
            easing: EASE_ENTER,
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
          }
        );

        // Hold: nodes float, phase-offset
        const floatY = Math.sin((clock.frame / 60) * 2 * Math.PI + idx) * 5;

        return (
          <NodeItem
            key={castId}
            castId={castId}
            sceneId={sceneId}
            index={idx}
            x={pos.x}
            y={pos.y + floatY}
            opacity={nodeOpacity}
            scale={nodeScale}
            debug={debug}
            isGallery={isGallery}
          />
        );
      })}
    </div>
  );
};

interface NodeItemProps {
  castId: string;
  sceneId: string;
  index: number;
  x: number;
  y: number;
  opacity: number;
  scale: number;
  debug?: boolean;
  isGallery?: boolean;
}

const NodeItem: React.FC<NodeItemProps> = ({
  castId,
  sceneId,
  index,
  x,
  y,
  opacity,
  scale,
  debug,
  isGallery,
}) => {
  const cast = useCast(castId);
  const castColor = cast?.color || palette.castSlots[index % palette.castSlots.length];
  const castName = cast?.name || castId;
  const avatarConfig = cast?.avatar || {
    age: "adult",
    facial_hair: "none",
    glasses: false,
    hair_color: "brown",
    hair_style: "short",
    headwear: "none",
    skin: 1,
  };

  return (
    <div
      style={{
        position: "absolute",
        left: x - 110,
        top: y - 90,
        width: 220,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        opacity,
        transform: `scale(${scale})`,
        transformOrigin: "center center",
      }}
    >
      {/* 180px Avatar */}
      <div
        style={{
          width: 180,
          height: 180,
          borderRadius: "50%",
          border: `6px solid ${castColor}`,
          boxSizing: "border-box",
          overflow: "hidden",
          backgroundColor: palette.bgRaised,
        }}
      >
        <Avatar
          avatar={avatarConfig}
          color={castColor}
          size={168}
        />
      </div>

      {/* Name 12 px under avatar in cast colour */}
      <div
        style={{
          marginTop: 12,
          width: 220,
          display: "flex",
          justifyContent: "center",
        }}
      >
        <FitText
          slot={NAME_SLOT}
          text={castName}
          sceneId={sceneId}
          template="relationship_map"
          slotName={`node_${index}`}
          debug={debug}
          isGallery={isGallery}
          style={{
            textAlign: "center",
            color: castColor,
            whiteSpace: "nowrap",
          }}
        />
      </div>
    </div>
  );
};
