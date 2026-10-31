"""Codecs for the laptop-hosted BLE bench peripheral.

The laptop is only a GATT bridge. These helpers keep the phone-facing format
separate from the UART frame format and from the FPGA.
"""

from __future__ import annotations

from .uart_frame import decode_record_payload

BLE_SERVICE_UUID = "7d9f3a20-4b1a-4f0e-9b6e-2a5c8d1e0001"
BLE_RECORD_UUID = "7d9f3a20-4b1a-4f0e-9b6e-2a5c8d1e0002"
BLE_SUMMARY_UUID = "7d9f3a20-4b1a-4f0e-9b6e-2a5c8d1e0003"
BLE_STATUS_UUID = "7d9f3a20-4b1a-4f0e-9b6e-2a5c8d1e0004"
BLE_PEER_COMMAND_UUID = "7d9f3a20-4b1a-4f0e-9b6e-2a5c8d1e0005"
BLE_PEER_STATUS_UUID = "7d9f3a20-4b1a-4f0e-9b6e-2a5c8d1e0006"

SUMMARY_BYTES = 20


def _clamp_i16(value: int) -> int:
    return max(-32768, min(32767, int(value)))


def pack_summary(payload: bytes) -> bytes:
    """Pack a 20-byte notification-friendly summary.

    The summary uses signed 16-bit centimetres, so it is valid for the demo
    coordinate range only. The full 36-byte record remains available separately.
    """

    record = decode_record_payload(payload)
    return (
        int(record["origin_id"]).to_bytes(4, "big")
        + int(record["seq"]).to_bytes(4, "big")
        + int(record["fix_time_s"]).to_bytes(4, "big")
        + _clamp_i16(record["x_cm"]).to_bytes(2, "big", signed=True)
        + _clamp_i16(record["y_cm"]).to_bytes(2, "big", signed=True)
        + bytes((int(record["risk"]) & 0xFF, int(record["quality"]) & 0xFF))
        + (int(record["battery_mv"]) & 0xFFFF).to_bytes(2, "big")
    )


def format_status(payload: bytes) -> str:
    """Return a human-readable status line for the phone's read characteristic."""

    record = decode_record_payload(payload)
    return (
        f"origin={record['origin_id']} seq={record['seq']} "
        f"fix={record['fix_time_s']}s "
        f"x={record['x_cm'] / 100.0:.2f}m y={record['y_cm'] / 100.0:.2f}m "
        f"risk={record['risk']} quality={record['quality']} "
        f"battery={record['battery_mv']}mV"
    )


def parse_peer_command(text: str) -> tuple[int, int, int, int]:
    """Parse the phone write format: ``peer_id,seq,fix_time_s,risk``."""

    parts = text.replace(";", ",").split(",")
    if len(parts) != 4:
        raise ValueError("expected peer_id,seq,fix_time_s,risk")
    try:
        peer_id, seq, fix_time_s, risk = (int(part.strip(), 0) for part in parts)
    except ValueError as exc:
        raise ValueError("peer command fields must be integers") from exc
    if not 0 <= peer_id <= 0xFFFFFFFF:
        raise ValueError("peer_id out of range")
    if not 0 <= seq <= 0xFFFFFFFF:
        raise ValueError("seq out of range")
    if not 0 <= fix_time_s <= 0xFFFFFFFF:
        raise ValueError("fix_time_s out of range")
    if not 0 <= risk <= 4:
        raise ValueError("risk out of range")
    return peer_id, seq, fix_time_s, risk
