"""Reference model for the HerdSync-DTN proof of concept.

This is a software-only model. It is not RTL, firmware, or a safety component.
It does not authorize changes to the BALAT v0.1 safety path.
"""

from __future__ import annotations

import hashlib
import hmac
import struct
from collections import deque
from dataclasses import dataclass, replace
from typing import Mapping

SCHEMA_VERSION = 1
PRIORITY_ROUTINE = 0
PRIORITY_ALERT = 1
DEFAULT_TTL = 6
DEFAULT_STALE_AFTER_S = 300
DEFAULT_MAX_FUTURE_SKEW_S = 60
AUTH_TAG_BYTES = 8
AUTH_TAG_HEX_LEN = AUTH_TAG_BYTES * 2
RECORD_PAYLOAD_BYTES = 28
RECORD_WIRE_BYTES = RECORD_PAYLOAD_BYTES + AUTH_TAG_BYTES
SEQ_BITS = 32
SEQ_MASK = (1 << SEQ_BITS) - 1
SEQ_HALF = 1 << (SEQ_BITS - 1)


class RecordRejected(Exception):
    """Raised when a record fails schema, freshness, or authentication checks."""

    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(reason)


@dataclass(frozen=True)
class Record:
    """Signed location record owned by one collar."""

    origin_id: int
    epoch: int
    seq: int
    fix_time_s: int
    x_cm: int
    y_cm: int
    quality: int = 100
    battery_mv: int = 3700
    risk: int = 0
    priority: int = PRIORITY_ROUTINE
    auth_tag: str = ""

    def payload(self) -> bytes:
        return struct.pack(
            ">BBHIIIiiBHB",
            SCHEMA_VERSION,
            self.priority,
            self.epoch,
            self.origin_id,
            self.seq,
            self.fix_time_s,
            self.x_cm,
            self.y_cm,
            self.quality,
            self.battery_mv,
            self.risk,
        )

    def sign(self, key: bytes) -> "Record":
        tag = hmac.new(key, self.payload(), hashlib.sha256).hexdigest()[:AUTH_TAG_HEX_LEN]
        return replace(self, auth_tag=tag)

    def verify(self, key: bytes) -> bool:
        if len(self.auth_tag) != AUTH_TAG_HEX_LEN:
            return False
        expected = hmac.new(key, self.payload(), hashlib.sha256).hexdigest()[:AUTH_TAG_HEX_LEN]
        return hmac.compare_digest(self.auth_tag, expected)

    @property
    def record_id(self) -> tuple[int, int, int]:
        return (self.origin_id, self.epoch, self.seq)

    def age_s(self, now_s: float) -> float:
        return now_s - self.fix_time_s

    def is_stale(self, now_s: float, stale_after_s: float = DEFAULT_STALE_AFTER_S) -> bool:
        return self.age_s(now_s) > stale_after_s

    def newer_than(self, other: "Record") -> bool:
        if self.origin_id != other.origin_id:
            raise ValueError("records from different origins")
        if self.epoch != other.epoch:
            return self.epoch > other.epoch
        return seq_newer(self.seq, other.seq)

    def to_dict(self) -> dict:
        return {
            "origin_id": self.origin_id,
            "epoch": self.epoch,
            "seq": self.seq,
            "fix_time_s": self.fix_time_s,
            "x_cm": self.x_cm,
            "y_cm": self.y_cm,
            "quality": self.quality,
            "battery_mv": self.battery_mv,
            "risk": self.risk,
            "priority": self.priority,
            "record_id": list(self.record_id),
            "auth_tag": self.auth_tag,
        }


@dataclass(frozen=True)
class Envelope:
    """A record plus its remaining forwarding budget."""

    record: Record
    ttl: int


@dataclass(frozen=True)
class IngestResult:
    accepted: bool
    reason: str
    duplicate: bool = False


