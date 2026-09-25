import { geoMercator, geoNaturalEarth1, type GeoProjection } from "d3-geo";

export interface GeoPoint {
  lat: number;
  lon: number;
}

export interface BoundingBox {
  minLon: number;
  minLat: number;
  maxLon: number;
  maxLat: number;
}

export interface MapFramingOptions {
  points: GeoPoint[];
  region: "world" | string;
  width: number;
  height: number;
}

export function computeFramedBbox(
  points: GeoPoint[],
  region: "world" | string
): BoundingBox {
  if (points.length === 0) {
    if (region === "world") {
      return { minLon: -180, minLat: -60, maxLon: 180, maxLat: 80 };
    }
    return { minLon: -4, minLat: -3, maxLon: 4, maxLat: 3 };
  }

  let minLon = Math.min(...points.map((p) => p.lon));
  let maxLon = Math.max(...points.map((p) => p.lon));
  let minLat = Math.min(...points.map((p) => p.lat));
  let maxLat = Math.max(...points.map((p) => p.lat));

  const minLonSpan = region === "world" ? 60 : 8;
  const minLatSpan = region === "world" ? 40 : 6;

  const currentLonSpan = maxLon - minLon;
  const currentLatSpan = maxLat - minLat;

  if (currentLonSpan < minLonSpan) {
    const centerLon = (minLon + maxLon) / 2;
    minLon = centerLon - minLonSpan / 2;
    maxLon = centerLon + minLonSpan / 2;
  }

  if (currentLatSpan < minLatSpan) {
    const centerLat = (minLat + maxLat) / 2;
    minLat = centerLat - minLatSpan / 2;
    maxLat = centerLat + minLatSpan / 2;
  }

  // 25% padding on each side
  const spanLon = maxLon - minLon;
  const spanLat = maxLat - minLat;

  minLon -= spanLon * 0.25;
  maxLon += spanLon * 0.25;
  minLat -= spanLat * 0.25;
  maxLat += spanLat * 0.25;

  // Clamp latitudes
  minLat = Math.max(-85, minLat);
  maxLat = Math.min(85, maxLat);

  return { minLon, minLat, maxLon, maxLat };
}

export function createMapProjection({
  points,
  region,
  width,
  height,
}: MapFramingOptions): GeoProjection {
  const bbox = computeFramedBbox(points, region);

  const geoJsonPolygon: GeoJSON.Feature<GeoJSON.Polygon> = {
    type: "Feature",
    properties: {},
    geometry: {
      type: "Polygon",
      coordinates: [
        [
          [bbox.minLon, bbox.minLat],
          [bbox.maxLon, bbox.minLat],
          [bbox.maxLon, bbox.maxLat],
          [bbox.minLon, bbox.maxLat],
          [bbox.minLon, bbox.minLat],
        ],
      ],
    },
  };

  const projection =
    region === "world" ? geoNaturalEarth1() : geoMercator();

  projection.fitExtent(
    [
      [0, 0],
      [width, height],
    ],
    geoJsonPolygon
  );

  return projection;
}
