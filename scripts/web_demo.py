#!/usr/bin/env python3
"""BALAT Live Web UI Demo Server.

Streams collar risk assessment, distance calculations, and cue activation
to any web browser on laptop or phone.

Usage:
    python3 scripts/web_demo.py [--port 8888] [--simulate]
    python3 scripts/web_demo.py --serial /dev/ttyUSB1 [--baud 115200]

Open in browser:
    Laptop: http://localhost:8888
    Phone:  http://<laptop-ip>:8888
"""

from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import json
import math
import os
import re
import socket
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

REPO = Path(__file__).resolve().parent.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from poc.herdsync_dtn.uart_frame import (  # noqa: E402
    TYPE_RECORD,
    FrameParser,
    decode_record_payload,
)

RISK_NAMES = {0: "INVALID", 1: "SAFE", 2: "CAUTION", 3: "DANGER", 4: "COOLDOWN"}

# Current live telemetry state (thread-safe)
STATE_LOCK = threading.Lock()
CURRENT_STATE = {
    "x_cm": 0,
    "y_cm": 0,
    "dist_m": 0.0,
    "risk": 0,          # 0=INVALID, 1=SAFE, 2=CAUTION, 3=DANGER, 4=COOLDOWN
    "risk_name": "INVALID",
    "speed_kmh": 0.0,
    "approaching": False,
    "cue_active": None,  # UART record v1 does not export LED5/cue_out.
    "cooldown": False,
    "battery_mv": 0,
    "quality": 0,
    "seq": 0,
    "fix_time_s": 0,
    "source": "WAITING",
    "link_status": "Select a telemetry source.",
}

RECORD_FIELDS = (
    "captured_at_utc", "elapsed_ms", "event", "source", "seq", "x_cm",
    "y_cm", "dist_m", "risk", "risk_name", "speed_kmh", "approaching",
    "cue_active", "cooldown", "battery_mv", "quality", "fix_time_s",
    "link_status",
)


class SessionRecorder:
    """Write local, append-only POC telemetry sessions as CSV.

    This class is intentionally capture-only: it has no interface to the FPGA,
    cue output, or board controls. A row is written when the telemetry producer
    publishes a fresh state, rather than on every browser poll.
    """

    def __init__(self, record_dir: Path):
        self._record_dir = record_dir
        self._lock = threading.Lock()
        self._file = None
        self._writer = None
        self._path = None
        self._started_at = None
        self._stopped_at = None
        self._started_monotonic = None
        self._row_count = 0
        self._last_risk = None
        self._last_cue_active = None

    @staticmethod
    def _safe_label(label: object) -> str:
        value = str(label or "poc").strip().lower()
        value = re.sub(r"[^a-z0-9_-]+", "-", value).strip("-_")
        return (value or "poc")[:40]

    def start(self, label: object = "poc") -> dict:
        with self._lock:
            if self._file is not None:
                raise RuntimeError("recording is already active")

            self._record_dir.mkdir(parents=True, exist_ok=True)
            self._started_at = datetime.now(timezone.utc)
            stamp = self._started_at.strftime("%Y%m%dT%H%M%S_%fZ")
            filename = f"balat_{self._safe_label(label)}_{stamp}.csv"
            self._path = self._record_dir / filename
            self._file = self._path.open("x", newline="", encoding="utf-8")
            self._writer = csv.DictWriter(self._file, fieldnames=RECORD_FIELDS)
            self._writer.writeheader()
            self._file.flush()
            self._started_monotonic = time.monotonic()
            self._stopped_at = None
            self._row_count = 0
            self._last_risk = None
            self._last_cue_active = None
            return self._status_locked()

    def record(self, state: dict) -> None:
        """Capture one producer update, if a session is active."""
        with self._lock:
            if self._file is None:
                return

            risk_name = str(state.get("risk_name", "UNKNOWN"))
            cue_value = state.get("cue_active")
            cue_active = cue_value is True
            events = []
            if self._last_risk != risk_name:
                events.append(f"risk:{risk_name}")
            if cue_value is not None and self._last_cue_active is not None:
                if cue_active and not self._last_cue_active:
                    events.append("cue:on")
                if not cue_active and self._last_cue_active:
                    events.append("cue:off")

            elapsed_ms = int((time.monotonic() - self._started_monotonic) * 1000)
            row = {field: state.get(field, "") for field in RECORD_FIELDS}
            row.update({
                "captured_at_utc": datetime.now(timezone.utc).isoformat(),
                "elapsed_ms": elapsed_ms,
                "event": ";".join(events),
                "risk_name": risk_name,
                "cue_active": int(cue_active) if cue_value is not None else "",
                "approaching": int(bool(state.get("approaching", False))),
                "cooldown": int(bool(state.get("cooldown", False))),
            })
            self._writer.writerow(row)
            self._file.flush()
            self._row_count += 1
            self._last_risk = risk_name
            self._last_cue_active = cue_active if cue_value is not None else None

    def stop(self) -> dict:
        with self._lock:
            if self._file is not None:
                self._file.close()
                self._file = None
                self._writer = None
                self._stopped_at = datetime.now(timezone.utc)
            return self._status_locked()

    def status(self) -> dict:
        with self._lock:
            return self._status_locked()

    def download_path(self) -> Path | None:
        with self._lock:
            if self._file is not None:
                self._file.flush()
            return self._path

    def _status_locked(self) -> dict:
        return {
            "active": self._file is not None,
            "filename": self._path.name if self._path else None,
            "rows": self._row_count,
            "started_at_utc": self._started_at.isoformat() if self._started_at else None,
            "stopped_at_utc": self._stopped_at.isoformat() if self._stopped_at else None,
        }


