"use client";

import L from "leaflet";
import { useEffect, useMemo, useRef } from "react";
import { Circle, CircleMarker, MapContainer, Marker, Polyline, TileLayer, Tooltip, useMap, useMapEvents } from "react-leaflet";
import {
  DEFAULT_SUMBAWA_ORIGIN,
  ROAD_BUFFER_CAUTION_CM,
  ROAD_BUFFER_DANGER_CM,
  geoToLocalPoint,
  localToLatLon,
  nearestRoadMatch,
  roadBufferState,
  roadClassLabel,
  type FirmwareRoadMap,
  type LocalPoint,
  type MockMapPoint,
} from "./roadGeometry";

type RiskTone = "safe" | "caution" | "danger";

const riskColors: Record<RiskTone, string> = {
  safe: "#2d7a5f",
  caution: "#d47942",
  danger: "#d84a40",
};

function mockPointIcon(risk: RiskTone) {
  return L.divIcon({
    className: `mock-point-icon ${risk}`,
    html: "<span></span>",
    iconSize: [24, 24],
    iconAnchor: [12, 12],
  });
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

function MapViewport({ roadMap, point }: { roadMap: FirmwareRoadMap | null; point: LocalPoint | null }) {
  const map = useMap();
  const fitted = useRef(false);
  const focused = useRef(false);

  useEffect(() => {
    if (fitted.current || !roadMap?.segments.length) return;
    const corners = roadMap.segments.flatMap((segment) => [
      localToLatLon({ x_cm: segment.ax, y_cm: segment.ay }, roadMap),
      localToLatLon({ x_cm: segment.bx, y_cm: segment.by }, roadMap),
    ]);
    map.fitBounds(L.latLngBounds(corners), { padding: [18, 18] });
    fitted.current = true;
  }, [map, roadMap]);

  useEffect(() => {
    if (!point) {
      focused.current = false;
      return;
    }
    const target = localToLatLon(point, roadMap);
    if (!focused.current) {
      map.setView(target, Math.max(map.getZoom(), 18));
      focused.current = true;
      return;
    }
    if (!map.getBounds().pad(-0.2).contains(target)) map.panTo(target);
  }, [map, point, roadMap]);

  return null;
}

export default function InteractiveRoadMap({
  roadMap,
  point,
  livePoint,
  livePointValid,
  risk,
  riskLabel,
  onSelect,
}: {
  roadMap: FirmwareRoadMap | null;
  point: MockMapPoint | null;
  livePoint: LocalPoint | null;
  livePointValid: boolean;
  risk: RiskTone;
  riskLabel?: string;
  onSelect: (point: MockMapPoint) => void;
}) {
  const activePoint = point ?? livePoint;
  const match = useMemo(() => nearestRoadMatch(activePoint, roadMap?.segments), [activePoint, roadMap]);
  const center: [number, number] = [
    roadMap?.origin_lat ?? DEFAULT_SUMBAWA_ORIGIN.lat,
    roadMap?.origin_lon ?? DEFAULT_SUMBAWA_ORIGIN.lon,
  ];
  const markerPosition = activePoint
    ? point && (point.lat_deg7 !== 0 || point.lon_deg7 !== 0)
      ? [point.lat_deg7 / 10_000_000, point.lon_deg7 / 10_000_000] as [number, number]
      : localToLatLon(activePoint, roadMap)
    : null;
  const roadColor = riskColors[risk];
  const nearestRoadPositions = match
    ? [
        localToLatLon({ x_cm: match.segment.ax, y_cm: match.segment.ay }, roadMap),
        localToLatLon({ x_cm: match.segment.bx, y_cm: match.segment.by }, roadMap),
      ] as [[number, number], [number, number]]
    : null;
  const projectionPosition = match ? localToLatLon(match.projected, roadMap) : null;
  const distanceLabel = match ? `${(match.distanceCm / 100).toFixed(1)} m` : null;
  const buffer = roadBufferState(match?.distanceCm);
  const bufferLabel = buffer === "danger"
    ? "inside 2 m danger buffer"
    : buffer === "caution"
      ? "inside 5 m caution buffer"
      : "outside 5 m caution buffer";

  return (
    <div className="firmware-map-shell">
      <MapContainer className="firmware-leaflet-map" center={center} zoom={14} scrollWheelZoom>
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
            <Tooltip>{segment.id} · {roadClassLabel(segment.road_class)} · OSM road segment</Tooltip>
          </Polyline>
        ))}
        {nearestRoadPositions && (
          <>
            <Polyline positions={nearestRoadPositions} pathOptions={{ color: roadColor, weight: 14, opacity: 0.16 }} />
            <Polyline positions={nearestRoadPositions} pathOptions={{ color: roadColor, weight: 7, opacity: 0.95 }} />
          </>
        )}
        {projectionPosition && (
          <>
            <Circle
              center={projectionPosition}
              radius={ROAD_BUFFER_CAUTION_CM / 100}
              pathOptions={{ color: riskColors.caution, weight: 1.5, dashArray: "4 4", fillColor: riskColors.caution, fillOpacity: 0.06 }}
            />
            <Circle
              center={projectionPosition}
              radius={ROAD_BUFFER_DANGER_CM / 100}
              pathOptions={{ color: riskColors.danger, weight: 1.5, dashArray: "4 4", fillColor: riskColors.danger, fillOpacity: 0.06 }}
            />
          </>
        )}
        <ClickToMockPoint onSelect={onSelect} roadMap={roadMap} />
        {markerPosition && projectionPosition && (
          <Polyline
            positions={[markerPosition, projectionPosition]}
            pathOptions={{ color: roadColor, weight: 2, dashArray: "6 6", opacity: 0.9 }}
          />
        )}
        {projectionPosition && (
          <CircleMarker
            center={projectionPosition}
            radius={6}
            pathOptions={{ color: roadColor, weight: 2, fillColor: roadColor, fillOpacity: 0.9 }}
          >
            <Tooltip direction="right">{distanceLabel} to nearest road</Tooltip>
          </CircleMarker>
        )}
        {markerPosition && (
          <Marker
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
          </Marker>
        )}
        <MapViewport roadMap={roadMap} point={activePoint} />
      </MapContainer>
      <div className={`road-reaction-hud ${risk}`} role="status" aria-live="polite">
        <span className="eyebrow">ROAD REACTION</span>
        <strong>{distanceLabel ?? "No fix"}</strong>
        <small>
          {match
            ? `${riskLabel ?? risk.toUpperCase()} · seg ${match.segment.id} · ${roadClassLabel(match.segment.road_class)}`
            : "Click or drag to place the collar"}
        </small>
        {match && <small className={`buffer-note ${buffer}`}>{bufferLabel}</small>}
      </div>
    </div>
  );
}
