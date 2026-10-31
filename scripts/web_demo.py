#!/usr/bin/env python3
"""BALAT Live Web UI Demo Server.

Streams collar risk assessment, distance calculations, and cue activation
to any web browser on laptop or phone.

Usage:
    python3 scripts/web_demo.py [--port 8888] [--interval 0.25]

Open in browser:
    Laptop: http://localhost:8888
    Phone:  http://<laptop-ip>:8888
"""

from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import json
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

# Current live telemetry state (thread-safe)
STATE_LOCK = threading.Lock()
CURRENT_STATE = {
    "x_cm": -1500,
    "y_cm": 1000,
    "dist_m": 15.0,
    "risk": 1,          # 0=INVALID, 1=SAFE, 2=CAUTION, 3=DANGER, 4=COOLDOWN
    "risk_name": "SAFE",
    "speed_kmh": 3.6,
    "approaching": True,
    "cue_active": False,
    "cooldown": False,
    "battery_mv": 3720,
    "seq": 0,
    "source": "SIMULATION",
}

RECORD_FIELDS = (
    "captured_at_utc", "elapsed_ms", "event", "source", "seq", "x_cm",
    "y_cm", "dist_m", "risk", "risk_name", "speed_kmh", "approaching",
    "cue_active", "cooldown", "battery_mv",
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
        self._last_cue_active = False

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
            self._last_cue_active = False
            return self._status_locked()

    def record(self, state: dict) -> None:
        """Capture one producer update, if a session is active."""
        with self._lock:
            if self._file is None:
                return

            risk_name = str(state.get("risk_name", "UNKNOWN"))
            cue_active = bool(state.get("cue_active", False))
            events = []
            if self._last_risk != risk_name:
                events.append(f"risk:{risk_name}")
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
                "cue_active": int(cue_active),
                "approaching": int(bool(state.get("approaching", False))),
                "cooldown": int(bool(state.get("cooldown", False))),
            })
            self._writer.writerow(row)
            self._file.flush()
            self._row_count += 1
            self._last_risk = risk_name
            self._last_cue_active = cue_active

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


