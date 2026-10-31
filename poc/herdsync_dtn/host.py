"""Host-side collector for the Basys 3 HerdSync-DTN USB-UART bridge."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from .uart_frame import (
    TYPE_PEER,
    FrameParser,
    encode_frame,
    encode_peer_summary,
    summarize_frame,
)


def _format_record(summary: dict, elapsed_s: float) -> str:
    record = summary.get("record")
    if record is None:
        return f"{elapsed_s:8.3f}s  record error={summary.get('error', 'unknown')}"
    return (
        f"{elapsed_s:8.3f}s  record origin={record['origin_id']} "
        f"seq={record['seq']} fix={record['fix_time_s']}s "
        f"x={record['x_cm'] / 100.0:8.2f}m y={record['y_cm'] / 100.0:8.2f}m "
        f"risk={record['risk']} quality={record['quality']} "
        f"battery={record['battery_mv']}mV"
    )


def _format_peer(summary: dict, elapsed_s: float) -> str:
    peer = summary.get("peer")
    if peer is None:
        return f"{elapsed_s:8.3f}s  peer error={summary.get('error', 'unknown')}"
    return (
        f"{elapsed_s:8.3f}s  peer id={peer['peer_id']} seq={peer['seq']} "
        f"fix={peer['fix_time_s']}s risk={peer['risk']}"
    )


def _open_serial(port: str, baud: int):
    try:
        import serial
    except ImportError as exc:
        raise SystemExit(
            "pyserial is required: python3 -m pip install pyserial"
        ) from exc
    return serial.Serial(port, baud, timeout=0.1)


def _send_peer(ser, peer_id: int, seq: int, fix_s: int, risk: int) -> None:
    payload = encode_peer_summary(peer_id, seq, fix_s, risk)
    ser.write(encode_frame(TYPE_PEER, payload))
    ser.flush()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Collect framed records from the Basys 3 HerdSync UART bridge."
    )
    parser.add_argument("--port", help="Serial port, for example /dev/ttyUSB1.")
    parser.add_argument("--baud", type=int, default=115200, help="UART baud rate.")
    parser.add_argument("--duration", type=float, default=0.0, help="Stop after N seconds.")
    parser.add_argument("--jsonl", metavar="PATH", help="Write decoded frames as JSON Lines.")
    parser.add_argument("--send-peer", action="store_true", help="Send a peer summary to the board.")
    parser.add_argument("--peer-id", type=int, default=2)
    parser.add_argument("--peer-seq", type=int, default=1)
    parser.add_argument("--peer-fix", type=int, default=0)
    parser.add_argument("--peer-risk", type=int, default=0)
    parser.add_argument("--peer-interval", type=float, default=0.0, help="Resend peer summary every N seconds.")
    parser.add_argument("--list-ports", action="store_true", help="List serial ports and exit.")
    args = parser.parse_args(argv)

    if args.list_ports:
        try:
            from serial.tools import list_ports
        except ImportError as exc:
            raise SystemExit(
                "pyserial is required: python3 -m pip install pyserial"
            ) from exc
        for port in list_ports.comports():
            print(f"{port.device}  {port.description}")
        return 0

    if not args.port:
        parser.error("--port is required unless --list-ports is used")

    ser = _open_serial(args.port, args.baud)
    frame_parser = FrameParser()
    jsonl = None
    if args.jsonl:
        path = Path(args.jsonl)
        path.parent.mkdir(parents=True, exist_ok=True)
        jsonl = path.open("w", encoding="utf-8")

    start = time.monotonic()
    next_peer = start
    received = 0
    print("Basys 3 HerdSync UART collector; Ctrl-C to stop.")
    try:
        if args.send_peer:
            _send_peer(ser, args.peer_id, args.peer_seq, args.peer_fix, args.peer_risk)
            next_peer = start + args.peer_interval if args.peer_interval > 0 else float("inf")

        while True:
            now = time.monotonic()
            elapsed = now - start
            if args.duration > 0 and elapsed >= args.duration:
                break
            if args.send_peer and now >= next_peer:
                _send_peer(ser, args.peer_id, args.peer_seq, args.peer_fix, args.peer_risk)
                next_peer = now + args.peer_interval

            chunk = ser.read(256)
            if not chunk:
                continue
            for frame in frame_parser.feed(chunk):
                received += 1
                summary = summarize_frame(frame)
                if frame.frame_type == TYPE_PEER:
                    line = _format_peer(summary, elapsed)
                else:
                    line = _format_record(summary, elapsed)
                print(line)
                if jsonl is not None:
                    jsonl.write(json.dumps({"t_s": elapsed, **summary}) + "\n")
                    jsonl.flush()
    except KeyboardInterrupt:
        pass
    finally:
        ser.close()
        if jsonl is not None:
            jsonl.close()

    if frame_parser.crc_errors:
        print(f"CRC errors: {frame_parser.crc_errors}", file=sys.stderr)
    print(f"Frames received: {received}, bytes buffered: {frame_parser.pending_bytes}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
