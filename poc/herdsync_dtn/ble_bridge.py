"""Laptop-hosted BLE GATT bridge for the Basys 3 HerdSync bench.

This turns a Linux laptop into a BLE peripheral. The FPGA still streams framed
records over USB-UART; the laptop exposes them to a phone and forwards a phone
written peer summary back to the FPGA. No FPGA logic or cue path changes.

This is a bench aid, not a production collar BLE stack. It is unauthenticated
and does not validate radio range, power, body attenuation, or an embedded BLE
implementation.

Use ``--simulate`` to run without hardware: generates fake records from the
demo trace so the full laptop-to-phone BLE path can be exercised.
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import os
import signal
import threading
import time
from typing import Callable

from .ble_codec import (
    BLE_PEER_COMMAND_UUID,
    BLE_PEER_STATUS_UUID,
    BLE_RECORD_UUID,
    BLE_SERVICE_UUID,
    BLE_STATUS_UUID,
    BLE_SUMMARY_UUID,
    format_status,
    pack_summary,
    parse_peer_command,
)
from .uart_frame import (
    RECORD_PAYLOAD_BYTES,
    TYPE_PEER,
    TYPE_RECORD,
    FrameParser,
    encode_frame,
    encode_peer_summary,
    encode_record_payload,
)

try:
    import serial
except ImportError as exc:
    raise SystemExit(
        "pyserial is required: python3 -m pip install pyserial"
    ) from exc

try:
    from bluez_peripheral.advert import Advertisement
    from bluez_peripheral.gatt.characteristic import CharacteristicFlags, characteristic
    from bluez_peripheral.gatt.service import Service
    from bluez_peripheral.util import Adapter, get_message_bus
except ImportError as exc:
    raise SystemExit(
        "bluez-peripheral is required: "
        "python3 -m pip install -r poc/requirements-ble.txt"
    ) from exc


class SerialLink:
    """Read framed records from the FPGA and send peer summaries back."""

    def __init__(
        self,
        port: str,
        baud: int,
        on_record: Callable[[bytes], None],
        on_error: Callable[[str], None],
    ) -> None:
        self._serial = serial.Serial(port, baud, timeout=0.1)
        self._parser = FrameParser()
        self._on_record = on_record
        self._on_error = on_error
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._reader, daemon=True)

    def start(self) -> None:
        self._thread.start()

    def _reader(self) -> None:
        while not self._stop.is_set():
            try:
                chunk = self._serial.read(256)
            except serial.SerialException as exc:
                if not self._stop.is_set():
                    self._on_error(f"serial read failed: {exc}")
                return
            if not chunk:
                continue
            for frame in self._parser.feed(chunk):
                if frame.frame_type == TYPE_RECORD:
                    try:
                        self._on_record(frame.payload)
                    except ValueError as exc:
                        self._on_error(f"record decode failed: {exc}")

    def send_peer(self, peer_id: int, seq: int, fix_s: int, risk: int) -> None:
        frame = encode_frame(
            TYPE_PEER,
            encode_peer_summary(peer_id, seq, fix_s, risk),
        )
        with self._lock:
            self._serial.write(frame)
            self._serial.flush()

    def close(self) -> None:
        self._stop.set()
        if self._thread.is_alive():
            self._thread.join(timeout=1.0)
        self._serial.close()


class SimulatedLink:
    """Generate fake records from the demo trace CSV without FPGA hardware."""

    DEMO_TRACE = os.path.join(
        os.path.dirname(__file__), "..", "..", "data", "demo_trace.csv"
    )
    # Road segment at x=0: thresholds mirror RTL (CAUTION 500 cm, DANGER 200 cm)
    CAUTION_CM = 500
    DANGER_CM = 200

    def __init__(
        self,
        on_record: Callable[[bytes], None],
        interval: float = 0.5,
    ) -> None:
        self._on_record = on_record
        self._interval = interval
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._generator, daemon=True)
        self._trace = self._load_trace()

    def _load_trace(self) -> list[tuple[int, int]]:
        path = os.path.normpath(self.DEMO_TRACE)
        rows: list[tuple[int, int]] = []
        with open(path) as fh:
            for row in csv.DictReader(fh):
                rows.append((int(row["x_cm"]), int(row["y_cm"])))
        return rows

    def start(self) -> None:
        self._thread.start()

    def _risk_for(self, x_cm: int) -> int:
        dist = abs(x_cm)
        if dist <= self.DANGER_CM:
            return 3  # DANGER
        if dist <= self.CAUTION_CM:
            return 2  # CAUTION
        return 1      # SAFE

    def _generator(self) -> None:
        seq = 0
        epoch = 1
        t0 = int(time.time())
        while not self._stop.is_set():
            for x_cm, y_cm in self._trace:
                if self._stop.is_set():
                    return
                seq += 1
                risk = self._risk_for(x_cm)
                payload = encode_record_payload(
                    origin_id=1,
                    epoch=epoch,
                    seq=seq,
                    fix_time_s=int(time.time()) - t0,
                    x_cm=x_cm,
                    y_cm=y_cm,
                    quality=100,
                    battery_mv=3700,
                    risk=risk,
                )
                self._on_record(payload)
                self._stop.wait(self._interval)

    def send_peer(self, peer_id: int, seq: int, fix_s: int, risk: int) -> None:
        print(f"SIM: peer command ignored (no hardware): {peer_id},{seq},{fix_s},{risk}")

    def close(self) -> None:
        self._stop.set()
        if self._thread.is_alive():
            self._thread.join(timeout=1.0)


class BleBridge(Service):
    def __init__(self) -> None:
        super().__init__(BLE_SERVICE_UUID, primary=True)
        self._record = bytes(RECORD_PAYLOAD_BYTES)
        self._summary = bytes(20)
        self._status = "waiting for Basys 3 record"
        self._peer_status = "no peer command yet"
        self._link: SerialLink | None = None

    def attach(self, link: SerialLink) -> None:
        self._link = link

    @characteristic(
        BLE_RECORD_UUID,
        CharacteristicFlags.READ | CharacteristicFlags.NOTIFY,
    )
    def record(self, options):
        return self._record

    @characteristic(
        BLE_SUMMARY_UUID,
        CharacteristicFlags.READ | CharacteristicFlags.NOTIFY,
    )
    def summary(self, options):
        return self._summary

    @characteristic(
        BLE_STATUS_UUID,
        CharacteristicFlags.READ | CharacteristicFlags.NOTIFY,
    )
    def status(self, options):
        return self._status.encode("utf-8")

    @characteristic(
        BLE_PEER_STATUS_UUID,
        CharacteristicFlags.READ | CharacteristicFlags.NOTIFY,
    )
    def peer_status(self, options):
        return self._peer_status.encode("utf-8")

    @characteristic(BLE_PEER_COMMAND_UUID, CharacteristicFlags.WRITE)
    def peer_command(self, options):
        return b""

    @peer_command.setter
    def peer_command(self, value: bytes, options) -> None:
        text = value.decode("utf-8", errors="replace").strip()
        try:
            peer_id, seq, fix_s, risk = parse_peer_command(text)
            if self._link is None:
                raise ValueError("serial link not ready")
            self._link.send_peer(peer_id, seq, fix_s, risk)
            message = f"sent {peer_id},{seq},{fix_s},{risk}"
        except ValueError as exc:
            message = f"error: {exc}"
        self._peer_status = message
        self.peer_status.changed(message.encode("utf-8"))
        print(f"BLE peer command: {message}")

    def update_record(self, payload: bytes) -> None:
        try:
            summary = pack_summary(payload)
            status = format_status(payload)
        except ValueError as exc:
            print(f"record decode error: {exc}")
            return
        self._record = bytes(payload)
        self._summary = summary
        self._status = status
        self.record.changed(self._record)
        self.summary.changed(self._summary)
        self.status.changed(status.encode("utf-8"))


async def _run(args: argparse.Namespace) -> None:
    loop = asyncio.get_running_loop()
    service = BleBridge()

    def on_record(payload: bytes) -> None:
        loop.call_soon_threadsafe(service.update_record, payload)
        if args.verbose:
            try:
                print(format_status(payload))
            except ValueError as exc:
                print(f"record decode error: {exc}")

    def on_error(message: str) -> None:
        print(message)

    if args.simulate:
        link = SimulatedLink(on_record, interval=args.interval)
        print(f"SIMULATE mode: generating fake records every {args.interval}s")
    else:
        link = SerialLink(args.port, args.baud, on_record, on_error)

    service.attach(link)

    bus = await get_message_bus()
    await service.register(bus)
    adapter = await Adapter.get_first(bus)
    await adapter.set_alias(args.name)
    advertisement = Advertisement(
        args.name,
        [BLE_SERVICE_UUID],
        appearance=0,
        timeout=0,
        discoverable=True,
    )
    await advertisement.register(bus, adapter)
    link.start()

    print(f"BLE peripheral '{args.name}' advertising.")
    if not args.simulate:
        print(f"UART: {args.port} at {args.baud} baud.")
    print("Phone: connect with nRF Connect or LightBlue, then read the characteristics.")
    print("Write peer command as ASCII: peer_id,seq,fix_time_s,risk  (for example 2,7,30,1)")
    print("Ctrl-C to stop.")

    stop = asyncio.Event()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, stop.set)
    try:
        await stop.wait()
    finally:
        link.close()
        bus.disconnect()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Expose Basys 3 HerdSync UART records as a BLE GATT peripheral."
    )
    parser.add_argument("--port", default="/dev/ttyUSB1", help="Basys 3 USB-UART port.")
    parser.add_argument("--baud", type=int, default=115200, help="UART baud rate.")
    parser.add_argument("--name", default="BALAT-DTN", help="BLE advertised name.")
    parser.add_argument("--verbose", action="store_true", help="Print every received record.")
    parser.add_argument(
        "--simulate",
        action="store_true",
        help="Generate fake records from demo trace (no FPGA needed).",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=0.5,
        help="Seconds between simulated records (default 0.5).",
    )
    args = parser.parse_args(argv)
    try:
        asyncio.run(_run(args))
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
