"use client";

import { useEffect, useMemo, useRef, useState, useSyncExternalStore } from "react";

type Risk = "INVALID" | "SAFE" | "CAUTION" | "DANGER" | "COOLDOWN";
type ConnectionState = "connecting" | "live" | "fallback";

type TelemetryState = {
  x_cm: number;
  y_cm: number;
  fix_valid: boolean;
  map_valid: boolean | null;
  cue_active: boolean;
  dist_m: number;
  risk_name: string;
  battery_mv: number;
  quality: number;
  source: string;
  seq: number;
  link_status: string;
  mock_gps?: MockGpsState;
};

type MockGpsState = {
  available: boolean;
  mode: "mock" | "gps";
  running: boolean;
  index: number;
  total: number;
  interval: number;
};

type Animal = {
  id: string;
  name: string;
  region: string;
  risk: Risk;
  distance: string;
  lastSeen: string;
  battery: number;
  signal: string;
};

type DemoMode = "approach" | "away" | "stale";
const BALAT_BLE_SERVICE = "7f510001-1b15-4f0d-8e3a-7c522f8b96a1";
const BALAT_BLE_CONTROL = "7f510002-1b15-4f0d-8e3a-7c522f8b96a1";
const BALAT_BLE_STATUS = "7f510003-1b15-4f0d-8e3a-7c522f8b96a1";
const BLE_REPLAY_FIX_COUNT = 201;

const demoModes: Record<DemoMode, { label: string; distance: number; velocity: number; risk: Risk; note: string }> = {
  approach: { label: "Approaching road", distance: 42, velocity: 1.8, risk: "DANGER", note: "Valid fixes move toward the nearest mapped segment." },
  away: { label: "Moving away", distance: 128, velocity: -1.2, risk: "SAFE", note: "The same road distance stays safe when velocity points away." },
  stale: { label: "Stale GNSS fix", distance: 42, velocity: 1.8, risk: "SAFE", note: "Stale or invalid data is rejected before risk assessment." },
};

