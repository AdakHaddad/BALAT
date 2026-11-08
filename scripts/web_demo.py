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
import queue
import re
import socket
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlparse
from urllib.request import Request, urlopen

REPO = Path(__file__).resolve().parent.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from poc.herdsync_dtn.uart_frame import (  # noqa: E402
    TYPE_RECORD,
    FrameParser,
    decode_record_payload,
)

RISK_NAMES = {0: "INVALID", 1: "SAFE", 2: "CAUTION", 3: "DANGER", 4: "COOLDOWN"}
RISK_CODES = {name: code for code, name in RISK_NAMES.items()}
ESP32_ORIGIN_LAT_DEG7 = -338250000
ESP32_ORIGIN_LON_DEG7 = 186500000
ESP32_COS_LAT_Q14 = 13611

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
MOCK_LOCK = threading.Lock()
MOCK_CONTROL = {
    "available": False,
    "mode": "gps",
    "running": False,
    "index": 0,
    "total": 0,
    "interval": 0.1,
    "reset_pending": False,
    "stop_pending": False,
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


class SupabaseTelemetryWriter:
    """Asynchronously append validated bridge samples to Supabase."""

    def __init__(self, base_url: str, service_role_key: str, site_id: str = "default"):
        self._endpoint = f"{base_url.rstrip('/')}/rest/v1/telemetry_events"
        self._service_role_key = service_role_key
        self._site_id = site_id
        self._samples: queue.Queue[dict | None] = queue.Queue(maxsize=256)
        self._worker = threading.Thread(target=self._run, name="supabase-telemetry", daemon=True)
        self._worker.start()

    @classmethod
    def from_environment(cls) -> "SupabaseTelemetryWriter | None":
        base_url = os.environ.get("BALAT_SUPABASE_URL", "").strip()
        service_role_key = os.environ.get("BALAT_SUPABASE_SERVICE_ROLE_KEY", "").strip()
        if not base_url and not service_role_key:
            return None
        if not base_url or not service_role_key:
            raise RuntimeError(
                "BALAT_SUPABASE_URL and BALAT_SUPABASE_SERVICE_ROLE_KEY must be set together"
            )
        return cls(base_url, service_role_key, os.environ.get("BALAT_SUPABASE_SITE_ID", "default"))

    @staticmethod
    def row_from_state(state: dict, site_id: str) -> dict:
        return {
            "captured_at": datetime.now(timezone.utc).isoformat(),
            "site_id": site_id,
            "source": str(state.get("source", "UNKNOWN")),
            "seq": int(state.get("seq", 0)),
            "x_cm": int(state.get("x_cm", 0)),
            "y_cm": int(state.get("y_cm", 0)),
            "dist_m": float(state.get("dist_m", 0.0)),
            "risk": int(state.get("risk", 0)),
            "risk_name": str(state.get("risk_name", "INVALID")),
            "speed_kmh": float(state.get("speed_kmh", 0.0)),
            "approaching": bool(state.get("approaching", False)),
            "cue_active": state.get("cue_active"),
            "cooldown": bool(state.get("cooldown", False)),
            "battery_mv": int(state.get("battery_mv", 0)),
            "quality": int(state.get("quality", 0)),
            "fix_time_s": int(state.get("fix_time_s", 0)),
            "link_status": str(state.get("link_status", "")),
        }

    def submit(self, state: dict) -> None:
        try:
            self._samples.put_nowait(self.row_from_state(state, self._site_id))
        except queue.Full:
            print("Supabase telemetry queue full; dropping sample", file=sys.stderr)

    def _run(self) -> None:
        while True:
            sample = self._samples.get()
            if sample is None:
                return
            request = Request(
                self._endpoint,
                data=json.dumps(sample).encode("utf-8"),
                headers={
                    "apikey": self._service_role_key,
                    "Authorization": f"Bearer {self._service_role_key}",
                    "Content-Type": "application/json",
                    "Prefer": "return=minimal",
                },
                method="POST",
            )
            try:
                with urlopen(request, timeout=10):
                    pass
            except (HTTPError, URLError, TimeoutError) as exc:
                print(f"Supabase telemetry write failed: {exc}", file=sys.stderr)


SUPABASE_WRITER: SupabaseTelemetryWriter | None = None


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
    if SUPABASE_WRITER is not None:
        SUPABASE_WRITER.submit(snapshot)


def set_transport_status(source: str, message: str) -> None:
    """Update connection UI state without creating a telemetry CSV row."""
    with STATE_LOCK:
        CURRENT_STATE["source"] = source
        CURRENT_STATE["link_status"] = message


def mock_gps_status() -> dict:
    with MOCK_LOCK:
        control = dict(MOCK_CONTROL)
    return {
        "available": control["available"],
        "mode": control["mode"],
        "running": control["running"],
        "index": control["index"],
        "total": control["total"],
        "interval": control["interval"],
    }


def invalidate_esp32_state(message: str) -> None:
    """Fail closed in the browser when ESP32 decision logs stop arriving."""
    publish_state({
        "risk": 0,
        "risk_name": "INVALID",
        "approaching": False,
        "cue_active": False,
        "cooldown": False,
        "fix_valid": False,
        "quality": 0,
        "source": "ESP32_UART",
        "link_status": message,
    })


def invalidate_basys3_state(message: str) -> None:
    publish_state({
        "risk": 0, "risk_name": "INVALID", "approaching": False,
        "cue_active": None, "cooldown": False, "fix_valid": False,
        "map_valid": True, "quality": 0, "source": "BASYS3_NMEA_UART",
        "link_status": message,
    })


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
    if (previous.get("source") in ("BASYS3_UART", "BASYS3_NMEA_UART")
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


def run_basys3_nmea_telemetry(port: str, baud: int, interval: float = 0.1) -> None:
    """Send dashboard replay NMEA to the FPGA and read its HerdSync records."""
    try:
        import serial
    except ImportError:
        set_transport_status("BASYS3_NMEA_UART", "pyserial missing: python3 -m pip install pyserial")
        return

    trace = _load_esp32_mock_trace()
    with MOCK_LOCK:
        MOCK_CONTROL.update({"available": False, "mode": "mock", "running": False,
                             "index": 0, "total": len(trace), "interval": interval,
                             "reset_pending": False, "stop_pending": False})
    while True:
        try:
            serial_port = serial.Serial(port, baud, timeout=0.05, write_timeout=1)
        except serial.SerialException as exc:
            set_transport_status("BASYS3_NMEA_UART", f"FPGA UART unavailable: {exc}; retrying")
            invalidate_basys3_state(f"FPGA UART unavailable: {exc}; dashboard state forced INVALID.")
            time.sleep(1.0)
            continue

        parser = FrameParser()
        with MOCK_LOCK:
            MOCK_CONTROL["available"] = True
        set_transport_status("BASYS3_NMEA_UART", f"Connected to {port}; dashboard mock NMEA input enabled.")
        next_fix = time.monotonic()
        last_record_at = time.monotonic()
        stale_published = False
        previous = {"source": "BASYS3_NMEA_UART", "seq": 0}
        try:
            while True:
                chunk = serial_port.read(512)
                if chunk:
                    for frame in parser.feed(chunk):
                        if frame.frame_type != TYPE_RECORD:
                            continue
                        try:
                            record = decode_record_payload(frame.payload)
                        except ValueError:
                            continue
                        with STATE_LOCK:
                            previous = dict(CURRENT_STATE)
                        update = state_from_uart_record(record, previous)
                        update["source"] = "BASYS3_NMEA_UART"
                        update["fix_valid"] = int(record["risk"]) != 0
                        # Existing FPGA UART records omit map-valid and cue-active.
                        update["map_valid"] = None
                        update["link_status"] = "Dashboard NMEA → FPGA parser/risk pipeline → UART telemetry."
                        publish_state(update)
                        last_record_at = time.monotonic()
                        stale_published = False

                with MOCK_LOCK:
                    running = bool(MOCK_CONTROL["running"])
                    trace_index = int(MOCK_CONTROL["index"])
                    fix_interval = float(MOCK_CONTROL["interval"])
                    reset_pending = bool(MOCK_CONTROL["reset_pending"])
                    MOCK_CONTROL["reset_pending"] = False
                    MOCK_CONTROL["stop_pending"] = False
                if reset_pending:
                    trace_index = 0
                    with MOCK_LOCK:
                        MOCK_CONTROL["index"] = 0
                    next_fix = time.monotonic()
                if running and trace_index < len(trace) and time.monotonic() >= next_fix:
                    x_cm, y_cm = trace[trace_index]
                    for command in nmea_commands_for_local_fix(x_cm, y_cm, datetime.now(timezone.utc)):
                        # FPGA parser consumes raw NMEA, unlike the ESP32 console protocol.
                        raw_sentence = command.removeprefix("NMEA ")
                        serial_port.write(raw_sentence.encode("ascii"))
                    with MOCK_LOCK:
                        MOCK_CONTROL["index"] = trace_index + 1
                        if MOCK_CONTROL["index"] >= MOCK_CONTROL["total"]:
                            MOCK_CONTROL["running"] = False
                    next_fix = time.monotonic() + fix_interval
                if time.monotonic() - last_record_at > 3.0 and not stale_published:
                    invalidate_basys3_state("No FPGA telemetry for 3 seconds; displayed state forced INVALID.")
                    stale_published = True
        except serial.SerialException as exc:
            set_transport_status("BASYS3_NMEA_UART", f"FPGA UART read/write failed: {exc}; reconnecting")
            invalidate_basys3_state(f"FPGA serial fault: {exc}; dashboard state forced INVALID.")
        finally:
            with MOCK_LOCK:
                MOCK_CONTROL["available"] = False
            serial_port.close()
        time.sleep(1.0)


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


def esp32_log_to_state(line: str) -> dict | None:
    """Convert one ESP32 key/value CSV decision log into the dashboard schema."""
    if not line.startswith("event="):
        return None
    fields = {}
    for item in line.strip().split(","):
        key, separator, value = item.partition("=")
        if separator:
            fields[key] = value
    risk_name = fields.get("risk", "INVALID")
    if risk_name not in RISK_CODES or "x_cm" not in fields or "dist2_cm2" not in fields:
        return None
    try:
        x_cm = int(fields["x_cm"])
        y_cm = int(fields["y_cm"])
        distance_cm = math.sqrt(max(0, int(fields["dist2_cm2"])))
        speed_cm_s = math.sqrt(max(0, int(fields.get("speed2_cm2_s2", "0"))))
        fix_valid = fields.get("fix_valid", "0") == "1"
        map_valid = fields.get("map_valid", "0") == "1"
        stale = fields.get("stale", "0") == "1"
        seq = int(fields.get("fix_seq", fields.get("rx_seq", "0")))
        cue_active = fields.get("cue_active", "0") == "1" and fix_valid and map_valid and not stale
    except (TypeError, ValueError, OverflowError):
        return None
    if not fix_valid or not map_valid or stale:
        risk_name = "INVALID"
    return {
        "x_cm": x_cm,
        "y_cm": y_cm,
        "dist_m": round(distance_cm / 100.0, 2),
        "risk": RISK_CODES[risk_name],
        "risk_name": risk_name,
        "speed_kmh": round(speed_cm_s * 0.036, 2),
        "approaching": fields.get("approaching", "0") == "1",
        "cue_active": cue_active,
        "cooldown": fields.get("cooldown", "0") == "1",
        "fix_valid": fix_valid,
        "map_valid": map_valid,
        "battery_mv": 0,
        "quality": 0,
        "seq": seq,
        "fix_time_s": 0,
        "source": "ESP32_UART",
        "link_status": f"ESP32 bench log · {fields.get('event', 'decision')} · fix {'valid' if fix_valid else 'invalid'} · cues remain hardware gated.",
    }


def _nmea_sentence(body: str) -> str:
    checksum = 0
    for char in body:
        checksum ^= ord(char)
    return f"${body}*{checksum:02X}\r\n"


def _format_nmea_coordinate(deg7: int, latitude: bool) -> tuple[str, str]:
    hemisphere = ("N" if deg7 >= 0 else "S") if latitude else ("E" if deg7 >= 0 else "W")
    absolute = abs(deg7)
    degrees, remainder = divmod(absolute, 10_000_000)
    minutes = remainder * 60 / 10_000_000
    degree_width = 2 if latitude else 3
    return f"{degrees:0{degree_width}d}{minutes:09.6f}", hemisphere


def nmea_commands_for_local_fix(x_cm: int, y_cm: int, at: datetime) -> tuple[str, str]:
    """Make checksummed GGA/RMC commands for one local-coordinate replay fix."""
    lat_deg7 = ESP32_ORIGIN_LAT_DEG7 + round(y_cm * 65_536 / 72_872)
    lon_deg7 = ESP32_ORIGIN_LON_DEG7 + round(
        x_cm * 65_536 * 16_384 / (72_872 * ESP32_COS_LAT_Q14)
    )
    lat, ns = _format_nmea_coordinate(lat_deg7, True)
    lon, ew = _format_nmea_coordinate(lon_deg7, False)
    clock = at.strftime("%H%M%S") + f".{at.microsecond // 10000:02d}"
    date = at.strftime("%d%m%y")
    gga = _nmea_sentence(f"GPGGA,{clock},{lat},{ns},{lon},{ew},1,08,1.0,0.0,M,0.0,M,,")
    rmc = _nmea_sentence(f"GPRMC,{clock},A,{lat},{ns},{lon},{ew},1.9,0.0,{date},,,A")
    return f"NMEA {gga}", f"NMEA {rmc}"


def _load_esp32_mock_trace() -> list[tuple[int, int]]:
    path = REPO / "data" / "demo_trace.csv"
    with path.open(newline="", encoding="utf-8") as stream:
        return [(int(row["x_cm"]), int(row["y_cm"])) for row in csv.DictReader(stream)]


def run_esp32_telemetry(port: str, baud: int, mock_gps: bool = False, interval: float = 0.1) -> None:
    """Bridge ESP32 logs and dashboard-controlled mock NMEA through firmware parsing."""
    try:
        import serial
    except ImportError:
        set_transport_status("ESP32_UART", "pyserial missing: python3 -m pip install pyserial")
        return

    trace = _load_esp32_mock_trace()
    with MOCK_LOCK:
        MOCK_CONTROL.update({
            "available": False,
            "mode": "mock" if mock_gps else "gps",
            "running": bool(mock_gps),
            "index": 0,
            "total": len(trace),
            "interval": interval,
            "reset_pending": False,
            "stop_pending": False,
        })
    while True:
        try:
            serial_port = serial.Serial(port, baud, timeout=0.05, write_timeout=1)
        except serial.SerialException as exc:
            set_transport_status("ESP32_UART", f"UART unavailable: {exc}; retrying")
            invalidate_esp32_state(f"ESP32 UART unavailable: {exc}; displayed state forced INVALID.")
            time.sleep(1.0)
            continue

        with MOCK_LOCK:
            MOCK_CONTROL["available"] = True
        mode = "dashboard-controlled mock NMEA or GNSS"
        set_transport_status("ESP32_UART", f"Connected to {port}; {mode}.")
        next_fix = time.monotonic()
        device_mock_mode = False
        was_running = False
        last_decision_at = time.monotonic()
        stale_published = False
        input_buffer = bytearray()
        try:
            while True:
                chunk = serial_port.read(512)
                if chunk:
                    input_buffer.extend(chunk)
                    while b"\n" in input_buffer:
                        raw_line, _, rest = input_buffer.partition(b"\n")
                        input_buffer = bytearray(rest)
                        line = raw_line.decode("ascii", errors="ignore").strip()
                        update = esp32_log_to_state(line)
                        if update is not None:
                            publish_state(update)
                            last_decision_at = time.monotonic()
                            stale_published = False

                with MOCK_LOCK:
                    running = bool(MOCK_CONTROL["running"])
                    trace_index = int(MOCK_CONTROL["index"])
                    fix_interval = float(MOCK_CONTROL["interval"])
                    reset_pending = bool(MOCK_CONTROL["reset_pending"])
                    stop_pending = bool(MOCK_CONTROL["stop_pending"])
                    MOCK_CONTROL["reset_pending"] = False
                    MOCK_CONTROL["stop_pending"] = False

                if reset_pending:
                    if not device_mock_mode:
                        serial_port.write(b"MOCK START\r\n")
                        device_mock_mode = True
                    serial_port.write(b"MOCK RESET\r\n")
                    next_fix = time.monotonic()
                if stop_pending:
                    serial_port.write(b"MOCK STOP\r\n")
                    device_mock_mode = False
                elif running and not device_mock_mode:
                    serial_port.write(b"MOCK START\r\n")
                    device_mock_mode = True
                    next_fix = time.monotonic()
                elif not running and was_running and device_mock_mode:
                    serial_port.write(b"MOCK PAUSE\r\n")

                if not stop_pending and running and trace_index < len(trace) and time.monotonic() >= next_fix:
                    x_cm, y_cm = trace[trace_index]
                    at = datetime.now(timezone.utc)
                    for command in nmea_commands_for_local_fix(x_cm, y_cm, at):
                        serial_port.write(command.encode("ascii"))
                    with MOCK_LOCK:
                        MOCK_CONTROL["index"] = trace_index + 1
                        complete = MOCK_CONTROL["index"] >= MOCK_CONTROL["total"]
                        if complete:
                            MOCK_CONTROL["running"] = False
                    next_fix = time.monotonic() + fix_interval
                    if complete:
                        serial_port.write(b"MOCK PAUSE\r\n")
                        set_transport_status(
                            "ESP32_UART",
                            "Mock NMEA trace complete; receiving board decisions. No GPS receiver data was used.",
                        )
                elif not stop_pending and running and trace_index >= len(trace):
                    with MOCK_LOCK:
                        MOCK_CONTROL["running"] = False
                    serial_port.write(b"MOCK PAUSE\r\n")
                was_running = running
                if not stale_published and time.monotonic() - last_decision_at > 3.0:
                    invalidate_esp32_state("No ESP32 decision log for 3 seconds; displayed state forced INVALID.")
                    stale_published = True
        except serial.SerialException as exc:
            set_transport_status("ESP32_UART", f"UART read/write failed: {exc}; reconnecting")
            invalidate_esp32_state(f"ESP32 serial fault: {exc}; displayed state forced INVALID.")
        finally:
            with MOCK_LOCK:
                MOCK_CONTROL["available"] = False
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
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
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
                state = dict(CURRENT_STATE)
            if state.get("source") in ("ESP32_UART", "BASYS3_NMEA_UART"):
                state["mock_gps"] = mock_gps_status()
            payload = json.dumps(state)
            self.wfile.write(payload.encode("utf-8"))
        elif url.path == "/api/mock":
            self._send_json(200, mock_gps_status())
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
        if url.path not in ("/api/recording/start", "/api/recording/stop", "/api/mock/control"):
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

            if url.path == "/api/mock/control":
                action = body.get("action")
                if action not in ("start", "pause", "reset", "stop", "speed"):
                    raise ValueError("action must be start, pause, reset, stop, or speed")
                requested_interval = body.get("interval")
                with MOCK_LOCK:
                    if not MOCK_CONTROL["available"]:
                        raise RuntimeError("ESP32 serial bridge is not connected")
                    if requested_interval is not None:
                        try:
                            requested_interval = float(requested_interval)
                        except (TypeError, ValueError) as exc:
                            raise ValueError("interval must be between 0.05 and 2 seconds") from exc
                        if not 0.05 <= requested_interval <= 2.0:
                            raise ValueError("interval must be between 0.05 and 2 seconds")
                        MOCK_CONTROL["interval"] = requested_interval
                    if action == "start":
                        MOCK_CONTROL["mode"] = "mock"
                        if MOCK_CONTROL["index"] >= MOCK_CONTROL["total"]:
                            MOCK_CONTROL["index"] = 0
                            MOCK_CONTROL["reset_pending"] = True
                        MOCK_CONTROL["running"] = True
                    elif action == "pause":
                        MOCK_CONTROL["mode"] = "mock"
                        MOCK_CONTROL["running"] = False
                    elif action == "reset":
                        MOCK_CONTROL["mode"] = "mock"
                        MOCK_CONTROL["index"] = 0
                        MOCK_CONTROL["running"] = False
                        MOCK_CONTROL["reset_pending"] = True
                    elif action == "stop":
                        MOCK_CONTROL["mode"] = "gps"
                        MOCK_CONTROL["running"] = False
                        MOCK_CONTROL["index"] = 0
                        MOCK_CONTROL["reset_pending"] = False
                        MOCK_CONTROL["stop_pending"] = True
                result = mock_gps_status()
            elif url.path == "/api/recording/start":
                result = RECORDER.start(body.get("label", "poc"))
            else:
                result = RECORDER.stop()
            self._send_json(200, result)
        except (OSError, RuntimeError, ValueError, json.JSONDecodeError) as exc:
            self._send_json(400, {"error": str(exc)})

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Content-Length", "0")
        self.end_headers()

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
    parser.add_argument(
        "--esp32-serial", metavar="PORT",
        help="Read ESP32 key/value decision logs and expose them through the dashboard API.",
    )
    parser.add_argument(
        "--basys3-nmea-serial", metavar="PORT",
        help="Stream dashboard mock NMEA to the Basys3 and read its FPGA telemetry records.",
    )
    parser.add_argument(
        "--mock-gps", action="store_true",
        help="With --esp32-serial, stream a synthetic checksummed NMEA trace through the ESP32 firmware parser.",
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
    if sum(bool(value) for value in (args.serial, args.esp32_serial, args.basys3_nmea_serial, args.simulate)) > 1:
        parser.error("choose one telemetry source: --serial, --esp32-serial, --basys3-nmea-serial, or --simulate")
    if args.mock_gps and not args.esp32_serial:
        parser.error("--mock-gps currently requires --esp32-serial; FPGA replay is controlled in the dashboard")

    global RECORDER, MAP_DATA, SUPABASE_WRITER
    RECORDER = SessionRecorder(args.record_dir)
    MAP_DATA = load_reference_map(args.map_csv, args.map_manifest)
    try:
        SUPABASE_WRITER = SupabaseTelemetryWriter.from_environment()
    except RuntimeError as exc:
        parser.error(str(exc))

    if args.esp32_serial:
        telemetry_thread = threading.Thread(
            target=run_esp32_telemetry,
            args=(args.esp32_serial, args.baud, args.mock_gps, args.interval),
            daemon=True,
        )
        telemetry_thread.start()
        suffix = " with mock NMEA replay" if args.mock_gps else ""
        source_description = f"ESP32 USB serial on {args.esp32_serial} at {args.baud} baud{suffix}"
    elif args.basys3_nmea_serial:
        telemetry_thread = threading.Thread(
            target=run_basys3_nmea_telemetry,
            args=(args.basys3_nmea_serial, args.baud, args.interval),
            daemon=True,
        )
        telemetry_thread.start()
        source_description = f"Basys3 NMEA demo on {args.basys3_nmea_serial} at {args.baud} baud"
    elif args.serial:
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
    print(f" Supabase telemetry: {'enabled' if SUPABASE_WRITER else 'disabled'}")
    print("=" * 60)
    print(" Press Ctrl+C to stop.")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping server.")


if __name__ == "__main__":
    main()
