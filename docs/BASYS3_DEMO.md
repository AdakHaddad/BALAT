# Basys 3 Synthetic-Trace Demo Guide

This guide builds and runs a deterministic, self-contained Basys 3 demo of the
BALAT risk pipeline. A compiled synthetic track is replayed through the
road-distance engine, risk state machine, and bounded cue scheduler. The result
is visible on the board LEDs and on the `cue_out` logic-level pin.

> **Scope:** This is a bench demonstration of the RTL data path. It does not
> include a GNSS receiver or NMEA parser, does not use map data, and does not
> establish animal behaviour, cue efficacy, or road safety. The cue output is a
> 3.3 V logic signal, not an actuator drive.

## 1. What the demo shows

- A 10 Hz synthetic track approaches a fixed road segment at 1 m/s.
- A pipelined point-to-segment distance engine computes squared distance.
- A five-state risk FSM applies hysteresis, two-sample confirmation, a stale-fix
  watchdog, and a map-valid gate.
- A cue scheduler limits each cue to 0.5 s and enforces a 3 s cooldown.
- LEDs show state, validity, approach direction, cue/cooldown, fault, distance
  bar, and a 1 Hz heartbeat.
- `cue_out` on Pmod JA1 mirrors the cue LED for a scope or logic analyser.

The track loops every 20.1 s. A reset forces the FSM to `INVALID` and the cue
output inactive.

## 2. Hardware and tools

| Item | Requirement |
| --- | --- |
| Board | Digilent Basys 3, rev B, `xc7a35tcpg236-1` |
| Toolchain | Vivado 2024.2 (tested); other recent versions may work |
| Cable | USB cable for JTAG programming and power |
| Host | Linux, macOS, or Windows with Vivado installed |
| Optional | Oscilloscope or logic analyser on Pmod JA1 |
| Optional | 3.3 V logic-level driver stage for a non-aversive cue transducer |
| Not required | GNSS receiver, antenna, map data, or internet access |

Do not connect a speaker, motor, or other actuator directly to a Basys 3 pin.
See section 10.

## 3. Demo files

| Path | Purpose |
| --- | --- |
| `rtl/balat_basys3_top.v` | Top-level integration, LEDs, switches, watchdog |
| `rtl/trace_player.v` | 10 Hz trace address generator |
| `rtl/demo_trace_rom.v` | Generated 201-sample trace ROM |
| `rtl/road_geom.v` | Seven-stage pipelined point-to-segment squared distance |
| `rtl/risk_fsm.v` | INVALID/SAFE/CAUTION/DANGER/COOLDOWN FSM |
| `rtl/cue_scheduler.v` | Maximum-on-time and cooldown scheduler |
| `constraints/basys3_demo.xdc` | Basys 3 rev B pins for this demo |
| `scripts/golden_geometry.py` | Python reference model and trace generator |
| `scripts/build_basys3_demo.tcl` | Non-project Vivado build |
| `scripts/run_demo_sims.sh` | Icarus Verilog simulation suite |
| `tb/` | Unit and integration testbenches |
| `data/demo_trace.csv` | Human-readable trace |
| `data/demo_trace_expected.csv` | Distance and zone reference |

## 4. Build the bitstream

From the repository root:

```bash
vivado -mode batch -source scripts/build_basys3_demo.tcl
```

The script reads the RTL and XDC, runs synthesis, placement, routing, and
bitstream generation, then writes:

```text
build/basys3_demo/balat_basys3_demo.bit
build/basys3_demo/balat_basys3_demo_routed.dcp
build/basys3_demo/utilization.rpt
build/basys3_demo/timing_summary.rpt
```

Equivalent GUI flow:

1. Create a project for `xc7a35tcpg236-1`.
2. Add the RTL files listed in section 3.
3. Add `constraints/basys3_demo.xdc`.
4. Set `balat_basys3_top` as the top module.
5. Run synthesis, implementation, and `Generate Bitstream`.

## 5. Program the board

1. Connect the Basys 3 USB cable and power the board.
2. Open **Hardware Manager** and select **Open target > Auto connect**.
3. Select the `xc7a35t` device.
4. Select **Program device** and choose
   `build/basys3_demo/balat_basys3_demo.bit`.

Equivalent Vivado Tcl (adjust the bitstream path):

```tcl
open_hw_manager
connect_hw_server
open_hw_target
set dev [lindex [get_hw_devices] 0]
set_property PROGRAM.FILE {/absolute/path/to/balat_basys3_demo.bit} $dev
program_hw_devices $dev
refresh_hw_device $dev
```

