# Basys 3 HerdSync UART Bridge Demo

> **Status:** Bench demo; simulation, Vivado build, and the physical record and
> peer-summary paths are verified. This is a post-v0.1 communication transport for the HerdSync-DTN
> POC. It is not BLE, not authenticated, and not part of the v0.1 cue decision
> path.

This demo uses only a Basys 3, its USB cable, and a PC. The FPGA streams framed
location records over the on-board USB-UART. A Python host acts as the phone or
DTN peer: it validates frames, prints the latest records, and can send a peer
summary back to the board. It validates the FPGA-side framing and host-side
collection without a BLE radio.

## 1. What the demo shows

- The existing synthetic trace, road geometry, risk FSM, and cue scheduler still
  run unchanged.
- Every 100 ms sample emits a 43-byte UART frame containing a 36-byte record.
  The record is latched one clock after the sample so its risk byte is the same
  state shown on the risk LEDs.
- The host validates sync, version, length, and CRC-16/CCITT-FALSE.
- The host decodes origin, sequence, fix time, local coordinates, quality,
  battery, and risk.
- The host can send a peer summary; the board displays `PEER SEEN` and the peer
  risk bit.
- UART activity, CRC errors, TX drops, and peer status are visible on LEDs.
- A stale input still forces `INVALID`, drops the cue, and asserts the fault LED.

## 2. What it does not show

- BLE advertising, scanning, GATT, or radio range.
- Body attenuation, antenna behaviour, interference, or battery life.
- Production authentication. The RTL record has eight zero tag bytes.
- A real phone app, persistent storage, or map/firmware updates.
- Any path from UART data to the cue output.

## 3. Hardware and tools

| Item | Requirement |
| --- | --- |
| Board | Digilent Basys 3, rev B, `xc7a35tcpg236-1` |
| Toolchain | Vivado 2024.2 (tested) |
| Cable | USB cable for JTAG, power, and the USB-UART bridge |
| Host | Linux, macOS, or Windows with Python 3 and `pyserial` |
| Optional | Logic analyser on the USB-UART TX pin or a second serial monitor |
| Not required | BLE module, phone, GNSS receiver, map data, or internet |

Install the host dependency:

```bash
python3 -m pip install pyserial
```

## 4. Files

| Path | Purpose |
| --- | --- |
| `rtl/balat_herdsync_basys3_top.v` | Separate top: risk pipeline plus UART bridge |
| `rtl/herdsync_uart_bridge.v` | Record framing, CRC, host parser, counters |
| `rtl/uart_tx.v` | 8N1 UART transmitter |
| `rtl/uart_rx.v` | 8N1 UART receiver with a two-flop synchronizer |
| `constraints/basys3_herdsync.xdc` | Basys 3 pins, including USB-UART |
| `scripts/build_basys3_herdsync.tcl` | Vivado non-project build |
| `scripts/run_herdsync_sims.sh` | Icarus simulation suite |
| `poc/herdsync_dtn/uart_frame.py` | Host frame/CRC codec |
| `poc/herdsync_dtn/host.py` | Serial collector and peer-summary sender |
| `tb/tb_uart_tx.v` | UART TX timing and data test |
| `tb/tb_uart_rx.v` | UART RX data and framing-error test |
| `tb/tb_herdsync_uart_bridge.v` | Frame, CRC, peer parse, and reset test |
| `tb/tb_balat_herdsync_top.v` | End-to-end bridge and cue-path integration test |

## 5. Frame format

```text
AA 55 | version | type | length | payload | CRC16
```

| Field | Width | Value |
| --- | --- | --- |
| Sync | 2 bytes | `AA 55` |
| Version | 1 byte | `01` |
| Type | 1 byte | `01` record, `02` peer summary |
| Length | 1 byte | Payload length, 0-64 |
| Payload | N bytes | Record or peer summary |
| CRC | 2 bytes | CRC-16/CCITT-FALSE over version, type, length, payload |

CRC parameters: polynomial `0x1021`, initial value `0xFFFF`, no reflection, no
final XOR. The Python and RTL implementations use the same byte-wise algorithm.

### Record payload (type 0x01, length 36)

| Offset | Field | Encoding |
| --- | --- | --- |
| 0 | Schema | `u8`, value 1 |
| 1 | Priority | `u8`, 0 routine, 1 alert |
| 2-3 | Epoch | `u16` |
| 4-7 | Origin ID | `u32` |
| 8-11 | Sequence | `u32` |
| 12-15 | Fix time | `u32`, seconds |
| 16-19 | X | `i32`, centimetres |
| 20-23 | Y | `i32`, centimetres |
| 24 | Quality | `u8`, 0-100 |
| 25-26 | Battery | `u16`, millivolts |
| 27 | Risk | `u8`, 0-4 (INVALID/SAFE/CAUTION/DANGER/COOLDOWN) |
| 28-35 | Tag | 8 zero bytes in this demo |

### Peer summary payload (type 0x02, length 13)

| Offset | Field | Encoding |
| --- | --- | --- |
| 0-3 | Peer ID | `u32` |
| 4-7 | Sequence | `u32` |
| 8-11 | Fix time | `u32`, seconds |
| 12 | Risk | `u8`, 0-4 |

## 6. Build the bitstream

```bash
vivado -mode batch -source scripts/build_basys3_herdsync.tcl
```

Outputs:

```text
build/basys3_herdsync/balat_basys3_herdsync.bit
build/basys3_herdsync/balat_basys3_herdsync_routed.dcp
build/basys3_herdsync/utilization.rpt
build/basys3_herdsync/timing_summary.rpt
```

Measured local build with Vivado 2024.2, part `xc7a35tcpg236-1`:

| Metric | Result |
| --- | --- |
| Worst negative slack (WNS) | +0.614 ns |
| Worst hold slack (WHS) | +0.127 ns |
| Timing constraints | Met |
| Slice LUTs | 1053 (5.06%) |
| Slice registers | 1190 (2.86%) |
| DSPs | 18 (20.00%) |
| Block RAM | 0 |
| Bitstream | about 528 KiB compressed |

These are local measurements, not guarantees for other tool versions or board
revisions.

Measured hardware run on the local Basys 3:

| Check | Result |
| --- | --- |
| Port | `/dev/ttyUSB1`, 115200 baud |
| Records captured | 320 across two runs |
| Sequence gaps | 0 within each run |
| CRC errors | 0 |
| Bytes buffered at exit | 0 |
| Risk states observed | 0, 1, 2, 3, 4 (COOLDOWN) |
| JSON Lines check | 30 valid rows |
| Reset mid-capture | Sequence restarted at 1; run 1 ended at 138, run 2 reached 182 |
| Peer summary | Host frame accepted and decoded; counters remain available in RTL but are not shown in the simplified LED display |
| 120 s soak | 1200 frames, 0 sequence gaps, 0 CRC errors, 0 resets, 0 buffered bytes |

Multi-hour/thermal soak behaviour and BLE remain unverified.

## 7. Program the board

Use the same flow as `docs/BASYS3_DEMO.md`, but select
`build/basys3_herdsync/balat_basys3_herdsync.bit`.

The board's USB cable provides both JTAG and the USB-UART bridge. The host
usually sees the UART as `/dev/ttyUSB1` on Linux, `/dev/tty.usbserial-*` on
macOS, or `COMx` on Windows.

## 8. Run the host collector

List candidate ports:

```bash
python3 -m poc.herdsync_dtn.host --list-ports
```

Run the collector:

```bash
python3 -m poc.herdsync_dtn.host --port /dev/ttyUSB1
```

Example output (illustrative, not a hardware capture):

```text
Basys 3 HerdSync UART collector; Ctrl-C to stop.
   0.412s  record origin=1 seq=1 fix=0s x=  -15.00m y=  10.00m risk=1 quality=100 battery=3700mV
   0.512s  record origin=1 seq=2 fix=0s x=  -15.00m y=   9.90m risk=1 quality=100 battery=3700mV
```

Send a peer summary to the board and keep collecting:

```bash
python3 -m poc.herdsync_dtn.host --port /dev/ttyUSB1 \
  --send-peer --peer-id 2 --peer-seq 7 --peer-fix 30 --peer-risk 1
```

Write JSON Lines for later analysis:

```bash
python3 -m poc.herdsync_dtn.host --port /dev/ttyUSB1 \
  --duration 30 --jsonl build/herdsync_uart.jsonl
```

## 9. Controls and LEDs

Controls are the same as the synthetic-trace demo:

| Control | Function |
| --- | --- |
| `SW0` | Run/pause the trace and record generation |
| `SW1` | Force stale/invalid input |
| `SW2` | Enable cue output |
| `SW3` | Force map fault |
| `BTNC` | Reset (active high) |

| LED | Meaning |
| --- | --- |
| `LED0` | SAFE |
| `LED1` | CAUTION |
| `LED2` | DANGER |
| `LED3` | COOLDOWN |
| `LED4` | INVALID / fault |
| `LED5` | Cue active |
| `LED6` | UART telemetry heartbeat |
| `LED7` | Board heartbeat |
| `LED8..LED15` | Off in the simplified POC display |

With `SW0` and `SW2` up and `SW1`/`SW3` down, the host should print a record
every 100 ms. At 115200 baud a 43-byte frame takes about 3.7 ms, so the 10 Hz
rate has ample margin. Frame/error counters remain available for host-side
inspection but are intentionally not shown on the simplified POC LEDs.

## 10. Simulation

```bash
bash scripts/run_herdsync_sims.sh
```

Expected final line:

```text
All Basys 3 HerdSync-DTN simulations passed.
```

The suite covers UART TX timing, UART RX data and framing errors, frame
construction and CRC, record field encoding, TX drop counting, peer-summary
parsing, bad-CRC rejection, reset, the integrated risk path, stale fail-safe,
and the unchanged cue output. The existing `scripts/run_demo_sims.sh` suite also
remains green.

Python protocol tests:

```bash
python3 -m unittest discover -s poc/tests -t . -v
```

## 11. Troubleshooting

| Symptom | Check |
| --- | --- |
| No serial port | USB cable connected; `--list-ports`; install `pyserial` |
| Permission denied | Add the user to `dialout` on Linux, then log in again |
| No records | `SW0` up; board reset released; host baud 115200 |
| Garbled records / CRC errors | Wrong port or baud; confirm the bridge bitstream is programmed |
| Cue never asserts | `SW2` up; wait for DANGER; check the existing demo sequence |
| Host exits immediately | `--duration` may be too short; omit it for continuous capture |

## 12. Safety and limitations

- `cue_out` on JA1 remains a 3.3 V logic-level observation output. Never connect
  a speaker, motor, or other actuator directly.
- The UART bridge is unsigned and unauthenticated. Do not use it as a production
  collar link.
- UART/BLE state does not drive the risk FSM or cue scheduler. Stale input still
  forces `INVALID` and the cue off.
- This demo does not establish BLE range, power, field reliability, or animal
  behaviour.
- Any animal work requires veterinary/animal-welfare review, supervision, a safe
  enclosed area, non-aversive cues, and a stop rule.

## 13. Next step

The next hardware step is still a COTS BLE module, for example a Pmod BLE or an
nRF52/ESP32 board, connected to an unused Pmod header. The Basys 3 would keep
this UART framing and treat the module as a byte pipe; the DTN state machine can
live on the module or a host. See `docs/HERDSYNC_POC.md` for the phased plan.
