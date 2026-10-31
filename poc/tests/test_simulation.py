from __future__ import annotations

import json
import unittest

from poc.herdsync_dtn.scenarios import SCENARIOS, run_all, run_scenario


class ScenarioTests(unittest.TestCase):
    def test_two_collar_phone_gets_both(self) -> None:
        result = run_scenario("two_collar")
        metrics = result.report["metrics"]
        self.assertEqual(metrics["latest_coverage"], 2)
        self.assertEqual(metrics["phone_records"], 2)
        self.assertEqual(metrics["multi_hop_count"], 1)
        self.assertEqual(metrics["stale_phone_records"], 0)

    def test_multi_hop_reaches_one_phone_contact(self) -> None:
        result = run_scenario("multi_hop")
        metrics = result.report["metrics"]
        self.assertEqual(metrics["latest_coverage"], 6)
        self.assertEqual(metrics["phone_records"], 6)
        self.assertEqual(metrics["multi_hop_count"], 5)
        self.assertGreater(metrics["node_contact_count"], 0)
        self.assertLessEqual(metrics["freshness_p95_s"], 120.0)

    def test_partition_rejoins_and_converges(self) -> None:
        result = run_scenario("partition_rejoin")
        metrics = result.report["metrics"]
        self.assertEqual(metrics["latest_coverage"], 6)
        self.assertEqual(metrics["phone_records"], 6)
        self.assertEqual(metrics["multi_hop_count"], 5)

    def test_phone_mule_collects_from_each_collar(self) -> None:
        result = run_scenario("phone_mule")
        metrics = result.report["metrics"]
        self.assertEqual(metrics["latest_coverage"], 5)
        self.assertEqual(metrics["phone_records"], 5)
        self.assertEqual(metrics["multi_hop_count"], 0)
        self.assertEqual(metrics["node_contact_count"], 0)
        self.assertEqual(len(result.simulation.nodes[1].records), 5)

    def test_emergency_record_reaches_phone(self) -> None:
        result = run_scenario("emergency")
        metrics = result.report["metrics"]
        self.assertEqual(metrics["latest_coverage"], 6)
        self.assertEqual(len(metrics["emergency"]), 1)
        event = metrics["emergency"][0]
        self.assertTrue(event["delivered_to_phone"])
        self.assertTrue(event["still_in_phone_table"])
        self.assertIsNotNone(event["latency_s"])
        self.assertLessEqual(event["latency_s"], 120.0)

    def test_all_scenarios_are_deterministic_and_json_serializable(self) -> None:
        first = run_all(seed=7)
        second = run_all(seed=7)
        self.assertEqual([item.report["metrics"] for item in first], [item.report["metrics"] for item in second])
        for item in first:
            json.dumps(item.report)

    def test_scenario_registry(self) -> None:
        self.assertEqual(
            set(SCENARIOS),
            {"two_collar", "multi_hop", "partition_rejoin", "phone_mule", "emergency"},
        )


if __name__ == "__main__":
    unittest.main()