## 6. Controls

| Control | Function |
| --- | --- |
| `SW0` | Run (up) / pause (down) the trace replay |
| `SW1` | Force stale/invalid input |
| `SW2` | Enable cue output |
| `SW3` | Force map fault |
| `BTNC` | Reset (active high) |

All switches are active high. `SW1` and `SW3` force `INVALID` and inhibit the
cue; this is the intended way to demonstrate fail-safe behaviour.

## 7. LED map

| LED | Meaning |
| --- | --- |
| `LED2..LED0` | Risk state as a 3-bit binary value: 0 INVALID, 1 SAFE, 2 CAUTION, 3 DANGER, 4 COOLDOWN |
| `LED3` | Input valid (not stale) |
| `LED4` | Approaching (distance decreasing) |
| `LED5` | Cue active |
| `LED6` | Cooldown active |
| `LED7` | Fault (stale or map invalid) |
| `LED8` | Distance <= 1 m |
| `LED9` | Distance <= 2 m |
| `LED10` | Distance <= 3 m |
| `LED11` | Distance <= 4 m |
| `LED12` | Distance <= 5 m |
| `LED13` | Distance <= 7 m |
| `LED14` | Distance <= 10 m |
| `LED15` | 1 Hz heartbeat |

The distance LEDs form a bar: more LEDs light as the track gets closer. The
state LEDs are binary, not one-hot; read `LED2` as the most significant bit.

## 8. Expected sequence

With `SW0` and `SW2` up, `SW1` and `SW3` down, after reset:

| Time (approx.) | Event |
| --- | --- |
| 0 s | `INVALID`; heartbeat starts |
| 0.1-0.2 s | First valid samples; state becomes `SAFE` |
| 5.1 s | Two samples at <= 5 m; state becomes `CAUTION` |
| 8.1 s | Two samples at <= 2 m; state becomes `DANGER` |
| 8.2 s | Cue asserts for 0.5 s (`LED5`, JA1 high) |
| 8.7 s | Cue ends; cooldown starts for 3 s (`LED6`) |
| 10.0 s | Track crosses the road; distance increases |
| 11.7 s | Cooldown ends; state returns to `SAFE` |
| 20.1 s | Track wraps and approaches again |

The exact sample at which a transition occurs depends on the two-sample
confirmation and the 10 Hz sample boundary. The demo thresholds are:

| Threshold | Value |
| --- | --- |
| CAUTION enter | 5.0 m |
| CAUTION exit | 6.0 m |
| DANGER enter | 2.0 m |
| DANGER exit | 3.0 m |
| Cue maximum on-time | 5 samples = 0.5 s |
| Cooldown | 30 samples = 3.0 s |
| Stale watchdog | 500 ms |

These are demonstration values, not calibrated safety limits.

## 9. Regenerate the trace and reference data

The trace and geometry vectors are generated from integer arithmetic that
mirrors `rtl/road_geom.v`:

```bash
python3 scripts/golden_geometry.py
```

This rewrites:

- `data/demo_trace.csv`
- `data/demo_trace_expected.csv`
- `rtl/demo_trace_rom.v`
- `tb/road_geom_vectors.txt`

The trace is synthetic: x = -1500 cm, y from +1000 cm to -1000 cm in 10 cm
steps, 201 samples. The road is the horizontal segment from (-2000, 0) to
(2000, 0) in centimetres. No OpenStreetMap data or GNSS data is used.

## 10. Simulation verification

Run the full demo simulation suite:

```bash
bash scripts/run_demo_sims.sh
```

Expected final line:

```text
All Basys 3 demo simulations passed.
```

The suite covers:

- `tb_road_geom.v` — generated vectors, inside/outside projection, diagonal and
  vertical roads, zero-length segment, and the documented coordinate-range
  corners;
- `tb_risk_fsm.v` — state transitions, two-sample confirmation, cooldown
  inhibit, stale input, and map fault;
- `tb_cue_scheduler.v` — maximum on-time, cooldown, early termination, enable
  gating, and reset;
- `tb_trace_player.v` — sample timing, wrap, and pause;
- `tb_balat_basys3_top.v` — end-to-end SAFE/CAUTION/DANGER/cue/cooldown, stale
  fail-safe, cue disable, and reset.

Open the integration waveform with:

```bash
gtkwave build/sim/tb_balat_basys3_top.vcd
```

