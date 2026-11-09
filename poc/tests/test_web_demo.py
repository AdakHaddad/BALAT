"""Tests for the dashboard's local POC CSV recorder."""

import csv
import importlib.util
import tempfile
import unittest
from pathlib import Path


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


class UartDashboardStateTest(unittest.TestCase):
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
