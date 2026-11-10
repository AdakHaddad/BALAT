"""Tests for the dashboard's local POC CSV recorder."""

import csv
import json
import importlib.util
import tempfile
import threading
import unittest
from pathlib import Path
from http.server import ThreadingHTTPServer
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from unittest.mock import patch


REPO = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("balat_web_demo", REPO / "scripts" / "web_demo.py")
web_demo = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(web_demo)


class SessionRecorderTest(unittest.TestCase):
    def test_records_published_samples_and_transition_events(self):
        with tempfile.TemporaryDirectory() as tmp:
            recorder = web_demo.SessionRecorder(Path(tmp))

            started = recorder.start("Basys 3 / POC")
            self.assertTrue(started["active"])
            self.assertEqual(started["rows"], 0)
            self.assertTrue(started["filename"].startswith("balat_basys-3-poc_"))

            sample = {
                "source": "SIMULATION", "seq": 1, "x_cm": -300,
                "y_cm": 25, "dist_m": 3.0, "risk": 2,
                "risk_name": "CAUTION", "speed_kmh": 2.5,
                "approaching": True, "cue_active": False,
                "cooldown": False, "battery_mv": 3720,
            }
            recorder.record(sample)
            sample.update({"seq": 2, "risk": 3, "risk_name": "DANGER", "cue_active": True})
            recorder.record(sample)
            stopped = recorder.stop()

            self.assertFalse(stopped["active"])
            self.assertEqual(stopped["rows"], 2)
            self.assertIsNotNone(stopped["stopped_at_utc"])
            path = recorder.download_path()
            self.assertIsNotNone(path)

            with path.open(newline="", encoding="utf-8") as stream:
                rows = list(csv.DictReader(stream))
            self.assertEqual(len(rows), 2)
            self.assertEqual(rows[0]["event"], "risk:CAUTION")
            self.assertEqual(rows[1]["event"], "risk:DANGER;cue:on")
            self.assertEqual(rows[1]["cue_active"], "1")
            self.assertEqual(rows[1]["seq"], "2")

    def test_unexported_cue_state_is_blank_in_csv(self):
        with tempfile.TemporaryDirectory() as tmp:
            recorder = web_demo.SessionRecorder(Path(tmp))
            recorder.start("uart")
            recorder.record({"risk_name": "SAFE", "cue_active": None})
            recorder.stop()
            with recorder.download_path().open(newline="", encoding="utf-8") as stream:
                row = next(csv.DictReader(stream))
            self.assertEqual(row["cue_active"], "")

    def test_reference_map_keeps_manifest_provenance(self):
        loaded = web_demo.load_reference_map(
            REPO / "data" / "road_segments.csv",
            REPO / "data" / "road_manifest.json",
        )
        self.assertEqual(loaded["active"]["name"], "Basys3 synthetic demo map")
        self.assertTrue(loaded["reference"]["available"])
        self.assertGreater(loaded["reference"]["segment_count"], 0)
        self.assertIn("OpenStreetMap", loaded["reference"]["source"])
        self.assertIsInstance(loaded["reference"]["origin_lat"], float)
        self.assertIsInstance(loaded["reference"]["origin_lon"], float)
        self.assertEqual(loaded["reference"]["cos_lat_q14"], web_demo.ESP32_COS_LAT_Q14)

    def test_start_while_active_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            recorder = web_demo.SessionRecorder(Path(tmp))
            recorder.start("one")
            with self.assertRaises(RuntimeError):
                recorder.start("two")
            recorder.stop()


class SupabaseTelemetryWriterTest(unittest.TestCase):
    def test_row_maps_validated_state_to_database_shape(self):
        state = {
            "source": "SIMULATION", "seq": 7, "x_cm": -300, "y_cm": 25,
            "dist_m": 3.0, "risk": 2, "risk_name": "CAUTION",
            "speed_kmh": 2.5, "approaching": True, "cue_active": False,
            "cooldown": False, "battery_mv": 3720, "quality": 100,
            "fix_time_s": 12, "link_status": "ok",
        }
        row = web_demo.SupabaseTelemetryWriter.row_from_state(state, "kupang")
        self.assertEqual(row["site_id"], "kupang")
        self.assertEqual(row["seq"], 7)
        self.assertEqual(row["risk_name"], "CAUTION")
        self.assertEqual(row["cue_active"], False)
        self.assertIn("T", row["captured_at"])


