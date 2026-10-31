"""Command-line runner for the HerdSync-DTN proof of concept."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .scenarios import SCENARIOS, ScenarioResult, run_all, run_scenario


def _summary_line(result: ScenarioResult) -> str:
    metrics = result.report["metrics"]
    return (
        f"{result.name:18s} "
        f"{metrics['latest_coverage']}/{metrics['node_count']} "
        f"{metrics['phone_records']:>5d} "
        f"{metrics['freshness_p95_s']:>7.1f} "
        f"{metrics['multi_hop_count']:>9d} "
        f"{metrics['node_contact_count']:>8d} "
        f"{metrics['duplicates']:>4d} "
        f"{metrics['rejected']:>4d}"
    )


def _print_table(results: list[ScenarioResult]) -> None:
    print(
        f"{'scenario':18s} "
        f"{'cover':>5s} "
        f"{'phone':>5s} "
        f"{'p95 age':>7s} "
        f"{'multi':>9s} "
        f"{'contacts':>8s} "
        f"{'dup':>4s} "
        f"{'rej':>4s}"
    )
    for result in results:
        print(_summary_line(result))


def _print_detail(result: ScenarioResult) -> None:
    report = result.report
    metrics = report["metrics"]
    print(f"\nScenario: {report['scenario']}")
    print(
        "  latest coverage: "
        f"{metrics['latest_coverage']}/{metrics['node_count']} "
        f"({metrics['latest_coverage_pct']:.1f}%)"
    )
    print(f"  phone records: {metrics['phone_records']}")
    print(
        "  freshness p50/p95/max: "
        f"{metrics['freshness_p50_s']:.1f} / "
        f"{metrics['freshness_p95_s']:.1f} / "
        f"{metrics['freshness_max_s']:.1f} s"
    )
    print(f"  multi-hop origins: {metrics['multi_hop_count']}")
    print(f"  contacts: {metrics['node_contact_count']} node, {metrics['phone_contact_count']} phone")
    print(
        "  records sent/received: "
        f"{metrics['records_sent']} / {metrics['records_received']}"
    )
    print(
        "  bytes sent/received: "
        f"{metrics['bytes_sent']} / {metrics['bytes_received']}"
    )
    print(f"  duplicates rejected: {metrics['duplicates']}")
    print(f"  records rejected: {metrics['rejected']}")

    for event in metrics["emergency"]:
        print(
            "  emergency: "
            f"origin={event['origin_id']} "
            f"delivered={event['delivered_to_phone']} "
            f"latency={event['latency_s']} s"
        )

    print("\n  phone table:")
    print(
        f"  {'origin':>6s} {'seq':>6s} {'age_s':>7s} "
        f"{'x_m':>8s} {'y_m':>8s} {'stale':>6s}"
    )
    for record in report["phone"]["records"]:
        print(
            f"  {record['origin_id']:>6d} {record['seq']:>6d} "
            f"{record['age_s']:>7.1f} "
            f"{record['x_cm'] / 100.0:>8.1f} "
            f"{record['y_cm'] / 100.0:>8.1f} "
            f"{str(record['stale']):>6s}"
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run the HerdSync-DTN software proof of concept."
    )
    parser.add_argument(
        "--scenario",
        choices=["all", *SCENARIOS.keys()],
        default="all",
        help="Scenario to run (default: all).",
    )
    parser.add_argument("--seed", type=int, default=7, help="Deterministic random seed.")
    parser.add_argument(
        "--json",
        metavar="PATH",
        help="Write the full report as JSON to PATH.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print the full report for each scenario.",
    )
    args = parser.parse_args(argv)

    print("HerdSync-DTN POC — software simulation, not BLE hardware.")
    print("Safety path is not modified; this is a post-v0.1 communication study.\n")

    if args.scenario == "all":
        results = run_all(args.seed)
    else:
        results = [run_scenario(args.scenario, args.seed)]

    _print_table(results)
    for result in results:
        _print_detail(result)
        if args.verbose:
            print(json.dumps(result.report, indent=2))

    if args.json:
        path = Path(args.json)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = [result.report for result in results]
        path.write_text(json.dumps(payload, indent=2) + "\n")
        print(f"\nWrote {path}")

    return 0