RECORDER = SessionRecorder(REPO / "build" / "poc_records")

# The loaded OSM-derived segments are a dashboard reference layer only. The
# current Basys3 UART bitstream uses the single synthetic segment below; it does
# not load data/road_segments.csv at runtime.
ACTIVE_DEMO_MAP = {
    "name": "Basys3 synthetic demo map",
    "coordinate_unit": "centimetres",
    "crs": "local synthetic Cartesian coordinates",
    "segments": [{"id": "demo-road", "ax": -2000, "ay": 0, "bx": 2000, "by": 0}],
}
MAP_DATA = {
    "active": ACTIVE_DEMO_MAP,
    "reference": {"available": False, "reason": "No reference map loaded."},
}


def load_reference_map(segment_path: Path, manifest_path: Path) -> dict:
    """Load a bounded local map layer for dashboard context, never FPGA control."""
    reference = {"available": False, "reason": "Reference map files not found."}
    if not segment_path.is_file() or not manifest_path.is_file():
        return {"active": ACTIVE_DEMO_MAP, "reference": reference}

    try:
        with manifest_path.open(encoding="utf-8") as stream:
            manifest = json.load(stream)
        with segment_path.open(newline="", encoding="utf-8") as stream:
            reader = csv.DictReader(stream)
            segments = [
                {
                    "id": row["seg_id"], "ax": int(row["ax"]), "ay": int(row["ay"]),
                    "bx": int(row["bx"]), "by": int(row["by"]),
                    "road_class": int(row["road_class"]),
                }
                for row in reader
            ]
        if not segments:
            raise ValueError("segment CSV is empty")
        reference = {
            "available": True,
            "segment_count": len(segments),
            "source": manifest.get("source", "unknown"),
            "license": manifest.get("license", "unknown"),
            "extraction_utc": manifest.get("extraction_utc", "unknown"),
            "crs": manifest.get("crs", "unknown"),
            "coordinate_unit": manifest.get("coordinate_unit", "unknown"),
            "origin_lat": manifest.get("origin_lat"),
            "origin_lon": manifest.get("origin_lon"),
            "segments": segments,
            "notice": "Reference layer only; not loaded into the current Basys3 demo bitstream.",
        }
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        reference = {"available": False, "reason": f"Reference map unavailable: {exc}"}
    return {"active": ACTIVE_DEMO_MAP, "reference": reference}