class InteractiveMockMapTest(unittest.TestCase):
    def test_map_point_uses_gps_free_firmware_fix_command(self):
        self.assertEqual(web_demo.synthetic_fix_command(12040, -1768), b"FIX 12040 -1768\r\n")

    def test_map_point_motion_is_capped_and_stops_at_target(self):
        self.assertEqual(web_demo.step_towards_point((0, 0), (300, 400), 100), (60, 80))
        self.assertEqual(web_demo.step_towards_point((60, 80), (60, 80), 50), (60, 80))
        self.assertEqual(web_demo.step_towards_point((60, 80), (60, 80), 0), (60, 80))
        self.assertEqual(web_demo.step_towards_point((60, 80), (300, 400), 500), (300, 400))

    def test_geographic_projection_round_trips_local_points(self):
        points = [(0, 0), (-1500, 1000), (12_000, -5_500)]
        for x_cm, y_cm in points:
            lat_deg7 = web_demo.ESP32_ORIGIN_LAT_DEG7 + round(y_cm * 65_536 / 72_872)
            lon_deg7 = web_demo.ESP32_ORIGIN_LON_DEG7 + round(
                x_cm * 65_536 * 16_384 / (72_872 * web_demo.ESP32_COS_LAT_Q14)
            )
            projected = web_demo.esp32_geo_to_local_cm(lat_deg7, lon_deg7)
            self.assertLessEqual(abs(projected[0] - x_cm), 1)
            self.assertLessEqual(abs(projected[1] - y_cm), 1)

    def test_nearest_distance_uses_loaded_osm_segments(self):
        loaded = web_demo.load_reference_map(
            REPO / "data" / "road_segments.csv",
            REPO / "data" / "road_manifest.json",
        )
        segments = loaded["reference"]["segments"]
        segment = segments[0]
        mid_x = (segment["ax"] + segment["bx"]) // 2
        mid_y = (segment["ay"] + segment["by"]) // 2
        self.assertAlmostEqual(web_demo.nearest_road_distance_cm(mid_x, mid_y, segments), 0)
        self.assertGreater(
            web_demo.nearest_road_distance_cm(mid_x + 500_000, mid_y + 500_000, segments),
            0,
        )

    def test_point_endpoint_queues_projected_mock_location(self):
        server = ThreadingHTTPServer(("127.0.0.1", 0), web_demo.DemoHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        with patch.dict(web_demo.MOCK_CONTROL, {"available": True, "mode": "gps", "running": False}):
            thread.start()
            try:
                payload = json.dumps({
                    "lat_deg7": web_demo.ESP32_ORIGIN_LAT_DEG7,
                    "lon_deg7": web_demo.ESP32_ORIGIN_LON_DEG7,
                }).encode()
                request = Request(
                    f"http://127.0.0.1:{server.server_port}/api/mock/point",
                    data=payload,
                    headers={"Content-Type": "application/json"},
                )
                with urlopen(request) as response:
                    result = json.load(response)
                self.assertEqual((result["x_cm"], result["y_cm"]), (0, 0))
                self.assertTrue(result["manual_point"])
                self.assertEqual(web_demo.MOCK_CONTROL["point_pending"], (0, 0))
                self.assertTrue(web_demo.MOCK_CONTROL["reset_pending"])
            finally:
                server.shutdown()
                server.server_close()
                thread.join()

    def test_point_endpoint_rejects_location_outside_firmware_range(self):
        server = ThreadingHTTPServer(("127.0.0.1", 0), web_demo.DemoHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        with patch.dict(web_demo.MOCK_CONTROL, {"available": True, "mode": "gps", "running": False}):
            thread.start()
            try:
                payload = json.dumps({"lat_deg7": -337_000_000, "lon_deg7": 186_500_000}).encode()
                request = Request(
                    f"http://127.0.0.1:{server.server_port}/api/mock/point",
                    data=payload,
                    headers={"Content-Type": "application/json"},
                )
                with self.assertRaises(HTTPError) as error:
                    urlopen(request)
                self.assertEqual(error.exception.code, 400)
            finally:
                server.shutdown()
                server.server_close()
                thread.join()


class UartDashboardStateTest(unittest.TestCase):
    def test_esp32_invalid_log_exposes_firmware_fault(self):
        state = web_demo.esp32_log_to_state(
            "event=GNSS_STALE,rx_seq=11,fix_seq=10,risk=INVALID,"
            "fault=STALE,fix_valid=0,stale=1,map_valid=1,x_cm=12000,"
            "y_cm=-1700,dist2_cm2=123456"
        )

        self.assertIsNotNone(state)
        self.assertFalse(state["fix_valid"])
        self.assertEqual(state["risk_name"], "INVALID")
        self.assertEqual(state["fault"], "STALE")
        self.assertIn("invalid (STALE)", state["link_status"])

    def test_fpga_record_maps_to_live_dashboard_state(self):
        previous = {
            "source": "BASYS3_UART", "seq": 20, "x_cm": -1500,
            "y_cm": 100, "dist_m": 1.0,
        }
        record = {
            "seq": 21, "x_cm": -1500, "y_cm": 90, "risk": 2,
            "battery_mv": 3700, "quality": 100, "fix_time_s": 2,
        }

        state = web_demo.state_from_uart_record(record, previous)

        self.assertEqual(state["source"], "BASYS3_UART")
        self.assertEqual(state["risk_name"], "CAUTION")
        self.assertEqual(state["dist_m"], 0.9)
        self.assertEqual(state["speed_kmh"], 3.6)
        self.assertTrue(state["approaching"])
        self.assertIsNone(state["cue_active"])


if __name__ == "__main__":
    unittest.main()
