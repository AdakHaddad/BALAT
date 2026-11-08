# Basys 3 dashboard controlled NMEA demo

This is a separate FPGA image from the existing synthetic-trace and HerdSync
images. It lets one dashboard trace exercise the FPGA parser and risk pipeline:

```text
Dashboard replay → Python bridge → Basys 3 USB-UART RX → NMEA parser
                 → coordinate conversion → road geometry → risk FSM
Dashboard ← Python bridge ← Basys 3 USB-UART TX ← FPGA telemetry record
```

The dashboard sends checksummed GGA/RMC sentences from `data/demo_trace.csv`.
The FPGA consumes RMC, converts it relative to the existing BALAT origin, and
assesses distance to its fixed demonstration segment from (-2000, 0) to
(2000, 0) cm. It emits the existing HerdSync record format so the dashboard
shows FPGA-originated coordinates and risk state. The reference OSM map remains
display-only and is not loaded into this bitstream.

## Build and program

From the repository root, build with Vivado 2024.2 (or a compatible release):

```bash
vivado -mode batch -source scripts/build_basys3_dashboard.tcl
```

The image and reports are written to `build/basys3_dashboard/`. Open the
generated `.bit` file in Vivado Hardware Manager and program the Basys 3. This
uses top `balat_basys3_dashboard_top` and constraints
`constraints/basys3_dashboard.xdc`; it does not replace either existing demo
image.

Build completed with Vivado 2024.2 for `xc7a35tcpg236-1`: routed WNS is
+0.193 ns at 100 MHz, with 0 setup violations, 0 DRC errors, 2,387 LUTs,
2,268 flip-flops, and 32 DSPs. These are tool reports; physical FPGA behavior
still needs to be checked on the board.

## Run the dashboard

Connect the Basys 3 micro-USB port to the laptop and find its USB-UART device
(for example `/dev/ttyUSB0` or `COM4`). Install Python dependencies if needed,
then run:

```bash
python3 -m pip install pyserial
python3 scripts/web_demo.py --basys3-nmea-serial /dev/ttyUSB0
```

On Windows, replace the port with e.g. `COM4`. Open `http://localhost:8888`.
The input replay controls appear after the USB-UART connection opens. Start, pause,
reset, stop, and interval changes act on the single local replay and are sent
as checksummed NMEA through the FPGA UART receiver. FPGA record data returns
over the same full-duplex UART connection.

Use the dashboard run command with either `--esp32-serial PORT` or
`--basys3-nmea-serial PORT`, one target at a time. Run each target in turn to
compare decisions from the same source trace. Do not start two server processes
against the same trace/device at the same time.

## Board controls and output boundary

| Control | Function |
|---|---|
| SW1 | Force invalid/stale input |
| SW2 | Physical FPGA cue scheduler enable |
| SW3 | Force map invalid |
| BTNC | Reset |
| LED[2:0] | INVALID / SAFE / CAUTION / DANGER / COOLDOWN |
| LED3 | Accepted position and non-stale input |
| LED4 | Approaching indicator |
| LED5 | Cue active |
| JA1 | 3.3 V logic-level cue observation |

The dashboard only selects replay fixes and reads records. It cannot enable
the FPGA cue; SW2 is a physical board control. JA1 is not a speaker/motor
output and must not be connected directly to an actuator. The FPGA JA1 signal
and ESP32 PCB driver nets are not electrically combined; use one hardware
controller at a time unless a separately reviewed selector/isolation circuit
is installed. The PCB v1 power-path/DRC hold remains in effect.

## Contract and limits

- UART is 115200 baud, 8N1, through the Basys 3 FTDI bridge (RsRx B18, RsTx A18).
- The RTL parser accepts checksummed GPRMC/GNRMC sentences and rejects void or
  checksum-invalid fixes. No live GNSS receiver is used in this dashboard mode.
- The FPGA uses the existing coordinate origin and one fixed horizontal segment.
- The sample watchdog forces INVALID after 500 ms without a valid position.
- The cue scheduler uses the RTL defaults: at most five 10 Hz sample ticks on,
  followed by 30 ticks of cooldown. The 3-second cooldown is the inherited RTL
  demo value, not the ESP32's 30-second bench setting.
- The dashboard cannot report the FPGA cue pin as telemetry because the
  existing record format does not include cue-active; check LED5 or JA1.
- This proves a dashboard-to-FPGA data path and FPGA-originated risk telemetry.
  It is not map completeness, GNSS performance, cue effectiveness, or animal
  safety evidence.