def publish_state(update: dict) -> None:
    """Publish a telemetry sample and offer it to the local recorder."""
    with STATE_LOCK:
        CURRENT_STATE.update(update)
        snapshot = dict(CURRENT_STATE)
    RECORDER.record(snapshot)


def set_transport_status(source: str, message: str) -> None:
    """Update connection UI state without creating a telemetry CSV row."""
    with STATE_LOCK:
        CURRENT_STATE["source"] = source
        CURRENT_STATE["link_status"] = message


def demo_road_distance_cm(x_cm: int, y_cm: int) -> float:
    """Distance to the fixed demo segment: (-2000, 0) to (2000, 0), in cm."""
    nearest_x = min(2000, max(-2000, int(x_cm)))
    return math.hypot(int(x_cm) - nearest_x, int(y_cm))


def state_from_uart_record(record: dict, previous: dict) -> dict:
    """Convert one validated FPGA UART record into dashboard telemetry.

    The UART v1 record carries the actual FPGA position and risk state. Distance,
    approach, and speed are host-side display calculations for the fixed synthetic
    demo road; cue-active is deliberately left unavailable because LED5 is not
    exported in this record format.
    """
    x_cm = int(record["x_cm"])
    y_cm = int(record["y_cm"])
    distance_cm = demo_road_distance_cm(x_cm, y_cm)
    seq = int(record["seq"])
    previous_seq = int(previous.get("seq", 0))
    seq_delta = seq - previous_seq
    if (previous.get("source") == "BASYS3_UART"
            and "dist_m" in previous and seq_delta > 0):
        dx_cm = x_cm - int(previous["x_cm"])
        dy_cm = y_cm - int(previous["y_cm"])
        speed_kmh = round((math.hypot(dx_cm, dy_cm) / 100.0) / (seq_delta * 0.1) * 3.6, 1)
        approaching = distance_cm < float(previous["dist_m"]) * 100.0
    else:
        speed_kmh = 0.0
        approaching = False

    risk = int(record["risk"])
    return {
        "x_cm": x_cm,
        "y_cm": y_cm,
        "dist_m": round(distance_cm / 100.0, 2),
        "risk": risk,
        "risk_name": RISK_NAMES.get(risk, "INVALID"),
        "speed_kmh": speed_kmh,
        "approaching": approaching,
        "cue_active": None,
        "cooldown": risk == 4,
        "battery_mv": int(record["battery_mv"]),
        "quality": int(record["quality"]),
        "seq": seq,
        "fix_time_s": int(record["fix_time_s"]),
        "source": "BASYS3_UART",
        "link_status": "Receiving validated FPGA UART records.",
    }


def run_uart_telemetry(port: str, baud: int) -> None:
    """Read-only USB-UART worker for the HerdSync Basys3 bench bitstream."""
    try:
        import serial
    except ImportError:
        set_transport_status("BASYS3_UART", "pyserial missing: python3 -m pip install pyserial")
        return

    while True:
        try:
            serial_port = serial.Serial(port, baud, timeout=0.1)
        except serial.SerialException as exc:
            set_transport_status("BASYS3_UART", f"UART unavailable: {exc}; retrying")
            time.sleep(1.0)
            continue

        parser = FrameParser()
        set_transport_status("BASYS3_UART", f"Connected to {port}; waiting for FPGA records.")
        try:
            while True:
                chunk = serial_port.read(256)
                if not chunk:
                    continue
                for frame in parser.feed(chunk):
                    if frame.frame_type != TYPE_RECORD:
                        continue
                    try:
                        record = decode_record_payload(frame.payload)
                    except ValueError:
                        continue
                    with STATE_LOCK:
                        previous = dict(CURRENT_STATE)
                    publish_state(state_from_uart_record(record, previous))
        except serial.SerialException as exc:
            set_transport_status("BASYS3_UART", f"UART read failed: {exc}; reconnecting")
        finally:
            serial_port.close()
        time.sleep(1.0)

# ---------------------------------------------------------------------------
# Background Simulation Worker (Generates Telemetry from Demo Trace)
# ---------------------------------------------------------------------------