def publish_state(update: dict) -> None:
    """Publish a telemetry sample and offer it to the local recorder."""
    with STATE_LOCK:
        CURRENT_STATE.update(update)
        snapshot = dict(CURRENT_STATE)
    RECORDER.record(snapshot)

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

    RISK_NAMES = {0: "INVALID", 1: "SAFE", 2: "CAUTION", 3: "DANGER", 4: "COOLDOWN"}

    while True:
        for x_cm, y_cm in points:
            seq += 1
            # Road at x=0, y in [-2000, 2000]
            dist_cm = abs(x_cm)
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
                "approaching": (x_cm < 0),
                "cue_active": cue_active,
                "cooldown": (risk == 4),
                "seq": seq,
                "speed_kmh": round(1.8 + (seq % 5) * 0.2, 1),
            })

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
  .header { display: flex; justify-content: space-between; align-items: center; padding-bottom: 14px; border-bottom: 1px solid var(--border); margin-bottom: 16px; }
  .title { font-size: 20px; font-weight: 700; letter-spacing: 0.5px; }
  .badge { background: #1e293b; color: var(--safe); padding: 4px 10px; border-radius: 9999px; font-size: 12px; font-weight: 600; text-transform: uppercase; border: 1px solid var(--border); }
  .grid { display: grid; grid-template-columns: 1fr; gap: 14px; max-width: 900px; margin: 0 auto; }
  @media(min-width: 768px) { .grid { grid-template-columns: 1.2fr 1fr; } }
  
  .card { background: var(--card); border: 1px solid var(--border); border-radius: 12px; padding: 16px; box-shadow: 0 4px 20px rgba(0,0,0,0.3); }
  .card-title { font-size: 13px; text-transform: uppercase; color: var(--subtext); letter-spacing: 1px; margin-bottom: 10px; font-weight: 600; }
  
  /* Risk Banner */
  .risk-gauge { border-radius: 10px; padding: 18px; text-align: center; font-size: 28px; font-weight: 800; letter-spacing: 2px; transition: all 0.3s ease; }
  .risk-SAFE { background: rgba(16, 185, 129, 0.15); color: var(--safe); border: 2px solid var(--safe); }
  .risk-CAUTION { background: rgba(245, 158, 11, 0.15); color: var(--caution); border: 2px solid var(--caution); }
  .risk-DANGER { background: rgba(239, 68, 68, 0.25); color: var(--danger); border: 2px solid var(--danger); animation: pulse 0.8s infinite alternate; }
  .risk-COOLDOWN { background: rgba(59, 130, 246, 0.15); color: var(--cooldown); border: 2px solid var(--cooldown); }
  @keyframes pulse { from { box-shadow: 0 0 10px rgba(239, 68, 68, 0.3); } to { box-shadow: 0 0 25px rgba(239, 68, 68, 0.8); } }

  /* Metrics grid */
  .metrics { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-top: 12px; }
  .metric-box { background: #0f172a; padding: 12px; border-radius: 8px; border: 1px solid var(--border); }
  .metric-val { font-size: 22px; font-weight: 700; margin-top: 2px; }
  .metric-unit { font-size: 12px; color: var(--subtext); margin-left: 3px; font-weight: 400; }
  
  /* MCI Cue Box */
  .cue-box { display: flex; align-items: center; justify-content: space-between; padding: 14px; border-radius: 8px; margin-top: 12px; background: #0f172a; border: 1px solid var(--border); }
  .cue-light { width: 18px; height: 18px; border-radius: 50%; background: #334155; transition: all 0.2s; }
  .cue-active { background: #ef4444; box-shadow: 0 0 16px #ef4444; animation: flash 0.3s infinite; }
  @keyframes flash { 0%, 100% { opacity: 1; } 50% { opacity: 0.3; } }

  /* Map Canvas */
  canvas { width: 100%; height: 320px; background: #0a0e17; border-radius: 8px; display: block; border: 1px solid #1e293b; }
  
  .transport-note { margin-top: 10px; padding: 10px; color: var(--subtext); background: #0f172a; border: 1px solid var(--border); border-radius: 8px; font-size: 11px; line-height: 1.45; }
  .recording { margin-top: 12px; padding: 12px; border-radius: 8px; background: #0f172a; border: 1px solid var(--border); }
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
    <div class="title">BALAT &middot; Basys3 POC Dashboard</div>
    <div style="font-size: 11px; color: var(--subtext); margin-top: 2px;">Synthetic-trace observability &middot; display/record only</div>
  </div>
  <div id="conn-badge" class="badge">SYNTHETIC FEED</div>
</div>

<div class="grid">
  <!-- Map View -->
  <div class="card">
    <div class="card-title">Live Spatial Radar &amp; Road Proximity</div>
    <canvas id="radar" width="500" height="400"></canvas>
    <div style="font-size: 11px; color: var(--subtext); margin-top: 8px; display: flex; justify-content: space-between;">
      <span>&VerticalSeparator; Road Corridor (x=0)</span>
      <span style="color: var(--caution);">&bull; Caution (5m)</span>
      <span style="color: var(--danger);">&bull; Danger (2m)</span>
    </div>
  </div>

  <!-- Telemetry & Risk HUD -->
  <div class="card">
    <div class="card-title">Decision Pipeline State</div>
    
    <div id="risk-banner" class="risk-gauge risk-SAFE">SAFE</div>
    
    <div class="metrics">
      <div class="metric-box">
        <div style="font-size:11px; color:var(--subtext);">ROAD DISTANCE</div>
        <div class="metric-val"><span id="val-dist">15.0</span><span class="metric-unit">m</span></div>
      </div>
      <div class="metric-box">
        <div style="font-size:11px; color:var(--subtext);">ESTIMATED SPEED</div>
        <div class="metric-val"><span id="val-speed">3.6</span><span class="metric-unit">km/h</span></div>
      </div>
      <div class="metric-box">
        <div style="font-size:11px; color:var(--subtext);">POSITION (X, Y)</div>
        <div class="metric-val" style="font-size:16px; margin-top:6px;"><span id="val-pos">-15.0, 10.0</span><span class="metric-unit">m</span></div>
      </div>
      <div class="metric-box">
        <div style="font-size:11px; color:var(--subtext);">BATTERY</div>
        <div class="metric-val"><span id="val-batt">3.72</span><span class="metric-unit">V</span></div>
      </div>
    </div>

    <!-- MCI Actuator Output Indicator -->
    <div class="cue-box">
      <div>
        <div style="font-weight: 700; font-size: 14px;">Cue logic signal (Pmod JA1)</div>
        <div style="font-size: 11px; color: var(--subtext);">Observation only; external protected driver required</div>
      </div>
      <div id="cue-led" class="cue-light"></div>
    </div>

    <div class="recording">
      <div style="font-weight:700; font-size:14px;">POC session recorder</div>
      <div style="font-size:11px; color:var(--subtext); margin-top:3px;">Local CSV capture only; it cannot command the FPGA or cue output.</div>
      <div class="recording-row">
        <input id="record-label" maxlength="40" value="basys3-poc" aria-label="POC session label">
        <button id="record-start" class="record-start" onclick="startRecording()">Start</button>
        <button id="record-stop" class="record-stop" onclick="stopRecording()" disabled>Stop</button>
      </div>
      <button id="record-download" class="record-download" onclick="downloadRecording()" disabled>Download CSV</button>
      <div id="record-status" class="record-status">Not recording.</div>
    </div>

    <div class="transport-note">
      <strong style="color:var(--text);">Transport status:</strong> Bluetooth is not part of this Basys3 POC.
      This dashboard uses its synthetic telemetry source and records locally to CSV. The separate USB-UART bridge is
      bench-only and has no path to the cue output.
    </div>
  </div>
</div>

<script>
const canvas = document.getElementById('radar');
const ctx = canvas.getContext('2d');
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

// Polling telemetry
setInterval(async () => {
  try {
    const res = await fetch('/api/state');
    const data = await res.json();
    updateUI(data);
  } catch(e) {}
}, 200);

function updateUI(d) {
  document.getElementById('val-dist').innerText = d.dist_m.toFixed(1);
  document.getElementById('val-speed').innerText = d.speed_kmh.toFixed(1);
  document.getElementById('val-pos').innerText = (d.x_cm/100).toFixed(1) + ', ' + (d.y_cm/100).toFixed(1);
  document.getElementById('val-batt').innerText = (d.battery_mv/1000).toFixed(2);
  
  const banner = document.getElementById('risk-banner');
  banner.innerText = d.risk_name;
  banner.className = 'risk-gauge risk-' + d.risk_name;
  
  const cueLed = document.getElementById('cue-led');
  if (d.cue_active) cueLed.className = 'cue-light cue-active';
  else cueLed.className = 'cue-light';

  // Update map trail
  trail.push({x: d.x_cm, y: d.y_cm});
  if (trail.length > 50) trail.shift();
  drawMap(d);
}

function drawMap(d) {
  const w = canvas.width;
  const h = canvas.height;
  ctx.clearRect(0, 0, w, h);

  // Center coordinate: map x [-20m, 20m] to [0, w], y [-15m, 15m] to [0, h]
  const scale = w / 4000.0; // cm to px
  const cx = w / 2;
  const cy = h / 2;

  function toPx(x_cm, y_cm) {
    return { x: cx + x_cm * scale, y: cy - y_cm * scale };
  }

  // Draw Grid
  ctx.strokeStyle = '#152033';
  ctx.lineWidth = 1;
  for (let x = -2000; x <= 2000; x += 500) {
    const p1 = toPx(x, -2000); const p2 = toPx(x, 2000);
    ctx.beginPath(); ctx.moveTo(p1.x, 0); ctx.lineTo(p1.x, h); ctx.stroke();
  }

  // Draw Caution Buffer (5m)
  const c1 = toPx(-500, -2000); const c2 = toPx(500, 2000);
  ctx.fillStyle = 'rgba(245, 158, 11, 0.1)';
  ctx.fillRect(c1.x, 0, c2.x - c1.x, h);

  // Draw Danger Buffer (2m)
  const d1 = toPx(-200, -2000); const d2 = toPx(200, 2000);
  ctx.fillStyle = 'rgba(239, 68, 68, 0.18)';
  ctx.fillRect(d1.x, 0, d2.x - d1.x, h);

  // Draw Road (x=0)
  const r1 = toPx(0, -2000); const r2 = toPx(0, 2000);
  ctx.strokeStyle = '#94a3b8';
  ctx.lineWidth = 4;
  ctx.beginPath(); ctx.moveTo(r1.x, 0); ctx.lineTo(r1.x, h); ctx.stroke();

  // Draw Trail
  if (trail.length > 1) {
    ctx.strokeStyle = 'rgba(59, 130, 246, 0.4)';
    ctx.lineWidth = 2;
    ctx.beginPath();
    const p0 = toPx(trail[0].x, trail[0].y);
    ctx.moveTo(p0.x, p0.y);
    for (let i = 1; i < trail.length; i++) {
      const p = toPx(trail[i].x, trail[i].y);
      ctx.lineTo(p.x, p.y);
    }
    ctx.stroke();
  }

  // Draw Cow Position
  const pos = toPx(d.x_cm, d.y_cm);
  ctx.fillStyle = d.cue_active ? '#ef4444' : (d.risk === 2 ? '#f59e0b' : '#10b981');
  ctx.beginPath();
  ctx.arc(pos.x, pos.y, 8, 0, Math.PI * 2);
  ctx.fill();
  ctx.strokeStyle = '#ffffff';
  ctx.lineWidth = 2;
  ctx.stroke();

  // Cow label
  ctx.fillStyle = '#ffffff';
  ctx.font = 'bold 12px sans-serif';
  ctx.fillText('🐄 Collar #1', pos.x + 12, pos.y + 4);
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
        "--interval", type=float, default=0.25,
        help="Synthetic telemetry sample interval in seconds (default: 0.25)",
    )
    parser.add_argument(
        "--record-dir", type=Path, default=REPO / "build" / "poc_records",
        help="Directory for local CSV POC recordings (default: build/poc_records)",
    )
    args = parser.parse_args()

    if args.interval <= 0:
        parser.error("--interval must be positive")

    global RECORDER
    RECORDER = SessionRecorder(args.record_dir)

    # Start simulation generator in background
    sim_thread = threading.Thread(target=run_simulation, args=(args.interval,), daemon=True)
    sim_thread.start()

    local_ip = get_local_ip()
    server = ThreadingHTTPServer(("0.0.0.0", args.port), DemoHandler)

    print("=" * 60)
    print(" BALAT Live Web UI Demo Server Running")
    print("=" * 60)
    print(f" Laptop Browser: http://localhost:{args.port}")
    print(f" Phone Browser:  http://{local_ip}:{args.port}")
    print(f" POC CSV records: {args.record_dir}")
    print("=" * 60)
    print(" Press Ctrl+C to stop.")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping server.")


if __name__ == "__main__":
    main()