function PipelineExplainer() {
  const [mode, setMode] = useState<DemoMode>("approach");
  const [playing, setPlaying] = useState(true);
  const demo = demoModes[mode];
  const blocked = mode === "stale";

  useEffect(() => {
    if (!playing) return;
    const timer = window.setInterval(() => {
      setMode((current) => current === "approach" ? "away" : current === "away" ? "stale" : "approach");
    }, 4200);
    return () => window.clearInterval(timer);
  }, [playing]);

  const cueLabel = blocked ? "HELD · INVALID" : demo.risk === "DANGER" ? "CUE ENABLED" : "INACTIVE";
  const flowClass = blocked ? "explainer-flow blocked" : "explainer-flow";

  return (
    <section className="pipeline-explainer" aria-labelledby="pipeline-title">
      <div className="explainer-heading">
        <div>
          <span className="eyebrow">HOW BALAT WORKS</span>
          <h2 id="pipeline-title">A local decision, built like an instrument</h2>
          <p>Move the replay through the machine. Each station is one bounded RTL step: no cloud decision, no direct actuator drive.</p>
        </div>
        <div className="explainer-controls">
          {(Object.keys(demoModes) as DemoMode[]).map((key) => (
            <button key={key} className={mode === key ? "explainer-mode active" : "explainer-mode"} onClick={() => { setMode(key); setPlaying(false); }}>
              {demoModes[key].label}
            </button>
          ))}
          <button className="explainer-play" onClick={() => setPlaying((value) => !value)}>{playing ? "Pause replay" : "Play replay"}</button>
        </div>
      </div>

      <div className="explainer-card">
        <div className="machine-stage">
          <div className="machine-caption">EDGE RISK ENGINE · REPLAY {playing ? "RUNNING" : "PAUSED"}</div>
          <svg className="machine-svg" viewBox="0 0 1160 430" role="img" aria-label="Interactive diagram of the BALAT FPGA pipeline">
            <defs>
              <linearGradient id="machineMetal" x1="0" x2="0" y1="0" y2="1"><stop offset="0" stopColor="#27463a" /><stop offset="1" stopColor="#142a23" /></linearGradient>
              <linearGradient id="machineTop" x1="0" x2="1" y1="0" y2="1"><stop offset="0" stopColor="#315747" /><stop offset="1" stopColor="#1c362d" /></linearGradient>
              <filter id="machineGlow"><feGaussianBlur stdDeviation="7" /></filter>
            </defs>
            <ellipse className="machine-shadow" cx="580" cy="369" rx="480" ry="25" />
            <rect className="machine-base" x="55" y="318" width="1050" height="48" rx="10" />
            {[90, 1060].map((x) => <g key={x}><circle className="machine-foot" cx={x} cy="373" r="13" /><circle className="machine-foot-inner" cx={x} cy="373" r="6" /></g>)}
            <path className="machine-rail" d="M92 310 H1067" /><path className="machine-rail-highlight" d="M107 305 H1052" />
            <g className="machine-station" transform="translate(82 106)">
              <rect className="station-shell" x="0" y="0" width="165" height="195" rx="9" />
              <rect className="station-top" x="12" y="12" width="141" height="34" rx="4" />
              <circle className="station-led active" cx="28" cy="29" r="5" /><circle className="station-led" cx="45" cy="29" r="5" /><circle className="station-led" cx="62" cy="29" r="5" />
              <rect className="station-window" x="15" y="60" width="135" height="53" rx="4" /><path className="signal-wave" d="M30 92 l13 -15 12 23 14 -35 14 25 14 -14 15 16 15 -8" />
              <rect className="station-slot" x="20" y="132" width="125" height="9" rx="4" /><rect className="station-slot" x="20" y="151" width="88" height="9" rx="4" />
              <circle className="bolt" cx="13" cy="181" r="3" /><circle className="bolt" cx="152" cy="181" r="3" />
              <text className="machine-label" x="82" y="184">GNSS / VALIDATE</text>
            </g>
            <g className="machine-station" transform="translate(274 76)">
              <rect className="station-shell" x="0" y="0" width="194" height="225" rx="9" />
              <rect className="station-top" x="13" y="13" width="168" height="31" rx="4" /><text className="machine-label" x="97" y="33">LOCAL MAP MEMORY</text>
              <rect className="drawer" x="17" y="59" width="160" height="42" rx="3" /><rect className="drawer" x="17" y="108" width="160" height="42" rx="3" /><rect className="drawer active-drawer" x="17" y="157" width="160" height="42" rx="3" />
              <path className="map-lines" d="M31 84 C63 67 72 92 101 76 S144 67 162 82 M31 134 C63 119 74 144 98 125 S141 121 163 137 M31 183 C68 164 82 192 113 172 S141 164 164 181" />
              {[30, 177].map((x) => <g key={x}><circle className="bolt" cx={x} cy="214" r="3" /><circle className="bolt" cx={x} cy="29" r="3" /></g>)}
              <text className="drawer-text" x="30" y="75">RS-04 / ROAD SEGMENT</text><text className="drawer-text" x="30" y="124">BUFFER + CLASS</text><text className="drawer-text" x="30" y="173">CRC · v0.4.2</text>
            </g>
            <g className="machine-station" transform="translate(495 106)">
              <rect className="station-shell" x="0" y="0" width="196" height="195" rx="9" />
              <rect className="station-top" x="13" y="12" width="170" height="33" rx="4" /><text className="machine-label" x="98" y="33">GEOMETRY CARRIAGE</text>
              <rect className="carriage-track" x="22" y="73" width="151" height="11" rx="5" /><rect className="carriage" x="67" y="58" width="52" height="42" rx="6" />
              <circle className="carriage-wheel" cx="77" cy="105" r="8" /><circle className="carriage-wheel" cx="109" cy="105" r="8" />
              <path className="projection-line" d="M35 145 H163 M98 119 V176" /><circle className="animal-dot" cx="98" cy="145" r="10" /><circle className="road-dot" cx="148" cy="145" r="6" />
              <path className="distance-line" d="M108 145 H142" /><text className="readout" x="98" y="190" textAnchor="middle">{demo.distance} m · nearest road</text>
            </g>
            <g className="machine-station" transform="translate(718 76)">
              <rect className="station-shell" x="0" y="0" width="194" height="225" rx="9" />
              <rect className="station-top" x="13" y="13" width="168" height="31" rx="4" /><text className="machine-label" x="97" y="33">RISK RELAY</text>
              <circle className={`risk-lamp ${demo.risk.toLowerCase()}`} cx="48" cy="91" r="18" /><circle className="risk-lamp-ring" cx="48" cy="91" r="26" />
              <rect className="relay-window" x="87" y="61" width="82" height="60" rx="4" /><text className="risk-display" x="128" y="88" textAnchor="middle">{demo.risk}</text><text className="relay-small" x="128" y="106" textAnchor="middle">{demo.velocity > 0 ? "TOWARD" : "AWAY"}</text>
              <path className="relay-wire" d="M30 158 H164 M30 178 H125" /><circle className="bolt" cx="20" cy="211" r="3" /><circle className="bolt" cx="174" cy="211" r="3" /><text className="drawer-text" x="30" y="151">HYSTERESIS / CONFIRM</text>
            </g>
            <g className="machine-station" transform="translate(939 106)">
              <rect className="station-shell" x="0" y="0" width="165" height="195" rx="9" />
              <rect className="station-top" x="12" y="12" width="141" height="34" rx="4" /><text className="machine-label" x="82" y="33">CUE DRIVER</text>
              <circle className={`cue-lamp ${blocked ? "held" : demo.risk === "DANGER" ? "on" : ""}`} cx="82" cy="85" r="24" /><circle className="cue-ring" cx="82" cy="85" r="33" />
              <rect className="output-port" x="26" y="135" width="112" height="25" rx="4" /><circle className="port-dot" cx="42" cy="147" r="5" /><circle className="port-dot" cx="59" cy="147" r="5" /><circle className="port-dot" cx="76" cy="147" r="5" /><text className="cue-text" x="82" y="184" textAnchor="middle">{cueLabel}</text>
            </g>
            <g className={flowClass}>
              <path d="M247 205 H274 M468 205 H495 M691 205 H718 M912 205 H939" />
              <circle cx="260" cy="205" r="5" /><circle cx="480" cy="205" r="5" /><circle cx="704" cy="205" r="5" /><circle cx="926" cy="205" r="5" />
            </g>
            <text className="stage-note" x="165" y="398">1 · accept only trustworthy fix</text><text className="stage-note" x="371" y="398">2 · scan local segment memory</text><text className="stage-note" x="596" y="398">3 · compare point to segment</text><text className="stage-note" x="816" y="398">4 · classify with hysteresis</text><text className="stage-note" x="1021" y="398">5 · bounded cue</text>
          </svg>
        </div>
        <div className="explainer-readout">
          <div><span className="eyebrow">CURRENT REPLAY</span><strong>{demo.label}</strong><p>{demo.note}</p></div>
          <div className="readout-metric"><span className="eyebrow">FIX GATE</span><b className={blocked ? "red-text" : "green-text"}>{blocked ? "REJECTED" : "VALID"}</b></div>
          <div className="readout-metric"><span className="eyebrow">VELOCITY TO ROAD</span><b>{demo.velocity > 0 ? "+" : ""}{demo.velocity.toFixed(1)} m/s</b></div>
          <div className="readout-metric"><span className="eyebrow">OUTPUT</span><b className={demo.risk === "DANGER" && !blocked ? "orange-text" : ""}>{cueLabel}</b></div>
        </div>
      </div>
      <p className="explainer-footnote">Prototype boundary: BALAT issues a modular output command through protected external driver hardware. It does not directly drive a motor or speaker, and cue effectiveness with cattle remains unvalidated.</p>
    </section>
  );
}

