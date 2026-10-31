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

    def test_start_while_active_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            recorder = web_demo.SessionRecorder(Path(tmp))
            recorder.start("one")
            with self.assertRaises(RuntimeError):
                recorder.start("two")
            recorder.stop()


if __name__ == "__main__":
    unittest.main()