@dataclass
class SyncResult:
    sent: int = 0
    received: int = 0
    duplicates: int = 0
    rejected: int = 0
    bytes_sent: int = 0
    bytes_received: int = 0

    def to_dict(self) -> dict:
        return {
            "sent": self.sent,
            "received": self.received,
            "duplicates": self.duplicates,
            "rejected": self.rejected,
            "bytes_sent": self.bytes_sent,
            "bytes_received": self.bytes_received,
        }


@dataclass
class NodeStats:
    syncs: int = 0
    generated: int = 0
    accepted: int = 0
    duplicates: int = 0
    rejected: int = 0
    sent: int = 0
    received: int = 0
    bytes_sent: int = 0
    bytes_received: int = 0

    def to_dict(self) -> dict:
        return {
            "syncs": self.syncs,
            "generated": self.generated,
            "accepted": self.accepted,
            "duplicates": self.duplicates,
            "rejected": self.rejected,
            "sent": self.sent,
            "received": self.received,
            "bytes_sent": self.bytes_sent,
            "bytes_received": self.bytes_received,
        }


def seq_newer(a: int, b: int) -> bool:
    """Return True when serial-number sequence a is newer than b."""

    if a == b:
        return False
    return ((a - b) & SEQ_MASK) < SEQ_HALF


def version_newer(a: tuple[int, int], b: tuple[int, int]) -> bool:
    if a[0] != b[0]:
        return a[0] > b[0]
    return seq_newer(a[1], b[1])


def validate_record(
    record: Record,
    now_s: float,
    key: bytes,
    *,
    stale_after_s: float = DEFAULT_STALE_AFTER_S,
    allow_stale: bool = False,
    max_future_skew_s: float = DEFAULT_MAX_FUTURE_SKEW_S,
) -> None:
    if record.origin_id <= 0:
        raise RecordRejected("origin")
    if record.epoch <= 0:
        raise RecordRejected("epoch")
    if record.seq <= 0:
        raise RecordRejected("seq")
    if not 0 <= record.quality <= 100:
        raise RecordRejected("quality")
    if not 0 <= record.battery_mv <= 6000:
        raise RecordRejected("battery")
    if not 0 <= record.risk <= 4:
        raise RecordRejected("risk")
    if record.priority not in (PRIORITY_ROUTINE, PRIORITY_ALERT):
        raise RecordRejected("priority")
    if not record.verify(key):
        raise RecordRejected("auth")
    if record.fix_time_s > now_s + max_future_skew_s:
        raise RecordRejected("future")
    if not allow_stale and record.age_s(now_s) > stale_after_s:
        raise RecordRejected("stale")


