"""Basys 3 host-link frame format for the HerdSync-DTN bench bridge.

The frame is deliberately small and unsigned. It is a bench transport for the
Basys 3 POC, not a production authenticated record format.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass
from typing import Iterable

SYNC0 = 0xAA
SYNC1 = 0x55
VERSION = 0x01
TYPE_RECORD = 0x01
TYPE_PEER = 0x02
MAX_PAYLOAD = 64
HEADER_BYTES = 5
CRC_BYTES = 2
RECORD_PAYLOAD_BYTES = 36
PEER_PAYLOAD_BYTES = 13

_CRC_POLY = 0x1021
_CRC_INIT = 0xFFFF
_CRC_MASK = 0xFFFF


def crc16_ccitt(data: bytes | bytearray | Iterable[int]) -> int:
    """CRC-16/CCITT-FALSE over the supplied bytes."""

    crc = _CRC_INIT
    for value in data:
        crc ^= (int(value) & 0xFF) << 8
        for _ in range(8):
            if crc & 0x8000:
                crc = ((crc << 1) ^ _CRC_POLY) & _CRC_MASK
            else:
                crc = (crc << 1) & _CRC_MASK
    return crc


def encode_frame(frame_type: int, payload: bytes) -> bytes:
    if len(payload) > MAX_PAYLOAD:
        raise ValueError("payload too large")
    body = bytes((VERSION, frame_type & 0xFF, len(payload))) + bytes(payload)
    crc = crc16_ccitt(body)
    return bytes((SYNC0, SYNC1)) + body + bytes((crc >> 8, crc & 0xFF))


def encode_record_payload(
    *,
    origin_id: int,
    epoch: int,
    seq: int,
    fix_time_s: int,
    x_cm: int,
    y_cm: int,
    quality: int = 100,
    battery_mv: int = 3700,
    risk: int = 0,
    priority: int = 0,
) -> bytes:
    """Encode the 28-byte POC record plus eight zero authentication bytes."""

    payload = struct.pack(
        ">BBHIIIiiBHB",
        VERSION,
        priority & 0xFF,
        epoch & 0xFFFF,
        origin_id & 0xFFFFFFFF,
        seq & 0xFFFFFFFF,
        fix_time_s & 0xFFFFFFFF,
        int(x_cm),
        int(y_cm),
        quality & 0xFF,
        battery_mv & 0xFFFF,
        risk & 0xFF,
    )
    return payload + bytes(8)


def decode_record_payload(payload: bytes) -> dict:
    if len(payload) != RECORD_PAYLOAD_BYTES:
        raise ValueError("record payload must be 36 bytes")
    (
        schema,
        priority,
        epoch,
        origin_id,
        seq,
        fix_time_s,
        x_cm,
        y_cm,
        quality,
        battery_mv,
        risk,
    ) = struct.unpack(">BBHIIIiiBHB", payload[:28])
    if schema != VERSION:
        raise ValueError("unsupported record schema")
    return {
        "schema": schema,
        "priority": priority,
        "epoch": epoch,
        "origin_id": origin_id,
        "seq": seq,
        "fix_time_s": fix_time_s,
        "x_cm": x_cm,
        "y_cm": y_cm,
        "quality": quality,
        "battery_mv": battery_mv,
        "risk": risk,
        "auth_tag": payload[28:36].hex(),
    }


def encode_peer_summary(peer_id: int, seq: int, fix_time_s: int, risk: int) -> bytes:
    return struct.pack(
        ">IIIB",
        peer_id & 0xFFFFFFFF,
        seq & 0xFFFFFFFF,
        fix_time_s & 0xFFFFFFFF,
        risk & 0xFF,
    )


def decode_peer_summary(payload: bytes) -> dict:
    if len(payload) < PEER_PAYLOAD_BYTES:
        raise ValueError("peer payload must be at least 13 bytes")
    peer_id, seq, fix_time_s, risk = struct.unpack(">IIIB", payload[:13])
    return {
        "peer_id": peer_id,
        "seq": seq,
        "fix_time_s": fix_time_s,
        "risk": risk,
    }


@dataclass(frozen=True)
class Frame:
    frame_type: int
    payload: bytes
    raw: bytes


class FrameParser:
    """Incremental parser that tolerates leading noise and bad-CRC frames."""

    def __init__(self) -> None:
        self._buffer = bytearray()
        self.frames: list[Frame] = []
        self.crc_errors = 0
        self.length_errors = 0

    @property
    def pending_bytes(self) -> int:
        return len(self._buffer)

    def feed(self, data: bytes | bytearray | Iterable[int]) -> list[Frame]:
        self._buffer.extend(int(value) & 0xFF for value in data)
        decoded: list[Frame] = []
        while True:
            frame = self._decode_one()
            if frame is None:
                break
            decoded.append(frame)
            self.frames.append(frame)
        return decoded

    def _decode_one(self) -> Frame | None:
        while len(self._buffer) >= 2:
            if self._buffer[0] != SYNC0 or self._buffer[1] != SYNC1:
                del self._buffer[0]
                continue
            break
        if len(self._buffer) < HEADER_BYTES:
            return None
        if self._buffer[2] != VERSION:
            del self._buffer[0]
            return None
        payload_len = self._buffer[4]
        if payload_len > MAX_PAYLOAD:
            self.length_errors += 1
            del self._buffer[0]
            return None
        total = HEADER_BYTES + payload_len + CRC_BYTES
        if len(self._buffer) < total:
            return None
        candidate = bytes(self._buffer[:total])
        expected = crc16_ccitt(candidate[2:-2])
        received = (candidate[-2] << 8) | candidate[-1]
        if expected != received:
            self.crc_errors += 1
            del self._buffer[0]
            return None
        del self._buffer[:total]
        return Frame(candidate[3], candidate[5:-2], candidate)


def summarize_frame(frame: Frame) -> dict:
    summary = {
        "type": frame.frame_type,
        "payload_len": len(frame.payload),
        "crc_ok": True,
    }
    if frame.frame_type == TYPE_RECORD:
        try:
            summary["record"] = decode_record_payload(frame.payload)
        except ValueError as exc:
            summary["error"] = str(exc)
    elif frame.frame_type == TYPE_PEER:
        try:
            summary["peer"] = decode_peer_summary(frame.payload)
        except ValueError as exc:
            summary["error"] = str(exc)
    else:
        summary["error"] = "unknown frame type"
    return summary
