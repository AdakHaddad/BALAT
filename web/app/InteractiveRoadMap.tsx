"use client";

import L from "leaflet";
import { MapContainer, Marker, Polyline, TileLayer, Tooltip, useMapEvents } from "react-leaflet";

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

type LocalPoint = { x_cm: number; y_cm: number };

const DEFAULT_ORIGIN = {
  lat_deg7: -338_250_000,
  lon_deg7: 186_500_000,
  cos_lat_q14: 13_611,
};

function mockPointIcon(risk: "safe" | "caution" | "danger") {
  return L.divIcon({
    className: `mock-point-icon ${risk}`,
    html: "<span></span>",
    iconSize: [24, 24],
    iconAnchor: [12, 12],
  });
}

function geoToLocalPoint(lat: number, lon: number, roadMap: FirmwareRoadMap | null): MockMapPoint | null {
  const originLat = roadMap?.origin_lat_deg7 ?? DEFAULT_ORIGIN.lat_deg7;
  const originLon = roadMap?.origin_lon_deg7 ?? DEFAULT_ORIGIN.lon_deg7;
  const cosLat = roadMap?.cos_lat_q14 ?? DEFAULT_ORIGIN.cos_lat_q14;
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

function localToLatLon(point: LocalPoint, roadMap: FirmwareRoadMap | null): [number, number] {
  const originLat = roadMap?.origin_lat_deg7 ?? DEFAULT_ORIGIN.lat_deg7;
  const originLon = roadMap?.origin_lon_deg7 ?? DEFAULT_ORIGIN.lon_deg7;
  const cosLat = roadMap?.cos_lat_q14 ?? DEFAULT_ORIGIN.cos_lat_q14;
  const latDeg7 = originLat + Math.round(point.y_cm * 65_536 / 72_872);
  const lonDeg7 = originLon + Math.round(point.x_cm * 65_536 * 16_384 / (72_872 * cosLat));
  return [latDeg7 / 10_000_000, lonDeg7 / 10_000_000];
}

function ClickToMockPoint({ onSelect, roadMap }: { onSelect: (point: MockMapPoint) => void; roadMap: FirmwareRoadMap | null }) {
  useMapEvents({
    click(event) {
      const point = geoToLocalPoint(event.latlng.lat, event.latlng.lng, roadMap);
      if (point) onSelect(point);
    },
  });
  return null;
}

export default function InteractiveRoadMap({
  roadMap,
  point,
  livePoint,
  livePointValid,
  risk,
  onSelect,
}: {
  roadMap: FirmwareRoadMap | null;
  point: MockMapPoint | null;
  livePoint: LocalPoint | null;
  livePointValid: boolean;
  risk: "safe" | "caution" | "danger";
  onSelect: (point: MockMapPoint) => void;
}) {
  const center: [number, number] = [
    roadMap?.origin_lat ?? DEFAULT_ORIGIN.lat_deg7 / 10_000_000,
    roadMap?.origin_lon ?? DEFAULT_ORIGIN.lon_deg7 / 10_000_000,
  ];
  const visiblePoint = point ?? (livePoint
    ? { lat_deg7: 0, lon_deg7: 0, x_cm: livePoint.x_cm, y_cm: livePoint.y_cm }
    : null);
  const markerPosition = visiblePoint
    ? visiblePoint.lat_deg7 !== 0 || visiblePoint.lon_deg7 !== 0
      ? [visiblePoint.lat_deg7 / 10_000_000, visiblePoint.lon_deg7 / 10_000_000] as [number, number]
      : localToLatLon(visiblePoint, roadMap)
    : null;

  return (
    <MapContainer className="firmware-leaflet-map" center={center} zoom={15} scrollWheelZoom>
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap contributors</a>'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        maxZoom={19}
      />
      {(roadMap?.segments ?? []).map((segment) => (
        <Polyline
          key={segment.id}
          positions={[localToLatLon({ x_cm: segment.ax, y_cm: segment.ay }, roadMap), localToLatLon({ x_cm: segment.bx, y_cm: segment.by }, roadMap)]}
          pathOptions={{
            color: segment.road_class >= 3 ? "#d47942" : segment.road_class === 2 ? "#4a8bb5" : "#2d7a5f",
            weight: segment.road_class >= 3 ? 5 : 3,
            opacity: 0.9,
          }}
        >
          <Tooltip>{segment.id} · OSM road segment</Tooltip>
        </Polyline>
      ))}
      <ClickToMockPoint onSelect={onSelect} roadMap={roadMap} />
      {markerPosition && <Marker
        position={markerPosition}
        icon={mockPointIcon(risk)}
        draggable
        eventHandlers={{
          drag(event) {
            const latLng = (event.target as L.Marker).getLatLng();
            const nextPoint = geoToLocalPoint(latLng.lat, latLng.lng, roadMap);
            if (nextPoint) onSelect(nextPoint);
          },
        }}
      >
        <Tooltip permanent direction="top">
          {point ? "Mock point" : livePointValid ? "Live fix" : "Last fix · invalid"}
        </Tooltip>
      </Marker>}
    </MapContainer>
  );
}