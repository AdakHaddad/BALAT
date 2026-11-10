export type FirmwareRoadSegment = {
  id: string;
  ax: number;
  ay: number;
  bx: number;
  by: number;
  road_class: number;
};

export type FirmwareRoadMap = {
  available: boolean;
  origin_lat: number | null;
  origin_lon: number | null;
  origin_lat_deg7: number;
  origin_lon_deg7: number;
  cos_lat_q14: number;
  segment_count?: number;
  source?: string;
  segments: FirmwareRoadSegment[];
};

export type MockMapPoint = {
  lat_deg7: number;
  lon_deg7: number;
  x_cm: number;
  y_cm: number;
};

export type LocalPoint = { x_cm: number; y_cm: number };

export type RoadBufferState = "outside" | "caution" | "danger";

export const ROAD_BUFFER_CAUTION_CM = 500;
export const ROAD_BUFFER_DANGER_CM = 200;

export function roadBufferState(distanceCm: number | null | undefined): RoadBufferState {
  if (distanceCm === null || distanceCm === undefined || !Number.isFinite(distanceCm)) {
    return "outside";
  }
  if (distanceCm <= ROAD_BUFFER_DANGER_CM) return "danger";
  if (distanceCm <= ROAD_BUFFER_CAUTION_CM) return "caution";
  return "outside";
}

export type RoadMatch = {
  segment: FirmwareRoadSegment;
  index: number;
  distanceCm: number;
  projected: LocalPoint;
  t: number;
};

export const DEFAULT_SUMBAWA_ORIGIN = {
  lat: -8.49,
  lon: 117.42,
  lat_deg7: -84_900_000,
  lon_deg7: 1_174_200_000,
  cos_lat_q14: 16_204,
} as const;

export function parseRoadMapPayload(payload: unknown): FirmwareRoadMap | null {
  if (typeof payload !== "object" || payload === null) return null;
  const record = payload as Record<string, unknown>;
  const candidate = "reference" in record ? record.reference : payload;
  if (typeof candidate !== "object" || candidate === null) return null;
  const map = candidate as Record<string, unknown>;
  if (map.available !== true || !Array.isArray(map.segments)) return null;
  return candidate as FirmwareRoadMap;
}

export function roadClassLabel(roadClass: number): string {
  if (roadClass >= 3) return "primary";
  if (roadClass === 2) return "secondary";
  if (roadClass === 1) return "local road";
  return "service road";
}

export function nearestRoadMatch(
  point: LocalPoint | null | undefined,
  segments: FirmwareRoadSegment[] | null | undefined,
): RoadMatch | null {
  if (!point || !segments || segments.length === 0) return null;
  let best: RoadMatch | null = null;

  segments.forEach((segment, index) => {
    const dx = segment.bx - segment.ax;
    const dy = segment.by - segment.ay;
    const lengthSquared = dx * dx + dy * dy;
    const t = lengthSquared === 0
      ? 0
      : Math.max(0, Math.min(1, ((point.x_cm - segment.ax) * dx + (point.y_cm - segment.ay) * dy) / lengthSquared));
    const projected = { x_cm: segment.ax + t * dx, y_cm: segment.ay + t * dy };
    const distanceCm = Math.hypot(point.x_cm - projected.x_cm, point.y_cm - projected.y_cm);

    if (!best || distanceCm < best.distanceCm) {
      best = { segment, index, distanceCm, projected, t };
    }
  });

  return best;
}

export function geoToLocalPoint(lat: number, lon: number, roadMap: FirmwareRoadMap | null): MockMapPoint | null {
  const originLat = roadMap?.origin_lat_deg7 ?? DEFAULT_SUMBAWA_ORIGIN.lat_deg7;
  const originLon = roadMap?.origin_lon_deg7 ?? DEFAULT_SUMBAWA_ORIGIN.lon_deg7;
  const cosLat = roadMap?.cos_lat_q14 ?? DEFAULT_SUMBAWA_ORIGIN.cos_lat_q14;
  const latDeg7 = Math.round(lat * 10_000_000);
  const lonDeg7 = Math.round(lon * 10_000_000);
  const deltaLat = latDeg7 - originLat;
  const deltaLon = lonDeg7 - originLon;
  const yCm = Math.floor(deltaLat * 72_872 / 65_536);
  const xMidCm = Math.floor(deltaLon * 72_872 / 65_536);
  const xCm = Math.floor(xMidCm * cosLat / 16_384);

  if (Math.abs(xCm) > 1_000_000 || Math.abs(yCm) > 1_000_000) return null;
  return { lat_deg7: latDeg7, lon_deg7: lonDeg7, x_cm: xCm, y_cm: yCm };
}

export function localToLatLon(point: LocalPoint, roadMap: FirmwareRoadMap | null): [number, number] {
  const originLat = roadMap?.origin_lat_deg7 ?? DEFAULT_SUMBAWA_ORIGIN.lat_deg7;
  const originLon = roadMap?.origin_lon_deg7 ?? DEFAULT_SUMBAWA_ORIGIN.lon_deg7;
  const cosLat = roadMap?.cos_lat_q14 ?? DEFAULT_SUMBAWA_ORIGIN.cos_lat_q14;
  const latDeg7 = originLat + Math.round(point.y_cm * 65_536 / 72_872);
  const lonDeg7 = originLon + Math.round(point.x_cm * 65_536 * 16_384 / (72_872 * cosLat));
  return [latDeg7 / 10_000_000, lonDeg7 / 10_000_000];
}
