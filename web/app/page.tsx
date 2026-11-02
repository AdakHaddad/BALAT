"use client";

import { useEffect, useMemo, useState } from "react";

type Risk = "SAFE" | "CAUTION" | "DANGER";
type ConnectionState = "connecting" | "live" | "fallback";

type TelemetryState = {
  dist_m: number;
  risk_name: string;
  battery_mv: number;
  quality: number;
  source: string;
  seq: number;
  link_status: string;
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

const initialAnimals: Animal[] = [
  { id: "BLT-042", name: "Collar 042", region: "Kupang / NTT", risk: "DANGER", distance: "24 m", lastSeen: "8 sec ago", battery: 82, signal: "EDGE" },
  { id: "BLT-017", name: "Collar 017", region: "Sumba Timur", risk: "CAUTION", distance: "86 m", lastSeen: "12 sec ago", battery: 74, signal: "EDGE" },
  { id: "BLT-008", name: "Collar 008", region: "Bojonegoro", risk: "SAFE", distance: "312 m", lastSeen: "18 sec ago", battery: 91, signal: "MULE" },
  { id: "BLT-031", name: "Collar 031", region: "Tuban", risk: "SAFE", distance: "428 m", lastSeen: "24 sec ago", battery: 66, signal: "EDGE" },
  { id: "BLT-053", name: "Collar 053", region: "Kupang / NTT", risk: "SAFE", distance: "515 m", lastSeen: "31 sec ago", battery: 58, signal: "MULE" },
];

const tone: Record<Risk, string> = {
  SAFE: "safe",
  CAUTION: "caution",
  DANGER: "danger",
};

function RiskBadge({ risk }: { risk: Risk }) {
  return <span className={`risk-badge ${tone[risk]}`}><span className="status-dot" />{risk}</span>;
}

function toRisk(value: string): Risk {
  return value === "DANGER" || value === "CAUTION" ? value : "SAFE";
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

function MapPanel({ activeId, onSelect }: { activeId: string; onSelect: (id: string) => void }) {
  const points = [
    { id: "BLT-042", x: 69, y: 58, risk: "DANGER" as Risk },
    { id: "BLT-017", x: 48, y: 36, risk: "CAUTION" as Risk },
    { id: "BLT-008", x: 28, y: 67, risk: "SAFE" as Risk },
    { id: "BLT-031", x: 57, y: 76, risk: "SAFE" as Risk },
    { id: "BLT-053", x: 82, y: 29, risk: "SAFE" as Risk },
  ];

  return (
    <div className="map-panel">
      <div className="map-header">
        <div>
          <span className="eyebrow">LOCAL ROAD MEMORY</span>
          <h2>Corridor watch</h2>
        </div>
        <span className="map-chip"><span className="status-dot safe-dot" />OFFLINE MAP</span>
      </div>
      <div className="map">
        <div className="map-label label-a">JALAN PROVINSI</div>
        <div className="map-label label-b">GRAZING ZONE 04</div>
        <svg viewBox="0 0 100 100" preserveAspectRatio="none" aria-label="Synthetic corridor map">
          <path className="terrain-line" d="M0,72 C18,58 19,80 34,60 S50,40 63,52 S78,76 100,53" />
          <path className="terrain-line faint" d="M0,22 C18,30 24,12 42,27 S65,38 80,20 S94,15 100,28" />
          <path className="road-line" d="M-5,84 C17,71 20,46 38,50 S63,67 74,45 S88,20 105,17" />
          <path className="road-line secondary" d="M-5,88 C17,75 20,50 38,54 S63,71 74,49 S88,24 105,21" />
          <path className="danger-zone" d="M58,74 C62,51 69,38 86,31" />
        </svg>
        {points.map((point) => (
          <button
            className={`map-point ${tone[point.risk]} ${activeId === point.id ? "active" : ""}`}
            key={point.id}
            style={{ left: `${point.x}%`, top: `${point.y}%` }}
            onClick={() => onSelect(point.id)}
            aria-label={`Select ${point.id}`}
          >
            <span />
            <b>{point.id.replace("BLT-", "")}</b>
          </button>
        ))}
        <div className="map-scale"><span /> 500 m</div>
      </div>
      <div className="map-legend">
        <span><i className="legend-road" /> road segment</span>
        <span><i className="legend-zone" /> approach zone</span>
        <span><i className="legend-animal" /> collar</span>
      </div>
    </div>
  );
}

export default function Home() {
  const [activeId, setActiveId] = useState("BLT-042");
  const [animals, setAnimals] = useState(initialAnimals);
  const [now, setNow] = useState("23:49:53");
  const [view, setView] = useState("Overview");
  const [cue, setCue] = useState(false);
  const [connection, setConnection] = useState<ConnectionState>("connecting");
  const [telemetry, setTelemetry] = useState<TelemetryState | null>(null);
  const [noticeVisible, setNoticeVisible] = useState(true);

  const apiBase = process.env.NEXT_PUBLIC_BALAT_API_URL?.replace(/\/$/, "") || "http://localhost:8888";

  useEffect(() => {
    let cancelled = false;

    const pollTelemetry = async () => {
      try {
        const response = await fetch(`${apiBase}/api/state`, { cache: "no-store" });
        if (!response.ok) throw new Error(`Telemetry request failed: ${response.status}`);
        const nextTelemetry = (await response.json()) as TelemetryState;
        if (cancelled) return;
        setTelemetry(nextTelemetry);
        setConnection("live");
        setAnimals((items) => items.map((animal, index) => index === 0 ? {
          ...animal,
          risk: toRisk(nextTelemetry.risk_name),
          distance: formatDistance(nextTelemetry.dist_m),
          lastSeen: "just now",
          battery: nextTelemetry.battery_mv > 0
            ? Math.min(100, Math.max(0, Math.round((nextTelemetry.battery_mv / 4200) * 100)))
            : animal.battery,
          signal: nextTelemetry.source === "BASYS3_UART" ? "EDGE" : animal.signal,
        } : animal));
      } catch {
        if (!cancelled) setConnection("fallback");
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
  }, [apiBase, connection]);

  const selected = useMemo(() => animals.find((animal) => animal.id === activeId) ?? animals[0], [activeId, animals]);
  const dangerCount = animals.filter((animal) => animal.risk === "DANGER").length;
  const cautionCount = animals.filter((animal) => animal.risk === "CAUTION").length;
  const sourceLabel = connection === "live" ? "LIVE FPGA TELEMETRY" : connection === "connecting" ? "CONNECTING TO BRIDGE" : "SYNTHETIC TRACE FALLBACK";

  return (
    <main className="app-shell">
      <aside className="sidebar">
        <div className="brand"><div className="brand-mark">B</div><div><strong>BALAT</strong><small>FIELD CONSOLE</small></div></div>
        <div className="site-switcher"><span className="site-dot" /><div><b>NTT / Kupang</b><small>Corridor 04 · Demo replay</small></div><span className="chevron">⌄</span></div>
        <nav>
          {["Overview", "Herd monitor", "Road memory", "Telemetry log"].map((item) => (
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
          <div><span className="eyebrow">FIELD OPERATIONS / {view.toUpperCase()}</span><h1>{view === "Overview" ? "Good evening, operator." : view}</h1></div>
          <div className="top-actions"><span className="replay-label"><span className="status-dot safe-dot" /> {sourceLabel}</span><span className="clock">{now} WIB</span><button className="icon-button">⚙</button></div>
        </header>

        {noticeVisible && <div className="notice"><span className="notice-icon">i</span><span><b>{connection === "live" ? "Bench telemetry connected." : "Demo environment."}</b> {connection === "live" ? "Read-only data is arriving from the BALAT bridge. Animal guidance effectiveness has not been validated in field trials." : "The telemetry bridge is unavailable, so this console is showing synthetic collar data. Animal guidance effectiveness has not been validated in field trials."}</span><button onClick={() => setNoticeVisible(false)}>Dismiss</button></div>}

        <div className="content">
          <div className="metric-row">
            <Metric label="HERD COVERAGE" value="05 / 05" detail="collars reporting" accent="green-accent" />
            <Metric label="ACTIVE RISK" value={`${dangerCount + cautionCount} animals`} detail={`${dangerCount} danger · ${cautionCount} caution`} accent="orange-accent" />
            <Metric label="TELEMETRY HEALTH" value={connection === "live" ? "CONNECTED" : connection === "connecting" ? "CONNECTING" : "FALLBACK"} detail={telemetry ? `frame ${telemetry.seq} · quality ${telemetry.quality}%` : "Bridge at localhost:8888"} accent="green-accent" />
            <Metric label="MAP VERSION" value="v0.4.2" detail="synced 18 min ago" />
          </div>

          <div className="main-grid">
            <MapPanel activeId={activeId} onSelect={setActiveId} />
            <section className="risk-card">
              <div className="card-header"><div><span className="eyebrow">SELECTED COLLAR</span><h2>{selected.name}</h2></div><RiskBadge risk={selected.risk} /></div>
              <div className={`risk-hero ${tone[selected.risk]}`}><span className="eyebrow">CURRENT APPROACH STATE</span><strong>{selected.risk === "DANGER" ? "Approach risk detected" : selected.risk === "CAUTION" ? "Entering caution zone" : "No approach risk"}</strong><span>{selected.distance} from mapped road segment</span></div>
              <div className="detail-grid"><div><span className="eyebrow">LOCATION</span><b>{selected.region}</b></div><div><span className="eyebrow">LAST FIX</span><b>{selected.lastSeen}</b></div><div><span className="eyebrow">BATTERY</span><b>{selected.battery}%</b></div><div><span className="eyebrow">PATH</span><b>{selected.signal === "EDGE" ? "Direct edge" : "Phone mule"}</b></div></div>
              <div className="cue-control"><div><span className="eyebrow">CUE OUTPUT</span><p>{cue ? "Presentation test only; no FPGA command sent" : "Output is inactive by default"}</p></div><button className={cue ? "cue-button armed" : "cue-button"} onClick={() => setCue(!cue)}>{cue ? "ARMED" : "TEST CUE"}</button></div>
            </section>
          </div>

          <section className="herd-section">
            <div className="section-heading"><div><span className="eyebrow">HERD MONITOR</span><h2>Live collar status</h2></div><button className="outline-button">Export CSV <span>↗</span></button></div>
            <div className="table-wrap">
              <table><thead><tr><th>COLLAR</th><th>RISK STATE</th><th>ROAD DISTANCE</th><th>LAST FIX</th><th>BATTERY</th><th>LINK</th></tr></thead>
                <tbody>{animals.map((animal) => <tr key={animal.id} className={activeId === animal.id ? "selected-row" : ""} onClick={() => setActiveId(animal.id)}><td><span className={`animal-avatar ${tone[animal.risk]}`}>●</span><b>{animal.id}</b><small>{animal.region}</small></td><td><RiskBadge risk={animal.risk} /></td><td className="distance">{animal.distance}</td><td className="muted">{animal.lastSeen}</td><td><div className="battery"><span style={{ width: `${animal.battery}%` }} /><small>{animal.battery}%</small></div></td><td><span className={`link-status ${animal.signal === "EDGE" ? "edge" : "mule"}`}>{animal.signal === "EDGE" ? "● edge" : "↗ mule"}</span></td></tr>)}</tbody>
              </table>
            </div>
          </section>

          <div className="bottom-grid">
            <section className="events-card"><div className="section-heading"><div><span className="eyebrow">EVENT STREAM</span><h2>Recent system events</h2></div><span className="live-tag"><span className="pulse" /> LIVE</span></div><div className="event-list"><div><span className="event-time">23:49:45</span><span className="event-icon danger">!</span><p><b>BLT-042 entered danger zone</b><small>Road segment RS-04 · cue scheduler held for validation</small></p></div><div><span className="event-time">23:49:31</span><span className="event-icon green">↗</span><p><b>HerdSync record received</b><small>BLT-008 via phone mule · sequence 1,200</small></p></div><div><span className="event-time">23:48:56</span><span className="event-icon blue">✓</span><p><b>Map manifest verified</b><small>v0.4.2 · 32 road segments · CRC valid</small></p></div></div></section>
            <section className="evidence-card"><div className="section-heading"><div><span className="eyebrow">VERIFICATION</span><h2>Evidence snapshot</h2></div><span className="tkt-tag">TKT 4</span></div><div className="evidence-list"><div><span>FPGA timing closure</span><b>+1.701 ns WNS</b></div><div><span>UART soak test</span><b>1,200 frames</b></div><div><span>CRC / sequence errors</span><b className="green-text">0 / 0</b></div><div><span>Animal efficacy</span><b className="orange-text">Not validated</b></div></div><div className="evidence-foot">Bench evidence only · See verification docs</div></section>
          </div>
        </div>
      </section>
    </main>
  );
}
