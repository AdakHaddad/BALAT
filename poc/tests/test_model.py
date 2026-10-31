from __future__ import annotations

import unittest
from dataclasses import replace

from poc.herdsync_dtn.model import (
    PRIORITY_ALERT,
    PRIORITY_ROUTINE,
    Node,
    Phone,
    Record,
    RecordRejected,
    seq_newer,
    validate_record,
)


def make_keys(*node_ids: int) -> dict[int, bytes]:
    return {node_id: f"test-key-{node_id}".encode() for node_id in node_ids}


def make_node(node_id: int, keys: dict[int, bytes], x_m: float = 0.0) -> Node:
    return Node(node_id, x_m, 0.0, keys[node_id], keys)


def make_record(
    origin_id: int,
    key: bytes,
    *,
    epoch: int = 1,
    seq: int = 1,
    fix_time_s: int = 10,
    x_cm: int = 0,
    y_cm: int = 0,
    priority: int = PRIORITY_ROUTINE,
) -> Record:
    return Record(
        origin_id=origin_id,
        epoch=epoch,
        seq=seq,
        fix_time_s=fix_time_s,
        x_cm=x_cm,
        y_cm=y_cm,
        priority=priority,
    ).sign(key)


class RecordTests(unittest.TestCase):
    def setUp(self) -> None:
        self.keys = make_keys(1, 2)
        self.record = make_record(1, self.keys[1])

    def test_sign_and_verify(self) -> None:
        self.assertTrue(self.record.verify(self.keys[1]))
        self.assertFalse(self.record.verify(self.keys[2]))
        self.assertEqual(len(self.record.payload()), 28)
        self.assertEqual(len(self.record.auth_tag), 16)

    def test_tampering_is_rejected(self) -> None:
        tampered = replace(self.record, x_cm=123)
        with self.assertRaises(RecordRejected) as context:
            validate_record(tampered, 10, self.keys[1])
        self.assertEqual(context.exception.reason, "auth")

    def test_seq_newer_handles_wraparound(self) -> None:
        self.assertTrue(seq_newer(1, 0xFFFFFFFF))
        self.assertTrue(seq_newer(0xFFFFFFFF, 0xFFFFFFFE))
        self.assertFalse(seq_newer(0xFFFFFFFE, 0xFFFFFFFF))
        self.assertFalse(seq_newer(7, 7))

    def test_epoch_wins_over_sequence(self) -> None:
        old = make_record(1, self.keys[1], epoch=1, seq=100)
        new = make_record(1, self.keys[1], epoch=2, seq=1)
        self.assertTrue(new.newer_than(old))
        self.assertFalse(old.newer_than(new))


class NodeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.keys = make_keys(1, 2, 3)
        self.node1 = make_node(1, self.keys)
        self.node2 = make_node(2, self.keys, 20.0)
        self.node3 = make_node(3, self.keys, 40.0)

    def test_accepts_newer_and_rejects_duplicate_and_old(self) -> None:
        first = self.node1.make_record(10)
        self.assertTrue(self.node2.ingest(first, 10).accepted)

        duplicate = self.node2.ingest(first, 10)
        self.assertTrue(duplicate.duplicate)
        self.assertFalse(duplicate.accepted)

        second = self.node1.make_record(20)
        self.assertTrue(self.node2.ingest(second, 20).accepted)

        old = self.node2.ingest(first, 20)
        self.assertFalse(old.accepted)
        self.assertEqual(old.reason, "old")

    def test_rejects_stale_and_future_records(self) -> None:
        stale = make_record(1, self.keys[1], fix_time_s=0)
        result = self.node2.ingest(stale, 1000)
        self.assertFalse(result.accepted)
        self.assertEqual(result.reason, "stale")

        future = make_record(1, self.keys[1], fix_time_s=2000)
        result = self.node2.ingest(future, 1000)
        self.assertFalse(result.accepted)
        self.assertEqual(result.reason, "future")

    def test_ttl_limits_forwarding(self) -> None:
        record = self.node1.make_record(10)
        self.node2.ingest(record, 10, ttl=1)
        self.node2.sync_with(self.node3, 10)
        self.assertNotIn(1, self.node3.records)

        self.node2.ingest(record, 10, ttl=2)
        self.node2.sync_with(self.node3, 10)
        self.assertIn(1, self.node3.records)

    def test_priority_orders_alert_before_routine(self) -> None:
        alert = self.node1.make_record(10, priority=PRIORITY_ALERT)
        routine = self.node2.make_record(10, priority=PRIORITY_ROUTINE)
        self.node3.ingest(alert, 10)
        self.node3.ingest(routine, 10)

        pending = self.node3.pending_for({})
        self.assertEqual(pending[0].record.origin_id, 1)
        self.assertEqual(pending[0].record.priority, PRIORITY_ALERT)

    def test_sync_exchanges_both_directions(self) -> None:
        self.node1.make_record(10)
        self.node2.make_record(10)
        result = self.node1.sync_with(self.node2, 10)
        self.assertIn(1, self.node2.records)
        self.assertIn(2, self.node1.records)
        self.assertGreaterEqual(result.sent, 1)
        self.assertGreaterEqual(result.received, 1)

    def test_version_vector_and_pending(self) -> None:
        first = self.node1.make_record(10)
        self.node2.ingest(first, 10)
        self.assertEqual(self.node1.latest_vv()[1], (first.epoch, first.seq))
        self.assertEqual(self.node2.pending_for(self.node1.latest_vv()), [])

        second = self.node1.make_record(20)
        pending = self.node1.pending_for(self.node2.latest_vv())
        self.assertEqual(len(pending), 1)
        self.assertEqual(pending[0].record.record_id, second.record_id)


class PhoneTests(unittest.TestCase):
    def setUp(self) -> None:
        self.keys = make_keys(1, 2)
        self.node1 = make_node(1, self.keys)
        self.node2 = make_node(2, self.keys, 20.0)
        self.phone = Phone(self.keys)

    def test_phone_accepts_stale_but_marks_it(self) -> None:
        record = make_record(1, self.keys[1], fix_time_s=0)
        result = self.phone.ingest(record, 1000, allow_stale=True)
        self.assertTrue(result.accepted)
        self.assertTrue(self.phone.records[1].is_stale(1000))

    def test_phone_pulls_and_pushes(self) -> None:
        self.node1.make_record(10)
        self.phone.sync_with_node(self.node1, 10)
        self.assertIn(1, self.phone.records)
        self.assertIn(1, self.phone.direct_origins)

        self.phone.sync_with_node(self.node2, 10, push=True)
        self.assertIn(1, self.node2.records)

    def test_phone_rejects_forged_record(self) -> None:
        forged = make_record(1, self.keys[2])
        result = self.phone.ingest(forged, 10)
        self.assertFalse(result.accepted)
        self.assertEqual(result.reason, "auth")


if __name__ == "__main__":
    unittest.main()