const initialAnimals: Animal[] = [
  { id: "BLT-042", name: "Collar 042", region: "Kupang / NTT", risk: "DANGER", distance: "24 m", lastSeen: "8 sec ago", battery: 82, signal: "EDGE" },
  { id: "BLT-017", name: "Collar 017", region: "Sumba Timur", risk: "CAUTION", distance: "86 m", lastSeen: "12 sec ago", battery: 74, signal: "EDGE" },
  { id: "BLT-008", name: "Collar 008", region: "Bojonegoro", risk: "SAFE", distance: "312 m", lastSeen: "18 sec ago", battery: 91, signal: "MULE" },
  { id: "BLT-031", name: "Collar 031", region: "Tuban", risk: "SAFE", distance: "428 m", lastSeen: "24 sec ago", battery: 66, signal: "EDGE" },
  { id: "BLT-053", name: "Collar 053", region: "Kupang / NTT", risk: "SAFE", distance: "515 m", lastSeen: "31 sec ago", battery: 58, signal: "MULE" },
];

const tone: Record<Risk, string> = {
  INVALID: "invalid",
  SAFE: "safe",
  CAUTION: "caution",
  DANGER: "danger",
  COOLDOWN: "cooldown",
};

function RiskBadge({ risk }: { risk: Risk }) {
  return <span className={`risk-badge ${tone[risk]}`}><span className="status-dot" />{risk}</span>;
}

function toRisk(value: string): Risk {
  return value === "INVALID" || value === "SAFE" || value === "CAUTION" || value === "DANGER" || value === "COOLDOWN"
    ? value
    : "INVALID";
}

function decodeBleStatus(value: DataView): TelemetryState | null {
  if (value.byteLength !== 19 || value.getUint8(0) !== 1) return null;
  const risk = (["INVALID", "SAFE", "CAUTION", "DANGER", "COOLDOWN"] as const)[value.getUint8(17)] ?? "INVALID";
  const flags = value.getUint8(18);
  return {
    x_cm: value.getInt32(1, true), y_cm: value.getInt32(5, true),
    dist_m: value.getUint32(9, true) / 100, seq: value.getUint32(13, true),
    risk_name: risk, fix_valid: (flags & 1) !== 0, map_valid: (flags & 2) !== 0,
    cue_active: (flags & 4) !== 0, battery_mv: 0, quality: 100,
    source: "ESP32_BLE", link_status: "BLE",
  };
}

function formatDistance(distance: number): string {
  return `${Number.isFinite(distance) ? distance.toFixed(1) : "—"} m`;
}

function Metric({ label, value, detail, accent = "" }: { label: string; value: string; detail: string; accent?: string }) {
  return (
    <div className={`metric-card ${accent}`}>
      <span className="eyebrow">{label}</span>
      <strong>{value}</strong>
      <span className="metric-detail">{detail}</span>
    </div>
  );
}

function MapPanel({ animals, activeId, onSelect, esp32Source, livePoint, onMoveMock }: { animals: Animal[]; activeId: string; onSelect: (id: string) => void; esp32Source: boolean; livePoint: { x_cm: number; y_cm: number } | null; onMoveMock?: (point: { x_cm: number; y_cm: number }) => void }) {
  const displayedAnimals = esp32Source ? animals.slice(0, 1) : animals;
  const livePosition = livePoint ? {
    left: `${Math.max(2, Math.min(98, 50 + livePoint.x_cm / 120_000 * 100))}%`,
    top: `${Math.max(2, Math.min(98, 50 - livePoint.y_cm / 120_000 * 100))}%`,
  } : null;
  return (
    <div className="map-panel">
      <div className="map-header">
        <div>
          <span className="eyebrow">MAP</span>
          <h2>{esp32Source ? "Hardware bench · local origin" : "Corridor 04 · Kupang"}</h2>
        </div>
        <span className="map-chip">OPENSTREETMAP</span>
      </div>
      <div className={esp32Source ? "map local-risk-map" : "map"} onPointerDown={(event) => {
        if (!esp32Source || !onMoveMock) return;
        const rect = event.currentTarget.getBoundingClientRect();
        const x_cm = Math.round(((event.clientX - rect.left) / rect.width - 0.5) * 120_000);
        const y_cm = Math.round((0.5 - (event.clientY - rect.top) / rect.height) * 120_000);
        onMoveMock({ x_cm, y_cm });
      }}>
        {esp32Source && <svg className="local-map-art" viewBox="0 0 100 100" preserveAspectRatio="none" aria-label="Local demo road map">
          <path className="local-road-buffer" d="M50 0V100"/><path className="local-road" d="M50 0V100"/>
          <path className="local-road-secondary" d="M0 50H100"/><path className="local-road-secondary" d="M22 0L78 100"/>
          <text x="52" y="8">ROAD SEGMENT</text><text x="3" y="48">CROSSING</text>
        </svg>}
        {!esp32Source && <iframe
          title="OpenStreetMap view of Corridor 04 near Kupang"
          src="https://www.openstreetmap.org/export/embed.html?bbox=123.52%2C-10.22%2C123.66%2C-10.12&layer=mapnik&marker=-10.17,123.59"
          loading="lazy"
        />}
        {/* Overlay cattle positions on map */}
        <div className="map-overlay">
          {displayedAnimals.map((animal, idx) => {
            if (esp32Source && !livePosition) return null;
            const positions = [
              { left: '28%', top: '35%' }, // BLT-042 - danger zone
              { left: '45%', top: '55%' }, // BLT-017 - caution
              { left: '65%', top: '25%' }, // BLT-008 - safe
              { left: '72%', top: '68%' }, // BLT-031 - safe
              { left: '38%', top: '78%' }, // BLT-053 - safe
            ];
            const pos = livePosition && idx === 0 ? livePosition : positions[idx] || positions[0];
            return (
              <button
                key={animal.id}
                className={`map-marker ${tone[animal.risk]} ${activeId === animal.id ? 'active' : ''}`}
                style={{ left: pos.left, top: pos.top }}
                onClick={() => onSelect(animal.id)}
                onPointerMove={(event) => { if ((event.buttons & 1) !== 0 && esp32Source && onMoveMock) { event.stopPropagation(); const rect = event.currentTarget.parentElement?.parentElement?.getBoundingClientRect(); if (rect) onMoveMock({ x_cm: Math.round(((event.clientX - rect.left) / rect.width - 0.5) * 120_000), y_cm: Math.round((0.5 - (event.clientY - rect.top) / rect.height) * 120_000) }); } }}
                aria-label={`${animal.name} - ${animal.risk}`}
              >
                <span className="marker-pulse" />
                <span className="marker-dot" />
                {activeId === animal.id && <span className="marker-label">{animal.id}</span>}
              </button>
            );
          })}
        </div>
      </div>
      <div className="map-footer">
        <span>{esp32Source ? `Hardware bench local coordinates · ${livePoint ? "approximate position · firmware road lines not overlaid" : "position hidden while fix is invalid"}` : "Road geometry: local manifest v0.4.2"}</span>
        <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noreferrer">© OpenStreetMap</a>
      </div>
    </div>
  );
}