def run_simulation(interval: float = 0.25):
    trace_path = REPO / "data" / "demo_trace.csv"
    points = []
    if trace_path.exists():
        with open(trace_path) as f:
            for row in csv.DictReader(f):
                points.append((int(row["x_cm"]), int(row["y_cm"])))
    if not points:
        points = [(-1500 + i * 15, 1000 - i * 10) for i in range(200)]

    seq = 0
    cue_ticks_left = 0
    cooldown_ticks_left = 0

    previous_distance_cm = None

    while True:
        for x_cm, y_cm in points:
            seq += 1
            # The actual FPGA demo road is horizontal: (-2000, 0) to (2000, 0).
            dist_cm = demo_road_distance_cm(x_cm, y_cm)
            dist_m = round(dist_cm / 100.0, 2)

            # Risk FSM logic mirror
            if cooldown_ticks_left > 0:
                risk = 4  # COOLDOWN
                cooldown_ticks_left -= 1
                cue_active = False
            elif dist_cm <= 200:
                risk = 3  # DANGER
                if cue_ticks_left == 0 and cooldown_ticks_left == 0:
                    cue_ticks_left = 3
                cue_active = (cue_ticks_left > 0)
                if cue_ticks_left > 0:
                    cue_ticks_left -= 1
                    if cue_ticks_left == 0:
                        cooldown_ticks_left = 6
            elif dist_cm <= 500:
                risk = 2  # CAUTION
                cue_active = False
            else:
                risk = 1  # SAFE
                cue_active = False

            publish_state({
                "x_cm": x_cm,
                "y_cm": y_cm,
                "dist_m": dist_m,
                "risk": risk,
                "risk_name": RISK_NAMES.get(risk, "UNKNOWN"),
                "approaching": previous_distance_cm is not None and dist_cm < previous_distance_cm,
                "cue_active": cue_active,
                "cooldown": (risk == 4),
                "seq": seq,
                "speed_kmh": 3.6,
                "quality": 100,
                "fix_time_s": seq // 10,
                "source": "SIMULATION",
                "link_status": "Synthetic trace; not connected to the FPGA.",
            })
            previous_distance_cm = dist_cm

            time.sleep(interval)


# ---------------------------------------------------------------------------
# HTML Dashboard Template (Single file, Zero dependencies)
# ---------------------------------------------------------------------------

