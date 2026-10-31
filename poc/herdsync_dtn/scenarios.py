"""Deterministic scenarios for the HerdSync-DTN proof of concept."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable

from .model import Node
from .simulation import Simulation


@dataclass
class ScenarioResult:
    name: str
    report: dict
    simulation: Simulation


def _make_keys(node_ids: Iterable[int]) -> dict[int, bytes]:
    return {
        node_id: f"balat-poc-herd-key-{node_id:04d}".encode()
        for node_id in node_ids
    }


def _make_nodes(
    node_ids: Iterable[int],
    positions: dict[int, tuple[float, float]],
    keys: dict[int, bytes],
    **kwargs,
) -> dict[int, Node]:
    return {
        node_id: Node(
            node_id,
            positions[node_id][0],
            positions[node_id][1],
            keys[node_id],
            keys,
            **kwargs,
        )
        for node_id in node_ids
    }


def _freeze_generation(sim: Simulation) -> None:
    for node in sim.nodes.values():
        node.fix_interval_s = float("inf")
        node.next_fix_s = float("inf")


def two_collar(seed: int = 7) -> ScenarioResult:
    node_ids = (1, 2)
    keys = _make_keys(node_ids)
    positions = {1: (0.0, 0.0), 2: (20.0, 0.0)}
    nodes = _make_nodes(node_ids, positions, keys)
    sim = Simulation(
        "two_collar",
        nodes,
        keys,
        ble_range_m=30.0,
        contact_period_s=1.0,
        sync_budget=8,
        seed=seed,
    )
    sim.run(60)
    _freeze_generation(sim)
    sim.run(10)
    sim.phone_visit(1)
    return ScenarioResult("two_collar", sim.report(), sim)


def multi_hop(seed: int = 7) -> ScenarioResult:
    node_ids = tuple(range(1, 7))
    keys = _make_keys(node_ids)
    positions = {node_id: (20.0 * (node_id - 1), 0.0) for node_id in node_ids}
    nodes = _make_nodes(node_ids, positions, keys)
    sim = Simulation(
        "multi_hop",
        nodes,
        keys,
        ble_range_m=30.0,
        contact_period_s=2.0,
        sync_budget=8,
        seed=seed,
    )
    sim.run(300)
    _freeze_generation(sim)
    sim.run(60)
    sim.phone_visit(6)
    return ScenarioResult("multi_hop", sim.report(), sim)


def partition_rejoin(seed: int = 7) -> ScenarioResult:
    node_ids = tuple(range(1, 7))
    keys = _make_keys(node_ids)
    positions = {
        1: (0.0, 0.0),
        2: (20.0, 0.0),
        3: (40.0, 0.0),
        4: (1000.0, 0.0),
        5: (1020.0, 0.0),
        6: (1040.0, 0.0),
    }
    nodes = _make_nodes(node_ids, positions, keys)
    sim = Simulation(
        "partition_rejoin",
        nodes,
        keys,
        ble_range_m=30.0,
        contact_period_s=2.0,
        sync_budget=8,
        seed=seed,
    )
    sim.run(300)
    sim.set_position(4, 60.0, 0.0)
    sim.set_position(5, 80.0, 0.0)
    sim.set_position(6, 100.0, 0.0)
    sim.run(300)
    _freeze_generation(sim)
    sim.run(60)
    sim.phone_visit(1)
    return ScenarioResult("partition_rejoin", sim.report(), sim)


def phone_mule(seed: int = 7) -> ScenarioResult:
    node_ids = tuple(range(1, 6))
    keys = _make_keys(node_ids)
    positions = {node_id: (100.0 * (node_id - 1), 0.0) for node_id in node_ids}
    nodes = _make_nodes(node_ids, positions, keys)
    sim = Simulation(
        "phone_mule",
        nodes,
        keys,
        ble_range_m=20.0,
        contact_period_s=2.0,
        sync_budget=8,
        seed=seed,
    )

    sim.run(100)
    _freeze_generation(sim)
    for node_id in node_ids:
        sim.phone_visit(node_id)
    sim.phone_visit(1, push=True)
    return ScenarioResult("phone_mule", sim.report(), sim)


def emergency(seed: int = 7) -> ScenarioResult:
    node_ids = tuple(range(1, 7))
    keys = _make_keys(node_ids)
    positions = {node_id: (20.0 * (node_id - 1), 0.0) for node_id in node_ids}
    nodes = _make_nodes(node_ids, positions, keys)
    sim = Simulation(
        "emergency",
        nodes,
        keys,
        ble_range_m=30.0,
        contact_period_s=2.0,
        sync_budget=8,
        seed=seed,
    )
    sim.run(30)
    sim.make_emergency(6, risk=2)
    _freeze_generation(sim)
    sim.run(90)
    sim.phone_visit(1)
    return ScenarioResult("emergency", sim.report(), sim)


SCENARIOS: dict[str, Callable[[int], ScenarioResult]] = {
    "two_collar": two_collar,
    "multi_hop": multi_hop,
    "partition_rejoin": partition_rejoin,
    "phone_mule": phone_mule,
    "emergency": emergency,
}


def run_scenario(name: str, seed: int = 7) -> ScenarioResult:
    if name == "all":
        raise ValueError("use run_all for the full scenario set")
    return SCENARIOS[name](seed)


def run_all(seed: int = 7) -> list[ScenarioResult]:
    return [scenario(seed) for scenario in SCENARIOS.values()]
