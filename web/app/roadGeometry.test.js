import { describe, expect, test } from "bun:test";
import {
  DEFAULT_SUMBAWA_ORIGIN,
  geoToLocalPoint,
  localToLatLon,
  nearestRoadMatch,
  parseRoadMapPayload,
  roadBufferState,
  roadClassLabel,
} from "./roadGeometry";

const segments = [
  { id: "north", ax: 0, ay: 1000, bx: 1000, by: 1000, road_class: 1 },
  { id: "south", ax: 0, ay: 0, bx: 1000, by: 0, road_class: 3 },
];

describe("nearestRoadMatch", () => {
  test("selects the closest segment and projects onto it", () => {
    const match = nearestRoadMatch({ x_cm: 250, y_cm: 300 }, segments);
    expect(match?.segment.id).toBe("south");
    expect(match?.projected).toEqual({ x_cm: 250, y_cm: 0 });
    expect(match?.distanceCm).toBe(300);
  });

  test("clamps the projection to the segment ends", () => {
    const before = nearestRoadMatch({ x_cm: -500, y_cm: 100 }, segments);
    expect(before?.segment.id).toBe("south");
    expect(before?.projected).toEqual({ x_cm: 0, y_cm: 0 });
    expect(before?.distanceCm).toBeCloseTo(Math.hypot(500, 100), 6);

    const after = nearestRoadMatch({ x_cm: 1500, y_cm: 100 }, segments);
    expect(after?.projected).toEqual({ x_cm: 1000, y_cm: 0 });
  });

  test("handles a zero-length segment without dividing by zero", () => {
    const match = nearestRoadMatch({ x_cm: 30, y_cm: 40 }, [
      { id: "point", ax: 0, ay: 0, bx: 0, by: 0, road_class: 0 },
    ]);
    expect(match?.projected).toEqual({ x_cm: 0, y_cm: 0 });
    expect(match?.distanceCm).toBe(50);
  });

  test("returns null without a point or segments", () => {
    expect(nearestRoadMatch(null, segments)).toBeNull();
    expect(nearestRoadMatch({ x_cm: 0, y_cm: 0 }, [])).toBeNull();
    expect(nearestRoadMatch({ x_cm: 0, y_cm: 0 }, null)).toBeNull();
  });
});

describe("Sumbawa coordinate conversion", () => {
  const roadMap = {
    available: true,
    origin_lat: DEFAULT_SUMBAWA_ORIGIN.lat,
    origin_lon: DEFAULT_SUMBAWA_ORIGIN.lon,
    origin_lat_deg7: DEFAULT_SUMBAWA_ORIGIN.lat_deg7,
    origin_lon_deg7: DEFAULT_SUMBAWA_ORIGIN.lon_deg7,
    cos_lat_q14: DEFAULT_SUMBAWA_ORIGIN.cos_lat_q14,
    segments,
  };

  test("maps the local origin to the Sumbawa map origin", () => {
    expect(localToLatLon({ x_cm: 0, y_cm: 0 }, roadMap)).toEqual([
      DEFAULT_SUMBAWA_ORIGIN.lat,
      DEFAULT_SUMBAWA_ORIGIN.lon,
    ]);
  });

  test("round-trips a local point through geo coordinates", () => {
    const local = { x_cm: 12_500, y_cm: -8_400 };
    const [lat, lon] = localToLatLon(local, roadMap);
    const point = geoToLocalPoint(lat, lon, roadMap);
    expect(point?.x_cm).toBeCloseTo(local.x_cm, -1);
    expect(point?.y_cm).toBeCloseTo(local.y_cm, -1);
  });

  test("rejects points far outside the bench map", () => {
    expect(geoToLocalPoint(10, 10, roadMap)).toBeNull();
  });
});

describe("parseRoadMapPayload", () => {
  const map = { available: true, segments, origin_lat: -8.49 };
  test("accepts the bridge wrapper and the bundled reference shape", () => {
    expect(parseRoadMapPayload({ reference: map })).toBe(map);
    expect(parseRoadMapPayload(map)).toBe(map);
  });

  test("rejects unavailable or malformed payloads", () => {
    expect(parseRoadMapPayload(null)).toBeNull();
    expect(parseRoadMapPayload({ reference: { available: false, segments: [] } })).toBeNull();
    expect(parseRoadMapPayload({ reference: { available: true, segments: "nope" } })).toBeNull();
  });
});

describe("roadBufferState", () => {
  test("uses the 5 m caution and 2 m danger buffers", () => {
    expect(roadBufferState(null)).toBe("outside");
    expect(roadBufferState(undefined)).toBe("outside");
    expect(roadBufferState(Number.NaN)).toBe("outside");
    expect(roadBufferState(0)).toBe("danger");
    expect(roadBufferState(200)).toBe("danger");
    expect(roadBufferState(201)).toBe("caution");
    expect(roadBufferState(500)).toBe("caution");
    expect(roadBufferState(501)).toBe("outside");
  });
});

describe("roadClassLabel", () => {
  test("labels OSM road classes used by the bench map", () => {
    expect(roadClassLabel(3)).toBe("primary");
    expect(roadClassLabel(2)).toBe("secondary");
    expect(roadClassLabel(1)).toBe("local road");
    expect(roadClassLabel(0)).toBe("service road");
  });
});