class Node:
    """A simulated collar with a latest-location table and version vector."""

    def __init__(
        self,
        node_id: int,
        x_m: float,
        y_m: float,
        key: bytes,
        keys: Mapping[int, bytes],
        *,
        fix_interval_s: float = 10.0,
        stale_after_s: float = DEFAULT_STALE_AFTER_S,
        history_limit: int = 256,
    ) -> None:
        self.node_id = int(node_id)
        self.x_m = float(x_m)
        self.y_m = float(y_m)
        self.key = key
        self.keys = keys
        self.fix_interval_s = float(fix_interval_s)
        self.stale_after_s = float(stale_after_s)
        self.epoch = 1
        self.seq = 0
        self.records: dict[int, Record] = {}
        self.record_ttls: dict[int, int] = {}
        self.history: deque[Record] = deque(maxlen=history_limit)
        self.stats = NodeStats()
        self.next_fix_s = 0.0

    @property
    def position_m(self) -> tuple[float, float]:
        return (self.x_m, self.y_m)

    def set_position(self, x_m: float, y_m: float) -> None:
        self.x_m = float(x_m)
        self.y_m = float(y_m)

    def make_record(
        self,
        now_s: float,
        *,
        priority: int = PRIORITY_ROUTINE,
        risk: int = 0,
        quality: int = 100,
        battery_mv: int = 3700,
        ttl: int = DEFAULT_TTL,
    ) -> Record:
        self.seq = (self.seq + 1) & SEQ_MASK
        if self.seq == 0:
            self.seq = 1
            self.epoch = (self.epoch + 1) & 0xFFFF
            if self.epoch == 0:
                self.epoch = 1
        record = Record(
            origin_id=self.node_id,
            epoch=self.epoch,
            seq=self.seq,
            fix_time_s=int(now_s),
            x_cm=round(self.x_m * 100),
            y_cm=round(self.y_m * 100),
            quality=quality,
            battery_mv=battery_mv,
            risk=risk,
            priority=priority,
        ).sign(self.key)
        self.ingest(record, now_s, ttl=ttl)
        self.stats.generated += 1
        return record

    def ingest(
        self,
        record: Record,
        now_s: float,
        *,
        ttl: int = DEFAULT_TTL,
        allow_stale: bool = False,
    ) -> IngestResult:
        key = self.keys.get(record.origin_id)
        if key is None:
            self.stats.rejected += 1
            return IngestResult(False, "unknown-origin")
        try:
            validate_record(
                record,
                now_s,
                key,
                stale_after_s=self.stale_after_s,
                allow_stale=allow_stale,
            )
        except RecordRejected as exc:
            self.stats.rejected += 1
            return IngestResult(False, exc.reason)
        existing = self.records.get(record.origin_id)
        if existing is not None:
            if record.record_id == existing.record_id:
                self.stats.duplicates += 1
                if ttl > self.record_ttls.get(record.origin_id, 0):
                    self.record_ttls[record.origin_id] = ttl
                return IngestResult(False, "duplicate", duplicate=True)
            if not record.newer_than(existing):
                self.stats.rejected += 1
                return IngestResult(False, "old")
        self.records[record.origin_id] = record
        self.record_ttls[record.origin_id] = ttl
        self.history.append(record)
        self.stats.accepted += 1
        return IngestResult(True, "accepted")

    def latest_vv(self) -> dict[int, tuple[int, int]]:
        return {
            origin: (record.epoch, record.seq)
            for origin, record in self.records.items()
        }

    def pending_for(self, peer_vv: Mapping[int, tuple[int, int]]) -> list[Envelope]:
        pending: list[Envelope] = []
        for origin, record in self.records.items():
            ttl = self.record_ttls.get(origin, 0)
            if record.origin_id != self.node_id and ttl <= 0:
                continue
            peer_version = peer_vv.get(origin)
            if peer_version is None or version_newer((record.epoch, record.seq), peer_version):
                pending.append(Envelope(record, ttl))
        pending.sort(
            key=lambda env: (
                -env.record.priority,
                -env.record.fix_time_s,
                env.record.origin_id,
                -env.record.seq,
            )
        )
        return pending

    def sync_with(self, peer: "Node", now_s: float, *, budget: int = 8) -> SyncResult:
        self.stats.syncs += 1
        peer.stats.syncs += 1
        result = SyncResult()
        to_peer = self.pending_for(peer.latest_vv())
        to_self = peer.pending_for(self.latest_vv())

        for envelope in to_peer[:budget]:
            ttl = envelope.ttl if envelope.record.origin_id == self.node_id else envelope.ttl - 1
            if ttl <= 0:
                continue
            outcome = peer.ingest(envelope.record, now_s, ttl=ttl)
            if outcome.accepted:
                result.sent += 1
                result.bytes_sent += RECORD_WIRE_BYTES
                self.stats.sent += 1
                self.stats.bytes_sent += RECORD_WIRE_BYTES
                peer.stats.received += 1
                peer.stats.bytes_received += RECORD_WIRE_BYTES
            elif outcome.duplicate:
                result.duplicates += 1
            else:
                result.rejected += 1

        for envelope in to_self[:budget]:
            ttl = envelope.ttl if envelope.record.origin_id == peer.node_id else envelope.ttl - 1
            if ttl <= 0:
                continue
            outcome = self.ingest(envelope.record, now_s, ttl=ttl)
            if outcome.accepted:
                result.received += 1
                result.bytes_received += RECORD_WIRE_BYTES
                peer.stats.sent += 1
                peer.stats.bytes_sent += RECORD_WIRE_BYTES
                self.stats.received += 1
                self.stats.bytes_received += RECORD_WIRE_BYTES
            elif outcome.duplicate:
                result.duplicates += 1
            else:
                result.rejected += 1

        return result

    def snapshot(self) -> dict[int, Record]:
        return dict(self.records)


