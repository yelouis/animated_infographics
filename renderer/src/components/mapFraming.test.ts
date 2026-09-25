import { describe, expect, it } from "vitest";
import { computeFramedBbox, createMapProjection } from "./mapFraming";

describe("mapFraming", () => {
  it("enforces minimum span for regional maps (8x6 degrees)", () => {
    // Single point: Boston at (lat 42.36, lon -71.06)
    const bbox = computeFramedBbox([{ lat: 42.36, lon: -71.06 }], "USA");

    // Before padding, span was expanded to at least 8x6.
    // With 25% padding on each side, span becomes 1.5 * minimum span:
    // lonSpan >= 8 * 1.5 = 12
    // latSpan >= 6 * 1.5 = 9
    const lonSpan = bbox.maxLon - bbox.minLon;
    const latSpan = bbox.maxLat - bbox.minLat;

    expect(lonSpan).toBeGreaterThanOrEqual(12);
    expect(latSpan).toBeGreaterThanOrEqual(9);
  });

  it("enforces minimum span for world region (60x40 degrees)", () => {
    const bbox = computeFramedBbox([{ lat: 0, lon: 0 }], "world");

    const lonSpan = bbox.maxLon - bbox.minLon;
    const latSpan = bbox.maxLat - bbox.minLat;

    // 60 * 1.5 = 90
    // 40 * 1.5 = 60
    expect(lonSpan).toBeGreaterThanOrEqual(90);
    expect(latSpan).toBeGreaterThanOrEqual(60);
  });

  it("applies 25% padding to multi-point bbox", () => {
    // 2 points with 20 lon span and 10 lat span (larger than minimum)
    const bbox = computeFramedBbox(
      [
        { lat: 10, lon: 10 },
        { lat: 20, lon: 30 },
      ],
      "AFR"
    );

    // Initial span: lon 20, lat 10
    // Padding 25% each side: span * 1.5 -> lon 30, lat 15
    const lonSpan = bbox.maxLon - bbox.minLon;
    const latSpan = bbox.maxLat - bbox.minLat;

    expect(lonSpan).toBeCloseTo(30, 2);
    expect(latSpan).toBeCloseTo(15, 2);
    expect(bbox.minLon).toBeCloseTo(10 - 5, 2);
    expect(bbox.maxLon).toBeCloseTo(30 + 5, 2);
    expect(bbox.minLat).toBeCloseTo(10 - 2.5, 2);
    expect(bbox.maxLat).toBeCloseTo(20 + 2.5, 2);
  });

  it("projects points inside the given width and height", () => {
    const points = [
      { lat: 42.36, lon: -71.06 },
      { lat: 40.71, lon: -74.01 },
    ];
    const width = 960;
    const height = 900;
    const projection = createMapProjection({
      points,
      region: "USA",
      width,
      height,
    });

    for (const p of points) {
      const projected = projection([p.lon, p.lat]);
      expect(projected).not.toBeNull();
      if (projected) {
        expect(projected[0]).toBeGreaterThanOrEqual(0);
        expect(projected[0]).toBeLessThanOrEqual(width);
        expect(projected[1]).toBeGreaterThanOrEqual(0);
        expect(projected[1]).toBeLessThanOrEqual(height);
      }
    }
  });
});
