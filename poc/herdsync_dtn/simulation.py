"""Deterministic BLE contact and store-carry-forward simulator for the POC."""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import Callable, Mapping

from .model import (
    DEFAULT_STALE_AFTER_S,
    PRIORITY_ALERT,
    Node,
    Phone,
    Record,
    SyncResult,
)


@dataclass
class Contact:
    time_s: float
    a: int
    b: int
    result: SyncResult


@dataclass
class PhoneContact:
    time_s: float
    node_id: int
    push: bool
    result: SyncResult


class Simulation:
    """A discrete-time world with range-limited BLE contacts."""

    def __init__(
        self,
        name: str,
        nodes: Mapping[int, Node],
        keys: Mapping[int, bytes],
        *,
        ble_range_m: float = 30.0,
        contact_period_s: float = 2.0,
        sync_budget: int = 8,
        step_s: float = 1.0,
        seed: int = 7,
        stale_after_s: float = DEFAULT_STALE_AFTER_S,
        body_loss_prob: float = 0.0,
        body_range_factor: float = 0.6,
    ) -> None:
        self.name = name
        self.nodes = dict(nodes)
        self.keys = keys
        self.ble_range_m = float(ble_range_m)
        self.contact_period_s = float(contact_period_s)
        self.sync_budget = int(sync_budget)
        self.step_s = float(step_s)
        self.seed = int(seed)
        self.stale_after_s = float(stale_after_s)
        self.body_loss_prob = float(body_loss_prob)
        self.body_range_factor = float(body_range_factor)
        self.phone = Phone(keys, stale_after_s=stale_after_s)
        self.time_s = 0.0
        self.last_contact: dict[tuple[int, int], float] = {}
        self.contacts: list[Contact] = []
        self.phone_contacts: list[PhoneContact] = []
        self.generated: list[Record] = []
        self.generated_by_id: dict[tuple[int, int, int], Record] = {}
        self.emergency_ids: list[tuple[int, int, int]] = []
        self.rng = random.Random(seed)

    def set_position(self, node_id: int, x_m: float, y_m: float) -> None:
        self.nodes[node_id].set_position(x_m, y_m)

    def phone_visit(self, node_id: int, *, push: bool = False) -> SyncResult:
        node = self.nodes[node_id]
        result = self.phone.sync_with_node(node, self.time_s, push=push)
        self.phone_contacts.append(PhoneContact(self.time_s, node_id, push, result))
        return result

    def make_emergency(
        self,
        node_id: int,
        *,
        risk: int = 2,
        priority: int = PRIORITY_ALERT,
    ) -> Record:
        record = self.nodes[node_id].make_record(self.time_s, priority=priority, risk=risk)
        self._note_generated(record)
        return record

    def _note_generated(self, record: Record) -> None:
        self.generated.append(record)
        self.generated_by_id[record.record_id] = record
        if record.priority == PRIORITY_ALERT:
            self.emergency_ids.append(record.record_id)

    def step(self) -> None:
        self.time_s += self.step_s
        for node in self.nodes.values():
            while math.isfinite(node.next_fix_s) and self.time_s + 1e-9 >= node.next_fix_s:
                record = node.make_record(self.time_s)
                self._note_generated(record)
                node.next_fix_s += node.fix_interval_s
        self._run_contacts()

    def run(self, steps: int, on_step: Callable[["Simulation", int], None] | None = None) -> None:
        for index in range(steps):
            if on_step is not None:
                on_step(self, index)
            self.step()

    def _run_contacts(self) -> None:
        node_ids = sorted(self.nodes)
        for index, a_id in enumerate(node_ids):
            for b_id in node_ids[index + 1 :]:
                if not self._in_range(a_id, b_id):
                    continue
                pair = (a_id, b_id)
                last = self.last_contact.get(pair, -1e9)
                if self.time_s - last < self.contact_period_s:
                    continue
                self.last_contact[pair] = self.time_s
                result = self.nodes[a_id].sync_with(
                    self.nodes[b_id], self.time_s, budget=self.sync_budget
                )
                self.contacts.append(Contact(self.time_s, a_id, b_id, result))

    def _in_range(self, a_id: int, b_id: int) -> bool:
        a = self.nodes[a_id]
        b = self.nodes[b_id]
        distance = math.hypot(a.x_m - b.x_m, a.y_m - b.y_m)
        if distance > self.ble_range_m:
            return False
        if self.body_loss_prob > 0.0 and self.rng.random() < self.body_loss_prob:
            return distance <= self.ble_range_m * self.body_range_factor
        return True

    def report(self) -> dict:
        latest_coverage = 0
        node_reports: dict[str, dict] = {}
        for node_id, node in sorted(self.nodes.items()):
            latest = node.records.get(node_id)
            phone_record = self.phone.records.get(node_id)
            covered = bool(
                latest is not None
                and phone_record is not None
                and latest.record_id == phone_record.record_id
            )
            latest_coverage += int(covered)
            node_reports[str(node_id)] = {
                "position_m": [node.x_m, node.y_m],
                "known_origins": sorted(node.records),
                "latest": latest.to_dict() if latest is not None else None,
                "latest_record_id": list(latest.record_id) if latest is not None else None,
                "latest_ttl": node.record_ttls.get(node_id),
                "stats": node.stats.to_dict(),
            }

        phone_records = []
        ages = []
        stale_records = 0
        for origin, record in sorted(self.phone.records.items()):
            age = self.time_s - record.fix_time_s
            ages.append(age)
            stale = age > self.stale_after_s
            stale_records += int(stale)
            phone_records.append(
                {
                    **record.to_dict(),
                    "age_s": age,
                    "stale": stale,
                    "received_at_s": self.phone.received_at.get(record.record_id),
                }
            )

        emergency = []
        for record_id in self.emergency_ids:
            record = self.generated_by_id[record_id]
            received_at = self.phone.received_at.get(record_id)
            emergency.append(
                {
                    "record_id": list(record_id),
                    "origin_id": record.origin_id,
                    "generated_at_s": record.fix_time_s,
                    "delivered_to_phone": received_at is not None,
                    "latency_s": (received_at - record.fix_time_s) if received_at is not None else None,
                    "still_in_phone_table": (
                        self.phone.records.get(record.origin_id) is not None
                        and self.phone.records[record.origin_id].record_id == record_id
                    ),
                }
            )

        node_stats = [node.stats for node in self.nodes.values()]
        records_sent = sum(stats.sent for stats in node_stats) + self.phone.stats.sent
        records_received = sum(stats.received for stats in node_stats) + self.phone.stats.received
        duplicates = sum(stats.duplicates for stats in node_stats) + self.phone.stats.duplicates
        rejected = sum(stats.rejected for stats in node_stats) + self.phone.stats.rejected
        bytes_sent = sum(stats.bytes_sent for stats in node_stats) + self.phone.stats.bytes_sent
        bytes_received = (
            sum(stats.bytes_received for stats in node_stats)
            + self.phone.stats.bytes_received
        )
        multi_hop_origins = sorted(set(self.phone.records) - self.phone.direct_origins)
        node_count = len(self.nodes)

        metrics = {
            "elapsed_s": self.time_s,
            "node_count": node_count,
            "generated_records": len(self.generated),
            "unique_generated_records": len(self.generated_by_id),
            "phone_records": len(self.phone.records),
            "latest_coverage": latest_coverage,
            "latest_coverage_pct": (100.0 * latest_coverage / node_count) if node_count else 0.0,
            "origin_coverage_pct": (100.0 * len(self.phone.records) / node_count) if node_count else 0.0,
            "freshness_p50_s": percentile(ages, 0.50),
            "freshness_p95_s": percentile(ages, 0.95),
            "freshness_max_s": max(ages) if ages else 0.0,
            "stale_phone_records": stale_records,
            "direct_phone_origins": sorted(self.phone.direct_origins),
            "multi_hop_origins": multi_hop_origins,
            "multi_hop_count": len(multi_hop_origins),
            "node_contact_count": len(self.contacts),
            "phone_contact_count": len(self.phone_contacts),
            "records_sent": records_sent,
            "records_received": records_received,
            "duplicates": duplicates,
            "rejected": rejected,
            "bytes_sent": bytes_sent,
            "bytes_received": bytes_received,
            "emergency": emergency,
        }

        return {
            "scenario": self.name,
            "config": {
                "ble_range_m": self.ble_range_m,
                "contact_period_s": self.contact_period_s,
                "sync_budget": self.sync_budget,
                "step_s": self.step_s,
                "seed": self.seed,
                "stale_after_s": self.stale_after_s,
                "body_loss_prob": self.body_loss_prob,
                "body_range_factor": self.body_range_factor,
            },
            "metrics": metrics,
            "phone": {
                "record_count": len(self.phone.records),
                "direct_origins": sorted(self.phone.direct_origins),
                "records": phone_records,
                "stats": self.phone.stats.to_dict(),
            },
            "nodes": node_reports,
        }


def percentile(values: list[float], fraction: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    index = int(round((len(ordered) - 1) * fraction))
    index = max(0, min(len(ordered) - 1, index))
    return ordered[index]