class Phone:
    """A farmer phone acting as a mobile sink and optional data mule."""

    def __init__(
        self,
        keys: Mapping[int, bytes],
        *,
        stale_after_s: float = DEFAULT_STALE_AFTER_S,
    ) -> None:
        self.keys = keys
        self.stale_after_s = float(stale_after_s)
        self.records: dict[int, Record] = {}
        self.received_at: dict[tuple[int, int, int], float] = {}
        self.direct_origins: set[int] = set()
        self.stats = NodeStats()

    def ingest(self, record: Record, now_s: float, *, allow_stale: bool = True) -> IngestResult:
        key = self.keys.get(record.origin_id)
        if key is None:
            self.stats.rejected += 1
            return IngestResult(False, "unknown-origin")
        try:
            validate_record(
                record,
                now_s,
                key,
                stale_after_s=self.stale_after_s,
                allow_stale=allow_stale,
            )
        except RecordRejected as exc:
            self.stats.rejected += 1
            return IngestResult(False, exc.reason)
        existing = self.records.get(record.origin_id)
        if existing is not None:
            if record.record_id == existing.record_id:
                self.stats.duplicates += 1
                return IngestResult(False, "duplicate", duplicate=True)
            if not record.newer_than(existing):
                self.stats.rejected += 1
                return IngestResult(False, "old")
        self.records[record.origin_id] = record
        self.received_at[record.record_id] = now_s
        self.stats.accepted += 1
        return IngestResult(True, "accepted")

    def sync_with_node(self, node: Node, now_s: float, *, push: bool = False, budget: int = 64) -> SyncResult:
        self.direct_origins.add(node.node_id)
        self.stats.syncs += 1
        node.stats.syncs += 1
        result = SyncResult()

        incoming = sorted(
            node.records.values(),
            key=lambda record: (-record.priority, -record.fix_time_s, record.origin_id),
        )
        for record in incoming[:budget]:
            existing = self.records.get(record.origin_id)
            if existing is not None and not record.newer_than(existing):
                continue
            outcome = self.ingest(record, now_s, allow_stale=True)
            if outcome.accepted:
                result.received += 1
                result.bytes_received += RECORD_WIRE_BYTES
                node.stats.sent += 1
                node.stats.bytes_sent += RECORD_WIRE_BYTES
                self.stats.received += 1
                self.stats.bytes_received += RECORD_WIRE_BYTES
            elif outcome.duplicate:
                result.duplicates += 1
            else:
                result.rejected += 1

        if push:
            outgoing = sorted(
                self.records.values(),
                key=lambda record: (-record.priority, -record.fix_time_s, record.origin_id),
            )
            for record in outgoing[:budget]:
                existing = node.records.get(record.origin_id)
                if existing is not None and not record.newer_than(existing):
                    continue
                outcome = node.ingest(record, now_s, ttl=DEFAULT_TTL)
                if outcome.accepted:
                    result.sent += 1
                    result.bytes_sent += RECORD_WIRE_BYTES
                    self.stats.sent += 1
                    self.stats.bytes_sent += RECORD_WIRE_BYTES
                    node.stats.received += 1
                    node.stats.bytes_received += RECORD_WIRE_BYTES
                elif outcome.duplicate:
                    result.duplicates += 1
                else:
                    result.rejected += 1

        return result
