import React, { useMemo } from "react";
import { geoPath } from "d3-geo";
import * as topojson from "topojson-client";
import type { Topology } from "topojson-specification";
import worldTopology from "world-atlas/countries-110m.json";
import lakesData from "../../public/geo/lakes-50m.json";
import { palette } from "../theme/palette";
import { Chip } from "./Chip";
import { NUMERIC_TO_ISO3 } from "../generated/countryCodes";
import { computeChipPlacement, createMapProjection, type GeoPoint } from "./mapFraming";

export interface MapMarker {
  placeId: string;
  label: string;
  lat: number;
  lon: number;
}

export interface MapViewProps {
  region: "world" | string;
  markers: MapMarker[];
  path?: boolean;
  width?: number; // default 960 (from 60 to 1020)
  height?: number; // default 900 (from 160 to 1060)
  radius?: number; // default 32
  style?: React.CSSProperties;
  frame?: number; // current scene frame for pulse and path animation
  renderMarkerLabel?: (
    marker: MapMarker & { x: number; y: number },
    index: number
  ) => React.ReactNode;
}

interface CountryFeature extends GeoJSON.Feature<GeoJSON.Geometry> {
  id?: string | number;
}

export const MapView: React.FC<MapViewProps> = ({
  region,
  markers,
  path = false,
  width = 960,
  height = 900,
  radius = 32,
  style,
  frame = 60,
  renderMarkerLabel,
}) => {
  const points: GeoPoint[] = useMemo(
    () => markers.map((m) => ({ lat: m.lat, lon: m.lon })),
    [markers]
  );

  const projection = useMemo(
    () => createMapProjection({ points, region, width, height }),
    [points, region, width, height]
  );

  const pathGenerator = useMemo(() => geoPath(projection), [projection]);

  const { countryFeatures, bordersPath } = useMemo(() => {
    const topo = worldTopology as unknown as Topology;
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const countries = topojson.feature(topo, topo.objects.countries as any);
    const feats = ("features" in countries
      ? countries.features
      : []) as CountryFeature[];

    const borders = topojson.mesh(
      topo,
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      topo.objects.countries as any,
      (a, b) => a !== b
    );
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const bPath = pathGenerator(borders as any) || "";

    return { countryFeatures: feats, bordersPath: bPath };
  }, [pathGenerator]);

  const lakeFeatures = useMemo(() => {
    return (lakesData as unknown as { features: GeoJSON.Feature[] }).features || [];
  }, []);


  // Projected marker positions
  const projectedMarkers = useMemo(() => {
    return markers.map((m) => {
      const coords = projection([m.lon, m.lat]);
      return {
        ...m,
        x: coords ? coords[0] : 0,
        y: coords ? coords[1] : 0,
      };
    });
  }, [markers, projection]);

  // Pulse ring animation: r 14 -> 48, 4 px highlight stroke, opacity 0.6 -> 0, period 30 frames
  const pulsePhase = (frame % 30) / 30;
  const pulseR = 14 + pulsePhase * (48 - 14);
  const pulseOpacity = 0.6 * (1 - pulsePhase);

  // Path curves if path is true and >= 2 markers
  const pathElements = useMemo(() => {
    if (!path || projectedMarkers.length < 2) return null;

    const segments: Array<{ d: string; endX: number; endY: number; angle: number }> = [];
    for (let i = 0; i < projectedMarkers.length - 1; i++) {
      const p1 = projectedMarkers[i];
      const p2 = projectedMarkers[i + 1];

      const dx = p2.x - p1.x;
      const dy = p2.y - p1.y;
      const dist = Math.sqrt(dx * dx + dy * dy);
      if (dist === 0) continue;

      // Midpoint
      const mx = (p1.x + p2.x) / 2;
      const my = (p1.y + p2.y) / 2;

      // Perpendicular unit vector (-dy/dist, dx/dist)
      const perpX = -dy / dist;
      const perpY = dx / dist;

      // Offset by 20% of segment length
      const offset = dist * 0.2;
      const cx = mx + perpX * offset;
      const cy = my + perpY * offset;

      const d = `M ${p1.x} ${p1.y} Q ${cx} ${cy} ${p2.x} ${p2.y}`;
      const angle = Math.atan2(p2.y - cy, p2.x - cx) * (180 / Math.PI);
      segments.push({ d, endX: p2.x, endY: p2.y, angle });
    }

    return segments;
  }, [path, projectedMarkers]);

  return (
    <div
      style={{
        position: "relative",
        width,
        height,
        borderRadius: radius,
        overflow: "hidden",
        backgroundColor: palette.mapSea,
        boxSizing: "border-box",
        ...style,
      }}
    >
      <svg
        width={width}
        height={height}
        style={{ position: "absolute", top: 0, left: 0, display: "block" }}
      >
        {/* Sea background */}
        <rect width={width} height={height} fill={palette.mapSea} />

        {/* Land polygons (mapRegion for region country, mapLand for others) */}
        <g>
          {countryFeatures.map((feat, idx) => {
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            const d = pathGenerator(feat as any);
            if (!d) return null;
            const iso3 = NUMERIC_TO_ISO3[String(parseInt(String(feat.id), 10))];
            const isRegion = region !== "world" && iso3 === region;
            const fill = isRegion ? palette.mapRegion : palette.mapLand;
            return <path key={idx} d={d} fill={fill} />;
          })}
        </g>

        {/* Lakes layer (drawn above land in sea colour) */}
        <g fill={palette.mapSea}>
          {lakeFeatures.map((feat, idx) => {
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            const d = pathGenerator(feat as any);
            if (!d) return null;
            return <path key={idx} d={d} />;
          })}
        </g>

        {/* Country Borders */}
        {bordersPath && (
          <path
            d={bordersPath}
            fill="none"
            stroke={palette.mapBorder}
            strokeWidth="1.5"
            strokeLinejoin="round"
          />
        )}

        {/* Path curves */}
        {pathElements &&
          pathElements.map((seg, idx) => (
            <g key={idx}>
              <path
                d={seg.d}
                fill="none"
                stroke={palette.highlight}
                strokeWidth={6}
                strokeDasharray="14 10"
                strokeDashoffset={-frame * 1.5}
                strokeLinecap="round"
              />
              {/* Arrowhead */}
              <polygon
                points="-8,-6 6,0 -8,6"
                fill={palette.highlight}
                transform={`translate(${seg.endX}, ${seg.endY}) rotate(${seg.angle})`}
              />
            </g>
          ))}

        {/* Marker Dots & Pulse Rings */}
        {projectedMarkers.map((m, idx) => (
          <g key={idx}>
            {/* Primary Pulse ring: radius 14->48, 4 px highlight stroke, opacity 0.6->0 */}
            <circle
              cx={m.x}
              cy={m.y}
              r={pulseR}
              fill="none"
              stroke={palette.highlight}
              strokeWidth={4}
              opacity={pulseOpacity}
            />
            {/* Dot: radius 14 px, fill highlight, with a 4 px bgDeep stroke */}
            <circle
              cx={m.x}
              cy={m.y}
              r={14}
              fill={palette.highlight}
              stroke={palette.bgDeep}
              strokeWidth={4}
            />
          </g>
        ))}
      </svg>

      {/* Marker Labels (Chip) */}
      {projectedMarkers.map((m, idx) => {
        const placement = computeChipPlacement({
          markerX: m.x,
          markerY: m.y,
        });

        if (renderMarkerLabel) {
          return (
            <div
              key={idx}
              style={{
                position: "absolute",
                left: m.x,
                top: placement.top,
                transform: placement.transform,
                pointerEvents: "none",
              }}
            >
              {renderMarkerLabel(m, idx)}
            </div>
          );
        }

        return (
          <div
            key={idx}
            style={{
              position: "absolute",
              left: m.x,
              top: placement.top,
              transform: placement.transform,
              pointerEvents: "none",
            }}
          >
            <Chip
              label={m.label}
              color={palette.bgDeep}
              textColor={palette.ink}
              size="sm"
            />
          </div>
        );
      })}
    </div>
  );
};