## 11. Dashboard POC recording

The local dashboard can capture an explicitly started POC session. It is an
observability tool only: it cannot program the Basys 3, change switches, or
command `cue_out`.

```bash
python3 scripts/web_demo.py --serial /dev/ttyUSB1
```

This requires the separate HerdSync USB-UART bridge bitstream, described in
`docs/BASYS3_HERDSYNC_BRIDGE.md`, and `pyserial` on the host:

```bash
python3 -m pip install pyserial
vivado -mode batch -source scripts/build_basys3_herdsync.tcl
```

Program `build/basys3_herdsync/balat_basys3_herdsync.bit`, then open
`http://localhost:8888`, enter an optional session label, press **Start**, then
**Stop** and **Download CSV**. The dashboard decodes the same validated UART
records that the FPGA emits and records one row per received record (not per
browser poll) under `build/poc_records/`. Each record carries the same risk
state as the board LEDs, and the dashboard refreshes at 50 ms so a transition
appears within one refresh. Each row contains a UTC capture
timestamp, elapsed time, FPGA sequence, coordinates, FPGA risk state, quality,
battery, and risk-transition events.

For an offline UI-only rehearsal, omit `--serial` or use `--simulate`. It must
not be presented as a live GNSS, Bluetooth, or cue-control interface. The v1
UART record does not export cue-active, so verify cue state on `LED5` or JA1.
Basys 3 POC Bluetooth is not implemented; the USB-UART bridge is bench-only and
has no cue-control path. To keep captures elsewhere, set an explicit local
directory:

```bash
python3 scripts/web_demo.py --record-dir /path/to/poc_records
```

The dashboard uses OpenStreetMap base-map tiles (internet required) centered on
the local-map origin. It always draws the active fixed synthetic segment that
the current FPGA bitstream uses in red. When `data/road_segments.csv` and
`data/road_manifest.json` are present, it also draws their OSM-derived local
segments in light blue as a **reference-only** layer and displays source,
timestamp, and attribution. Those segments are not loaded into this FPGA
bitstream and must not be represented as the active on-board map.

## 12. Measured build results

Local build with Vivado 2024.2, part `xc7a35tcpg236-1`, Basys 3 rev B:

| Metric | Result |
| --- | --- |
| Worst negative slack (WNS) | +1.701 ns |
| Worst hold slack (WHS) | +0.100 ns |
| Timing constraints | Met |
| Slice LUTs | 885 (4.25%) |
| Slice registers | 628 (1.51%) |
| DSPs | 18 (20.00%) |
| Block RAM | 0 |
| Bitstream | `build/basys3_demo/balat_basys3_demo.bit` (about 542 KiB compressed) |

These are measured values from the local run, not guarantees for other tool
versions or board revisions. Re-run the build and keep the reports for any
milestone record.

## 13. Troubleshooting

| Symptom | Check |
| --- | --- |
| No LEDs at all | Board powered, bitstream programmed, `LED15` heartbeat blinking |
| Stuck in `INVALID` | `SW1` and `SW3` down, `SW0` up, `BTNC` released |
| No `CAUTION`/`DANGER` | Trace running; wait for the next 20.1 s loop |
| No cue | `SW2` up; cue only in `DANGER`; wait through the 3 s cooldown |
| Cue never stops | Reset; verify `LED5` is bounded to 0.5 s |
| Timing not met | Check Vivado version and the timing report; the geometry path is pipelined to 7 stages |
| Pin/placement error | Verify the board is rev B and compare with Digilent's `Basys-3-Master.xdc` |

## 14. Safety and limitations

- `cue_out` on JA1 is a 3.3 V logic-level signal. It must drive a suitable
  transistor/MOSFET or driver IC, never a speaker, motor, or other actuator
  directly.
- The demo uses a synthetic trace, not a GNSS receiver, not NMEA, and not a
  real map. It does not demonstrate position accuracy, map completeness, or
  field behaviour.
- The thresholds are demo values. Do not treat them as safety limits.
- Do not conduct animal trials based on this demo. Any animal work requires
  veterinary/animal-welfare review, a controlled enclosed area, positive
  conditioning, supervision, and a pre-approved protocol.
- Do not claim that BALAT prevents road accidents or reliably steers cattle.
  Those claims require controlled behavioural evidence and field validation.
- The next RTL milestones remain the UART/NMEA parser, recorded GNSS replay,
  and the full map-memory path; see `PLAN.md`.