HTML_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<title>BALAT | Autonomous Livestock Safety Demo</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" integrity="sha256-p4NxAoJBhIIN+hmNHrzRCf9tD/miZyoHS5obTRR9BMY=" crossorigin="">
<style>
  :root {
    --bg: #0b0f19;
    --card: #151d30;
    --border: #222f4c;
    --safe: #10b981;
    --caution: #f59e0b;
    --danger: #ef4444;
    --cooldown: #3b82f6;
    --text: #f1f5f9;
    --subtext: #94a3b8;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; }
  body { background: var(--bg); color: var(--text); padding: 16px; min-height: 100vh; }
  .header { display: flex; justify-content: space-between; align-items: center; padding: 4px 0 18px; border-bottom: 1px solid var(--border); margin-bottom: 16px; }
  .title { font-size: 24px; font-weight: 800; letter-spacing: 1px; }
  .badge { background: #1e293b; color: var(--safe); padding: 4px 10px; border-radius: 9999px; font-size: 12px; font-weight: 600; text-transform: uppercase; border: 1px solid var(--border); }
  .link-note { font-size: 11px; color: var(--subtext); margin-top: 6px; max-width: 320px; text-align: right; }
  .grid { display: grid; grid-template-columns: minmax(0, 1fr); gap: 14px; max-width: 900px; margin: 0 auto; }
  @media(min-width: 768px) { .grid { grid-template-columns: 1.2fr 1fr; } }
  
  .card { min-width: 0; overflow: hidden; background: var(--card); border: 1px solid var(--border); border-radius: 12px; padding: 16px; box-shadow: 0 4px 20px rgba(0,0,0,0.3); }
  .card-title { font-size: 13px; text-transform: uppercase; color: var(--subtext); letter-spacing: 1px; margin-bottom: 10px; font-weight: 600; }
  
  /* Risk Banner */
  .risk-gauge { border-radius: 10px; padding: 20px; text-align: center; font-size: 32px; font-weight: 800; letter-spacing: 2px; transition: all 0.3s ease; }
  .risk-SAFE { background: rgba(16, 185, 129, 0.15); color: var(--safe); border: 2px solid var(--safe); }
  .risk-CAUTION { background: rgba(245, 158, 11, 0.15); color: var(--caution); border: 2px solid var(--caution); }
  .risk-DANGER { background: rgba(239, 68, 68, 0.25); color: var(--danger); border: 2px solid var(--danger); animation: pulse 0.8s infinite alternate; }
  .risk-COOLDOWN { background: rgba(59, 130, 246, 0.15); color: var(--cooldown); border: 2px solid var(--cooldown); }
  @keyframes pulse { from { box-shadow: 0 0 10px rgba(239, 68, 68, 0.3); } to { box-shadow: 0 0 25px rgba(239, 68, 68, 0.8); } }

  /* Metrics grid */
  .metrics { display: grid; grid-template-columns: minmax(0, 1fr); gap: 10px; margin-top: 12px; }
  .metric-box { background: #0f172a; padding: 14px; border-radius: 8px; border: 1px solid var(--border); }
  .metric-val { font-size: 24px; font-weight: 700; margin-top: 3px; }
  .metric-unit { font-size: 12px; color: var(--subtext); margin-left: 3px; font-weight: 400; }
  
  #map { position: relative; width: 100%; max-width: 100%; height: clamp(280px, 48vw, 370px); overflow: hidden; background: #0a0e17; border-radius: 8px; border: 1px solid #1e293b; z-index: 0; }
  .map-legend { display:flex; gap:12px; flex-wrap:wrap; font-size:11px; color:var(--subtext); margin-top:8px; }
  .legend-line { display:inline-block; width:18px; border-top:3px solid; vertical-align:middle; margin-right:4px; }
  .leaflet-container { overflow: hidden; font-family: inherit; }
  .leaflet-popup-content-wrapper, .leaflet-popup-tip { background:#151d30; color:#f1f5f9; }
  
  .map-note { margin-top: 8px; color: var(--subtext); font-size: 11px; }
  .recording { margin-top: 12px; padding: 14px; border-radius: 8px; background: #0f172a; border: 1px solid var(--border); }
  .recording-row { display: flex; gap: 8px; margin-top: 8px; }
  .recording input { min-width: 0; flex: 1; border: 1px solid var(--border); border-radius: 6px; padding: 8px; color: var(--text); background: #0b0f19; }
  .recording button { border: 0; border-radius: 6px; padding: 8px 10px; color: white; font-weight: 600; cursor: pointer; }
  .recording button:disabled { cursor: not-allowed; opacity: .45; }
  .record-start { background: #047857; }
  .record-stop { background: #b91c1c; }
  .record-download { background: #2563eb; width: 100%; margin-top: 8px; }
  .record-status { font-size: 11px; color: var(--subtext); margin-top: 8px; }
</style>
</head>
<body>

<div class="header">
  <div>
    <div class="title">BALAT</div>
    <div style="font-size: 11px; color: var(--subtext); margin-top: 2px;">LIVE ROAD APPROACH</div>
  </div>
  <div style="text-align:right;">
    <div id="conn-badge" class="badge">WAITING</div>
    <div id="link-status" class="link-note">Waiting for telemetry source.</div>
  </div>
</div>

<div class="grid">
  <!-- Map View -->
  <div class="card">
    <div class="card-title">Live map</div>
    <div id="map" role="application" aria-label="Local road map"></div>
    <div class="map-legend">
      <span><i class="legend-line" style="border-color:#ef4444"></i>Active road</span>
      <span><i class="legend-line" style="border-color:#38bdf8"></i>Map roads</span>
      <span><i class="legend-line" style="border-color:#f59e0b"></i>5 m zone</span>
    </div>
    <div id="map-status" class="map-note">Loading map.</div>
  </div>

  <!-- Telemetry & Risk HUD -->
  <div class="card">
    <div class="card-title">Live status</div>
    
    <div id="risk-banner" class="risk-gauge risk-SAFE">SAFE</div>
    
    <div class="metrics">
      <div class="metric-box">
        <div style="font-size:11px; color:var(--subtext);">DISTANCE TO ROAD</div>
        <div class="metric-val"><span id="val-dist">15.0</span><span class="metric-unit">m</span></div>
      </div>
    </div>

    <div class="recording">
      <div style="font-weight:700; font-size:14px;">Capture run</div>
      <div style="font-size:11px; color:var(--subtext); margin-top:3px;">Save the live FPGA data as CSV.</div>
      <div class="recording-row">
        <input id="record-label" maxlength="40" value="basys3-poc" aria-label="POC session label">
        <button id="record-start" class="record-start" onclick="startRecording()">Start</button>
        <button id="record-stop" class="record-stop" onclick="stopRecording()" disabled>Stop</button>
      </div>
      <button id="record-download" class="record-download" onclick="downloadRecording()" disabled>Download data</button>
      <div id="record-status" class="record-status">Not recording.</div>
    </div>

  </div>
</div>

<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js" integrity="sha256-20nQCchB9co0qIjJZRGuk2/Z9VM+kNiyxNV1lvTlZBo=" crossorigin=""></script>
<script>
let mapData = null;
let map = null;
let activeRoad = null;
let collarMarker = null;
let trailLine = null;
let cautionBuffer = null;
let dangerBuffer = null;
const trail = [];

function setRecordingStatus(status) {
  const active = Boolean(status.active);
  document.getElementById('record-start').disabled = active;
  document.getElementById('record-stop').disabled = !active;
  document.getElementById('record-download').disabled = !status.filename;
  const text = active
    ? 'Recording ' + status.rows + ' sample(s): ' + status.filename
    : (status.filename ? 'Stopped: ' + status.rows + ' sample(s) in ' + status.filename : 'Not recording.');
  document.getElementById('record-status').innerText = text;
}

async function recordingRequest(path, body) {
  const options = body === undefined ? {} : {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(body),
  };
  const response = await fetch(path, options);
  const payload = await response.json();
  if (!response.ok) throw new Error(payload.error || 'Recording request failed');
  setRecordingStatus(payload);
}

async function startRecording() {
  try {
    await recordingRequest('/api/recording/start', {label: document.getElementById('record-label').value});
  } catch (e) {
    alert('Recorder: ' + e.message);
  }
}

async function stopRecording() {
  try {
    await recordingRequest('/api/recording/stop', {});
  } catch (e) {
    alert('Recorder: ' + e.message);
  }
}

function downloadRecording() {
  window.location = '/api/recording/download';
}

async function loadRecordingStatus() {
  try {
    const response = await fetch('/api/recording');
    setRecordingStatus(await response.json());
  } catch (e) {
    document.getElementById('record-status').innerText = 'Recorder status unavailable.';
  }
}

loadRecordingStatus();

async function loadMap() {
  try {
    const response = await fetch('/api/map');
    mapData = await response.json();
    const reference = mapData.reference;
    document.getElementById('map-status').innerText = reference.available
      ? reference.segment_count + ' mapped roads • OpenStreetMap'
      : 'Map unavailable';
    initialiseMap();
  } catch (e) {
    document.getElementById('map-status').innerText = 'Map unavailable';
  }
}

loadMap();

// Polling telemetry
setInterval(async () => {
  try {
    const res = await fetch('/api/state', {cache: 'no-store'});
    const data = await res.json();
    updateUI(data);
  } catch(e) {}
}, 50);

function updateUI(d) {
  document.getElementById('val-dist').innerText = d.dist_m.toFixed(1);
  
  const banner = document.getElementById('risk-banner');
  banner.innerText = d.risk_name;
  banner.className = 'risk-gauge risk-' + d.risk_name;
  
  const badge = document.getElementById('conn-badge');
  badge.innerText = d.source === 'BASYS3_UART' ? 'BASYS3 UART' : d.source;
  badge.style.color = d.source === 'BASYS3_UART' ? '#38bdf8' : '#10b981';
  document.getElementById('link-status').innerText = d.link_status || '';

  updateMapPosition(d);
}

function localToLatLng(xCm, yCm) {
  const reference = mapData.reference;
  const lat0 = Number(reference.origin_lat);
  const lon0 = Number(reference.origin_lon);
  const radiusM = 6371008.8;
  const lat = lat0 + (Number(yCm) / 100 / radiusM) * (180 / Math.PI);
  const lon = lon0 + (Number(xCm) / 100 / (radiusM * Math.cos(lat0 * Math.PI / 180))) * (180 / Math.PI);
  return [lat, lon];
}

function initialiseMap() {
  if (!window.L) {
    document.getElementById('map-status').innerText = 'Interactive map library unavailable; check internet access and reload.';
    return;
  }
  if (!mapData || !mapData.reference || !mapData.reference.available || map) return;
  const reference = mapData.reference;
  map = L.map('map', {zoomControl: true}).setView([Number(reference.origin_lat), Number(reference.origin_lon)], 17);
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
  }).addTo(map);
  for (const seg of reference.segments) {
    L.polyline([localToLatLng(seg.ax, seg.ay), localToLatLng(seg.bx, seg.by)], {
      color: '#38bdf8', weight: 4, opacity: 0.75,
    }).bindTooltip('OSM reference segment ' + seg.id + ' — not loaded into FPGA').addTo(map);
  }
  const demo = mapData.active.segments[0];
  L.polyline([localToLatLng(demo.ax, demo.ay), localToLatLng(demo.bx, demo.by)], {
    color: '#ef4444', weight: 6, opacity: 0.9,
  }).bindTooltip('Active FPGA synthetic road segment').addTo(map);
  [[500, '#f59e0b', '6 6'], [-500, '#f59e0b', '6 6'], [200, '#ef4444', '4 5'], [-200, '#ef4444', '4 5']].forEach(([y, color, dash]) => {
    L.polyline([localToLatLng(-2000, y), localToLatLng(2000, y)], {color:color, weight:2, dashArray:dash}).addTo(map);
  });
}

function updateMapPosition(d) {
  if (!map || !mapData || !mapData.reference.available) return;
  const point = localToLatLng(d.x_cm, d.y_cm);
  const color = d.risk === 3 ? '#ef4444' : (d.risk === 2 ? '#f59e0b' : (d.risk === 4 ? '#3b82f6' : '#10b981'));
  if (!collarMarker) collarMarker = L.circleMarker(point, {radius:9, color:'#ffffff', weight:2, fillColor:color, fillOpacity:1}).addTo(map);
  collarMarker.setLatLng(point).setStyle({fillColor: color});
  collarMarker.bindPopup('<strong>FPGA position</strong><br>Risk: ' + d.risk_name);
  trail.push(point);
  if (trail.length > 100) trail.shift();
  if (!trailLine) trailLine = L.polyline(trail, {color:'#a78bfa', weight:3, opacity:0.7}).addTo(map);
  else trailLine.setLatLngs(trail);
}

</script>
</body>
</html>
"""

# ---------------------------------------------------------------------------
# HTTP Handler
# ---------------------------------------------------------------------------

class DemoHandler(BaseHTTPRequestHandler):
    def _send_json(self, status: int, payload: dict) -> None:
        encoded = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(encoded)

    def do_GET(self):
        url = urlparse(self.path)
        if url.path == "/" or url.path == "/index.html":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML_PAGE.encode("utf-8"))
        elif url.path == "/api/state":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            with STATE_LOCK:
                payload = json.dumps(CURRENT_STATE)
            self.wfile.write(payload.encode("utf-8"))
        elif url.path == "/api/map":
            self._send_json(200, MAP_DATA)
        elif url.path == "/api/recording":
            self._send_json(200, RECORDER.status())
        elif url.path == "/api/recording/download":
            path = RECORDER.download_path()
            if path is None or not path.is_file():
                self._send_json(404, {"error": "no recording is available"})
                return
            data = path.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/csv; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Content-Disposition", f'attachment; filename="{path.name}"')
            self.end_headers()
            self.wfile.write(data)
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        url = urlparse(self.path)
        if url.path not in ("/api/recording/start", "/api/recording/stop"):
            self._send_json(404, {"error": "not found"})
            return

        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length > 1024:
                raise ValueError("request body is too large")
            raw = self.rfile.read(length) if length else b"{}"
            body = json.loads(raw.decode("utf-8"))
            if not isinstance(body, dict):
                raise ValueError("request body must be an object")

            if url.path == "/api/recording/start":
                result = RECORDER.start(body.get("label", "poc"))
            else:
                result = RECORDER.stop()
            self._send_json(200, result)
        except (OSError, RuntimeError, ValueError, json.JSONDecodeError) as exc:
            self._send_json(400, {"error": str(exc)})

    def log_message(self, format, *args):
        # Silence standard HTTP logs for clean terminal
        return


def get_local_ip() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def main():
    parser = argparse.ArgumentParser(description="BALAT Web UI Demo Server")
    parser.add_argument("--port", type=int, default=8888, help="Web port (default: 8888)")
    parser.add_argument(
        "--serial", metavar="PORT",
        help="Read live, framed telemetry from the Basys3 HerdSync USB-UART bridge.",
    )
    parser.add_argument("--baud", type=int, default=115200, help="UART baud rate (default: 115200)")
    parser.add_argument(
        "--simulate", action="store_true",
        help="Use the local synthetic trace rather than Basys3 UART telemetry (default without --serial).",
    )
    parser.add_argument(
        "--interval", type=float, default=0.25,
        help="Synthetic telemetry sample interval in seconds (default: 0.25)",
    )
    parser.add_argument(
        "--record-dir", type=Path, default=REPO / "build" / "poc_records",
        help="Directory for local CSV POC recordings (default: build/poc_records)",
    )
    parser.add_argument(
        "--map-csv", type=Path, default=REPO / "data" / "road_segments.csv",
        help="Optional local road-segment CSV for the reference map layer.",
    )
    parser.add_argument(
        "--map-manifest", type=Path, default=REPO / "data" / "road_manifest.json",
        help="Manifest paired with --map-csv for reference-layer provenance.",
    )
    args = parser.parse_args()

    if args.interval <= 0:
        parser.error("--interval must be positive")
    if args.baud <= 0:
        parser.error("--baud must be positive")
    if args.serial and args.simulate:
        parser.error("choose either --serial or --simulate")

    global RECORDER, MAP_DATA
    RECORDER = SessionRecorder(args.record_dir)
    MAP_DATA = load_reference_map(args.map_csv, args.map_manifest)

    if args.serial:
        telemetry_thread = threading.Thread(
            target=run_uart_telemetry, args=(args.serial, args.baud), daemon=True,
        )
        telemetry_thread.start()
        source_description = f"Basys3 USB-UART on {args.serial} at {args.baud} baud"
    else:
        telemetry_thread = threading.Thread(target=run_simulation, args=(args.interval,), daemon=True)
        telemetry_thread.start()
        source_description = "local synthetic trace (not FPGA telemetry)"

    local_ip = get_local_ip()
    server = ThreadingHTTPServer(("0.0.0.0", args.port), DemoHandler)

    print("=" * 60)
    print(" BALAT Live Web UI Demo Server Running")
    print("=" * 60)
    print(f" Laptop Browser: http://localhost:{args.port}")
    print(f" Phone Browser:  http://{local_ip}:{args.port}")
    print(f" Telemetry source: {source_description}")
    print(f" Active FPGA map: {ACTIVE_DEMO_MAP['name']} (one fixed segment)")
    print(f" Reference map: {'loaded' if MAP_DATA['reference']['available'] else 'unavailable'}")
    print(f" POC CSV records: {args.record_dir}")
    print("=" * 60)
    print(" Press Ctrl+C to stop.")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping server.")


if __name__ == "__main__":
    main()