export default function Home() {
  const [activeId, setActiveId] = useState("BLT-042");
  const [animals, setAnimals] = useState(initialAnimals);
  const [now, setNow] = useState("23:49:53");
  const [view, setView] = useState("Overview");
  const pitchMode = useSyncExternalStore(
    (onStoreChange) => {
      window.addEventListener("popstate", onStoreChange);
      return () => window.removeEventListener("popstate", onStoreChange);
    },
    () => new URLSearchParams(window.location.search).get("pitch") === "1",
    () => false,
  );
  const [cue, setCue] = useState(false);
  const [connection, setConnection] = useState<ConnectionState>("connecting");
  const [telemetry, setTelemetry] = useState<TelemetryState | null>(null);
  const [mockGps, setMockGps] = useState<MockGpsState | null>(null);
  const [mockInterval, setMockInterval] = useState(0.1);
  const [mockControlBusy, setMockControlBusy] = useState(false);
  const [mockControlMessage, setMockControlMessage] = useState("");
  const [noticeVisible, setNoticeVisible] = useState(true);
  const [bleCharacteristic, setBleCharacteristic] = useState<BluetoothRemoteGATTCharacteristic | null>(null);
  const [bleStatus, setBleStatus] = useState("BLE disconnected");
  const [bleConnecting, setBleConnecting] = useState(false);
  const [bleControlBusy, setBleControlBusy] = useState(false);
  const [bleReplayRunning, setBleReplayRunning] = useState(false);
  const lastMockSend = useRef(0);

  const apiBase = process.env.NEXT_PUBLIC_BALAT_API_URL?.replace(/\/$/, "") || "http://localhost:8888";

  useEffect(() => {
    if (bleCharacteristic) {
      const timer = window.setInterval(() => setNow(new Date().toLocaleTimeString("en-GB", { hour12: false })), 1000);
      return () => window.clearInterval(timer);
    }
    let cancelled = false;

    const pollTelemetry = async () => {
      try {
        const response = await fetch(`${apiBase}/api/state`, { cache: "no-store" });
        if (!response.ok) throw new Error(`Telemetry request failed: ${response.status}`);
        const nextTelemetry = (await response.json()) as TelemetryState;
        if (cancelled) return;
        if (nextTelemetry.source === "WAITING") {
          setConnection("connecting");
          return;
        }
        setTelemetry(nextTelemetry);
        setMockGps(nextTelemetry.mock_gps ?? null);
        setConnection("live");
        const benchTelemetry = nextTelemetry.source === "ESP32_UART" || nextTelemetry.source === "BASYS3_NMEA_UART";
        setActiveId(benchTelemetry ? nextTelemetry.source === "ESP32_UART" ? "ESP32-C3" : "BASYS3" : initialAnimals[0].id);
        setAnimals((items) => items.map((animal, index) => index === 0 ? {
          ...animal,
          id: nextTelemetry.source === "ESP32_UART" ? "ESP32-C3" : nextTelemetry.source === "BASYS3_NMEA_UART" ? "BASYS3" : initialAnimals[0].id,
          name: nextTelemetry.source === "ESP32_UART" ? "ESP32-C3 bench" : nextTelemetry.source === "BASYS3_NMEA_UART" ? "Basys 3 FPGA" : initialAnimals[0].name,
          risk: toRisk(nextTelemetry.risk_name),
          distance: formatDistance(nextTelemetry.dist_m),
          region: nextTelemetry.source === "ESP32_UART" ? "ESP32 bench · local coordinates" : nextTelemetry.source === "BASYS3_NMEA_UART" ? "Basys 3 FPGA · local coordinates" : initialAnimals[0].region,
          lastSeen: "just now",
          battery: nextTelemetry.source === "ESP32_UART" && nextTelemetry.battery_mv <= 0
            ? 0
            : nextTelemetry.battery_mv > 0
            ? Math.min(100, Math.max(0, Math.round((nextTelemetry.battery_mv / 4200) * 100)))
            : animal.battery,
            signal: nextTelemetry.source === "BASYS3_UART" || nextTelemetry.source === "BASYS3_NMEA_UART" || nextTelemetry.source === "ESP32_UART" ? "EDGE" : initialAnimals[0].signal,
        } : animal));
      } catch {
        if (!cancelled) {
          setTelemetry(null);
          setAnimals(initialAnimals);
          setActiveId(initialAnimals[0].id);
          setConnection("fallback");
        }
      }
    };

    void pollTelemetry();
    const telemetryTimer = window.setInterval(() => void pollTelemetry(), 1000);
    const timer = setInterval(() => {
      setNow(new Date().toLocaleTimeString("en-GB", { hour12: false }));
      setAnimals((items) => items.map((animal, index) => index === 0 && connection === "live" ? animal : {
        ...animal,
        lastSeen: `${8 + ((Date.now() / 1000 + index * 7) % 35 | 0)} sec ago`,
      }));
    }, 5000);
    return () => {
      cancelled = true;
      window.clearInterval(telemetryTimer);
      clearInterval(timer);
    };
  }, [apiBase, connection, bleCharacteristic]);

  const esp32Source = Boolean(bleCharacteristic) || (connection === "live" && (telemetry?.source === "ESP32_UART" || telemetry?.source === "ESP32_BLE"));
  const fpgaNmeaSource = connection === "live" && telemetry?.source === "BASYS3_NMEA_UART";
  const benchSource = esp32Source || fpgaNmeaSource;
  const benchLabel = fpgaNmeaSource ? "Basys 3 FPGA" : "ESP32 bench";
  const visibleAnimals = benchSource ? animals.slice(0, 1) : animals;
  const selected = useMemo(() => visibleAnimals.find((animal) => animal.id === activeId) ?? visibleAnimals[0], [activeId, visibleAnimals]);
  const dangerCount = visibleAnimals.filter((animal) => animal.risk === "DANGER").length;
  const cautionCount = visibleAnimals.filter((animal) => animal.risk === "CAUTION").length;
  const livePoint = benchSource && telemetry?.fix_valid
    ? { x_cm: telemetry.x_cm, y_cm: telemetry.y_cm }
    : null;
  const sourceLabel = connection === "live"
    ? telemetry?.source === "ESP32_BLE" ? "LIVE ESP32 BLE" : telemetry?.source === "ESP32_UART" ? "LIVE ESP32 TELEMETRY" : telemetry?.source === "BASYS3_UART" || telemetry?.source === "BASYS3_NMEA_UART" ? "LIVE FPGA TELEMETRY" : "SYNTHETIC TRACE"
    : connection === "connecting" ? "CONNECTING TO BRIDGE" : "SYNTHETIC TRACE FALLBACK";
  const isExplainerView = view === "How BALAT works";
  const navItems = ["Overview", "Herd monitor", "Road memory", "Telemetry log", "How BALAT works"];
  const serialReplaySource = connection === "live" && (telemetry?.source === "ESP32_UART" || telemetry?.source === "BASYS3_NMEA_UART");
  const applyBleFrame = (frame: TelemetryState) => {
    setTelemetry(frame);
    setConnection("live");
    if (frame.seq >= BLE_REPLAY_FIX_COUNT) setBleReplayRunning(false);
    setAnimals((items) => items.map((animal, index) => index === 0 ? {
      ...animal,
      id: "ESP32-C3",
      name: "ESP32-C3 Super Mini",
      risk: toRisk(frame.risk_name),
      distance: formatDistance(frame.dist_m),
      region: "ESP32-C3 · local coordinates",
      lastSeen: "just now",
      signal: "EDGE",
    } : animal));
  };
  const connectBle = async () => {
    let device: BluetoothDevice | null = null;
    setBleConnecting(true);
    setBleStatus("Choose BALAT-C3 in the browser prompt.");
    try {
      if (!window.isSecureContext) throw new Error("Web Bluetooth requires HTTPS or localhost.");
      const bluetooth = (navigator as Navigator & { bluetooth?: { requestDevice(options: unknown): Promise<BluetoothDevice> } }).bluetooth;
      if (!bluetooth) throw new Error("Web Bluetooth is unavailable in this browser.");
      device = await bluetooth.requestDevice({ filters: [{ namePrefix: "BALAT" }], optionalServices: [BALAT_BLE_SERVICE] });
      const server = await device.gatt?.connect();
      if (!server) throw new Error("Could not connect to BALAT-C3 GATT server.");
      const service = await server?.getPrimaryService(BALAT_BLE_SERVICE);
      const characteristic = await service?.getCharacteristic(BALAT_BLE_CONTROL);
      const statusCharacteristic = await service?.getCharacteristic(BALAT_BLE_STATUS);
      if (!characteristic || !statusCharacteristic) throw new Error("BALAT BLE characteristics were not found.");
      await statusCharacteristic.startNotifications();
      device.addEventListener("gattserverdisconnected", () => {
        setBleCharacteristic(null);
        setBleReplayRunning(false);
        setBleStatus("ESP32-C3 disconnected.");
        setConnection("connecting");
      });
      statusCharacteristic.addEventListener("characteristicvaluechanged", (event) => {
        const value = (event.target as BluetoothRemoteGATTCharacteristic).value;
        if (!value) return;
        const frame = decodeBleStatus(value);
        if (frame) applyBleFrame(frame);
      });
      setBleCharacteristic(characteristic);
      setBleStatus("Connected to BALAT-C3.");
      setActiveId("ESP32-C3");
      const initial = decodeBleStatus(await statusCharacteristic.readValue());
      if (initial) applyBleFrame(initial);
    } catch (error) {
      device?.gatt?.disconnect();
      setBleCharacteristic(null);
      setBleStatus(error instanceof Error ? error.message : "BLE connection failed.");
    } finally {
      setBleConnecting(false);
    }
  };
  const controlBleReplay = async (action: "start" | "pause" | "reset" | "gps") => {
    if (!bleCharacteristic) return;
    const command = action === "start" ? 1 : action === "pause" ? 2 : action === "reset" ? 3 : 4;
    setBleControlBusy(true);
    try {
      await bleCharacteristic.writeValue(new Uint8Array([0x20, command]));
      setBleReplayRunning(action === "start");
      setBleStatus(action === "gps" ? "GPS receiver selected." : `BLE replay ${action === "start" ? "started" : action === "pause" ? "paused" : action === "reset" ? "reset" : "stopped"}.`);
    } catch (error) {
      setBleStatus(error instanceof Error ? error.message : "BLE replay command failed.");
    } finally {
      setBleControlBusy(false);
    }
  };
  const moveMockCow = (point: { x_cm: number; y_cm: number }) => {
    const characteristic = bleCharacteristic;
    if (!characteristic || bleReplayRunning) return;
    if (performance.now() - lastMockSend.current < 150) return;
    lastMockSend.current = performance.now();
    const packet = new Uint8Array(9);
    const view = new DataView(packet.buffer);
    packet[0] = 0x10;
    view.setInt32(1, point.x_cm, true);
    view.setInt32(5, point.y_cm, true);
    void characteristic.writeValue(packet).catch((error) => setBleStatus(error instanceof Error ? error.message : "Position update failed"));
  };
  const togglePitchMode = () => {
    const url = new URL(window.location.href);
    if (pitchMode) url.searchParams.delete("pitch");
    else url.searchParams.set("pitch", "1");
    window.history.replaceState({}, "", url);
    window.dispatchEvent(new PopStateEvent("popstate"));
  };

  const controlMockGps = async (action: "start" | "pause" | "reset" | "stop" | "speed", interval = mockInterval) => {
    setMockControlBusy(true);
    setMockControlMessage("");
    try {
      const response = await fetch(`${apiBase}/api/mock/control`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action, interval }),
      });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.error || "Mock GPS command failed");
      setMockGps(payload as MockGpsState);
      const labels = { start: "started", pause: "paused", reset: "reset", stop: "stopped; GPS receiver selected", speed: "fix interval updated" };
      setMockControlMessage(`Mock GPS ${labels[action]}.`);
    } catch (error) {
      setMockControlMessage(error instanceof Error ? error.message : "Mock GPS command failed.");
    } finally {
      setMockControlBusy(false);
    }
  };

  return (
    <main className={pitchMode ? "app-shell pitch-mode" : "app-shell"}>
      <aside className="sidebar">
        <div className="brand"><div className="brand-mark">B</div><div><strong>BALAT</strong><small>FIELD CONSOLE</small></div></div>
        <div className="site-switcher"><span className="site-dot" /><div><b>{benchSource ? benchLabel : "NTT / Kupang"}</b><small>{benchSource ? "Local coordinates · dashboard mock NMEA" : "Corridor 04 · Demo replay"}</small></div><span className="chevron">⌄</span></div>
        <nav>
          {navItems.map((item) => (
            <button key={item} className={view === item ? "nav-item active" : "nav-item"} onClick={() => setView(item)}>
              <span className={`nav-icon icon-${item.toLowerCase().replace(" ", "-")}`} />{item}<span className="nav-arrow">›</span>
            </button>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <div className="readiness"><span className="eyebrow">SYSTEM READINESS</span><div><span className="pulse" /> Bench demo online</div><small>TKT 4 · Edge pipeline verified</small></div>
          <button className="user-card"><span className="avatar">TH</span><span><b>Team BALAT</b><small>Local operator</small></span><span className="more">•••</span></button>
        </div>
      </aside>

      <section className="workspace">
        <header className="topbar">
          <div><span className="eyebrow">{pitchMode ? `BALAT / ${isExplainerView ? "SYSTEM EXPLAINER" : "FIELD CONSOLE"}` : `FIELD OPERATIONS / ${view.toUpperCase()}`}</span><h1>{pitchMode ? isExplainerView ? "How the local risk engine works." : benchSource ? `${benchLabel} · local risk state` : "Corridor 04 · Kupang" : view === "Overview" ? "Good evening, operator." : view}</h1></div>
          <div className="top-actions"><span className="replay-label"><span className="status-dot safe-dot" /> {sourceLabel}</span><span className="clock">{now} WIB</span><button className="pitch-toggle" disabled={bleConnecting} onClick={() => { if (bleCharacteristic) { bleCharacteristic.service?.device?.gatt?.disconnect(); setBleCharacteristic(null); setBleReplayRunning(false); setBleStatus("BLE disconnected."); setConnection("connecting"); } else { void connectBle(); } }}>{bleCharacteristic ? "Disconnect ESP32 BLE" : bleConnecting ? "Connecting…" : "Connect ESP32 BLE"}</button>{pitchMode && <button className="pitch-toggle" onClick={() => setView(isExplainerView ? "Overview" : "How BALAT works")}>{isExplainerView ? "Dashboard" : "How it works"}</button>}<button className="pitch-toggle" onClick={togglePitchMode}>{pitchMode ? "Operator view" : "Pitch snapshot"}</button><button className="icon-button">⚙</button></div>
        </header>

        {bleStatus !== "BLE disconnected" && <div className="ble-status" role="status" aria-live="polite">{bleStatus}</div>}

        {noticeVisible && <div className="notice"><span className="notice-icon">i</span><span><b>{connection === "live" ? "Bench telemetry connected." : "Demo environment."}</b> {connection === "live" ? esp32Source ? bleCharacteristic ? "The ESP32-C3 firmware replay uses synthetic fixtures over BLE; cue outputs still require the physical PCB button." : "The dashboard sends mock NMEA; ESP32 cue outputs still require the physical PCB button." : fpgaNmeaSource ? "Dashboard mock NMEA is parsed and assessed on the FPGA; its JA1 cue is logic-level only." : "Read-only telemetry is arriving from the BALAT bridge." : "The telemetry bridge is unavailable, so this console is showing synthetic collar data."} Animal guidance effectiveness has not been validated in field trials.</span><button onClick={() => setNoticeVisible(false)}>Dismiss</button></div>}

        {bleCharacteristic && <section className="mock-gps-panel" aria-label="ESP32 BLE replay controls">
          <div className="mock-gps-copy">
            <span className="eyebrow">ESP32-C3 BLE REPLAY</span>
            <strong>{bleReplayRunning ? "Firmware replay running" : "Firmware replay paused"}</strong>
            <small>{Math.min(BLE_REPLAY_FIX_COUNT, telemetry?.seq ?? 0)} / {BLE_REPLAY_FIX_COUNT} synthetic fixes · compiled on device</small>
          </div>
          <div className="mock-gps-actions">
            <button onClick={() => void controlBleReplay("start")} disabled={bleControlBusy || bleReplayRunning}>Start replay</button>
            <button onClick={() => void controlBleReplay("pause")} disabled={bleControlBusy || !bleReplayRunning}>Pause</button>
            <button onClick={() => void controlBleReplay("reset")} disabled={bleControlBusy}>Reset</button>
            <button onClick={() => void controlBleReplay("gps")} disabled={bleControlBusy}>GPS mode</button>
          </div>
          <p className="mock-gps-note">This is a 201-fix synthetic firmware replay, not live GNSS. Keep the PCB hold-to-enable button released.</p>
        </section>}

        {serialReplaySource && <section className="mock-gps-panel" aria-label="Mock GPS controls">
          <div className="mock-gps-copy">
            <span className="eyebrow">{fpgaNmeaSource ? "FPGA INPUT SIMULATION" : "ESP32 INPUT SIMULATION"}</span>
            <strong>{mockGps?.mode === "gps" ? fpgaNmeaSource ? "Mock GPS stopped" : "GPS receiver selected" : mockGps?.running ? "Checksummed NMEA replay running" : "Mock GPS paused"}</strong>
            <small>{mockGps ? `${mockGps.index} / ${mockGps.total} fixes · ${mockGps.interval.toFixed(2)} s per fix` : "Waiting for serial bridge status"}</small>
          </div>
          <label className="mock-speed">Fix interval
            <select value={mockInterval} onChange={(event) => { const value = Number(event.target.value); setMockInterval(value); void controlMockGps("speed", value); }} disabled={!mockGps?.available || mockControlBusy}>
              <option value={0.1}>0.10 s</option><option value={0.25}>0.25 s</option><option value={0.5}>0.50 s</option><option value={1}>1.00 s</option>
            </select>
          </label>
          <div className="mock-gps-actions">
            <button onClick={() => void controlMockGps("start")} disabled={!mockGps?.available || mockGps.running || mockControlBusy}>Start</button>
            <button onClick={() => void controlMockGps("pause")} disabled={!mockGps?.available || !mockGps.running || mockControlBusy}>Pause</button>
            <button onClick={() => void controlMockGps("reset")} disabled={!mockGps?.available || mockControlBusy}>Reset</button>
            <button onClick={() => void controlMockGps("stop")} disabled={!mockGps?.available || mockControlBusy}>{fpgaNmeaSource ? "Stop replay" : "GPS mode"}</button>
          </div>
          <p className="mock-gps-note">{fpgaNmeaSource ? "The dashboard streams checksummed NMEA into FPGA UART. Cue observation is JA1 logic output; do not connect it directly to a buzzer or motor." : "Simulation supplies GPS input only. The PCB button must be held to enable bounded buzzer and motor outputs."}</p>
          {mockControlMessage && <small className="mock-gps-message" role="status">{mockControlMessage}</small>}
        </section>}

        <div className="content">
          {pitchMode && !isExplainerView && <section className="pitch-summary" aria-label="Pitch evidence summary">
            <div className="pitch-proof">
              {benchSource ? <>
                <span><b>{telemetry?.seq ?? 0}</b><small>{fpgaNmeaSource ? "FPGA telemetry records" : "accepted ESP32 fixes"}</small></span>
                <span><b>{fpgaNmeaSource ? "STATIC" : telemetry?.map_valid ? "VALID" : "INVALID"}</b><small>{fpgaNmeaSource ? "map status on board" : "embedded map check"}</small></span>
                <span><b>{telemetry?.cue_active === null ? "BOARD" : telemetry?.cue_active ? "ON" : "OFF"}</b><small>{fpgaNmeaSource ? "cue state on FPGA LEDs" : "reported cue output"}</small></span>
              </> : <>
                <span><b>+1.701 ns</b><small>FPGA WNS</small></span>
                <span><b>1,200</b><small>UART frames</small></span>
                <span><b>0 / 0</b><small>CRC / sequence errors</small></span>
              </>}
              <span className="open"><b>OPEN</b><small>animal efficacy</small></span>
            </div>
          </section>}
          {isExplainerView ? <PipelineExplainer /> : <>
          <div className="metric-row">
            <Metric label={benchSource ? "BENCH DEVICE" : "HERD COVERAGE"} value={benchSource ? "01 / 01" : "05 / 05"} detail={benchSource ? `${benchLabel} reporting` : "collars reporting"} accent="green-accent" />
            <Metric label="ACTIVE RISK" value={`${dangerCount + cautionCount} ${benchSource ? "device" : "animals"}`} detail={`${dangerCount} danger · ${cautionCount} caution`} accent="orange-accent" />
            <Metric label="TELEMETRY HEALTH" value={connection === "live" ? "CONNECTED" : connection === "connecting" ? "CONNECTING" : "FALLBACK"} detail={telemetry?.source === "ESP32_UART" || telemetry?.source === "BASYS3_NMEA_UART" ? `${telemetry.fix_valid ? "fix accepted" : "fix invalid"} · ${fpgaNmeaSource ? "map/cue fault on board LEDs" : `map ${telemetry.map_valid ? "valid" : "invalid"}`} · seq ${telemetry.seq}` : telemetry ? `frame ${telemetry.seq} · quality ${telemetry.quality}%` : "Bridge at localhost:8888"} accent="green-accent" />
            <Metric label="MAP VERSION" value={fpgaNmeaSource ? "STATIC" : benchSource ? telemetry?.map_valid ? "v1 · VALID" : "INVALID" : "v0.4.2"} detail={benchSource ? fpgaNmeaSource ? "one FPGA demo segment" : "embedded firmware map" : "synced 18 min ago"} />
          </div>

          <div className="main-grid">
            <MapPanel
              animals={visibleAnimals}
              activeId={activeId}
              onSelect={setActiveId}
              esp32Source={benchSource}
              livePoint={livePoint}
              onMoveMock={moveMockCow}
            />
            <section className="risk-card">
              <div className="card-header"><div><span className="eyebrow">SELECTED COLLAR</span><h2>{selected.name}</h2></div><RiskBadge risk={selected.risk} /></div>
              <div className={`risk-hero ${tone[selected.risk]}`}><span className="eyebrow">CURRENT APPROACH STATE</span><strong>{selected.risk === "INVALID" ? "Fix or map invalid · cue inhibited" : selected.risk === "DANGER" ? "Approach risk detected" : selected.risk === "CAUTION" ? "Entering caution zone" : selected.risk === "COOLDOWN" ? "Cue cooldown active" : "No approach risk"}</strong><span>{selected.distance} from mapped road segment</span></div>
              <div className="detail-grid"><div><span className="eyebrow">LOCATION</span><b>{selected.region}</b></div><div><span className="eyebrow">LAST FIX</span><b>{selected.lastSeen}</b></div><div><span className="eyebrow">BATTERY</span><b>{selected.battery > 0 ? `${selected.battery}%` : "—"}</b></div><div><span className="eyebrow">PATH</span><b>{selected.signal === "EDGE" ? "Direct edge" : "Phone mule"}</b></div></div>
              <div className="cue-control"><div><span className="eyebrow">CUE OUTPUT</span><p>{cue ? "UI presentation only · no device command sent" : "Hardware output remains independent"}</p></div><button className={cue ? "cue-button armed" : "cue-button"} onClick={() => setCue(!cue)}>{cue ? "DEMO ON" : "UI DEMO"}</button></div>
            </section>
          </div>

          <section className="herd-section">
            <div className="section-heading"><div><span className="eyebrow">{benchSource ? "BENCH DEVICE" : "HERD MONITOR"}</span><h2>{benchSource ? `${benchLabel} status` : "Live collar status"}</h2></div><button className="outline-button">Export CSV <span>↗</span></button></div>
            <div className="table-wrap">
              <table><thead><tr><th>COLLAR</th><th>RISK STATE</th><th>ROAD DISTANCE</th><th>LAST FIX</th><th>BATTERY</th><th>LINK</th></tr></thead>
                <tbody>{visibleAnimals.map((animal) => <tr key={animal.id} className={activeId === animal.id ? "selected-row" : ""} onClick={() => setActiveId(animal.id)}><td><span className={`animal-avatar ${tone[animal.risk]}`}>●</span><b>{animal.id}</b><small>{animal.region}</small></td><td><RiskBadge risk={animal.risk} /></td><td className="distance">{animal.distance}</td><td className="muted">{animal.lastSeen}</td><td><div className="battery"><span style={{ width: `${animal.battery}%` }} /><small>{animal.battery}%</small></div></td><td><span className={`link-status ${animal.signal === "EDGE" ? "edge" : "mule"}`}>{animal.signal === "EDGE" ? "● edge" : "↗ mule"}</span></td></tr>)}</tbody>
              </table>
            </div>
          </section>

          <div className="bottom-grid">
            <section className="events-card"><div className="section-heading"><div><span className="eyebrow">EVENT STREAM</span><h2>{benchSource ? `Latest ${benchLabel} decision` : "Recent system events"}</h2></div><span className="live-tag"><span className="pulse" /> {benchSource ? "LIVE" : "SAMPLE"}</span></div><div className="event-list">{benchSource ? <div><span className="event-time">{now}</span><span className={`event-icon ${tone[selected.risk]}`}>{selected.risk === "INVALID" ? "!" : selected.risk === "DANGER" ? "!" : "✓"}</span><p><b>{selected.risk} · {selected.distance} from mapped road</b><small>Fix {telemetry?.fix_valid ? "valid" : "invalid"} · map {telemetry?.map_valid ? "valid" : "invalid"} · cue {telemetry?.cue_active === null ? "state shown on board" : telemetry?.cue_active ? "active" : "inactive"} · sequence {telemetry?.seq}</small></p></div> : <><div><span className="event-time">23:49:45</span><span className="event-icon danger">!</span><p><b>BLT-042 entered danger zone</b><small>Road segment RS-04 · cue scheduler held for validation</small></p></div><div><span className="event-time">23:49:31</span><span className="event-icon green">↗</span><p><b>HerdSync record received</b><small>BLT-008 via phone mule · sequence 1,200</small></p></div><div><span className="event-time">23:48:56</span><span className="event-icon blue">✓</span><p><b>Map manifest verified</b><small>v0.4.2 · 32 road segments · CRC valid</small></p></div></>}</div></section>
            <section className="evidence-card"><div className="section-heading"><div><span className="eyebrow">VERIFICATION</span><h2>Evidence snapshot</h2></div><span className="tkt-tag">TKT 4</span></div><div className="evidence-list"><div><span>FPGA timing closure</span><b>+1.701 ns WNS</b></div><div><span>UART soak test</span><b>1,200 frames</b></div><div><span>CRC / sequence errors</span><b className="green-text">0 / 0</b></div><div><span>Animal efficacy</span><b className="orange-text">Not validated</b></div></div><div className="evidence-foot">Bench evidence only · See verification docs</div></section>
          </div>
          </>}
        </div>
      </section>
    </main>
  );
}
