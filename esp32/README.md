# BALAT ESP32-C3 bench prototype

This is an ESP-IDF v5.x firmware target for the BALAT-P platform and its
portable C decision core. The default pin profile matches the current
`BALAT_PCB_v1` main board signal nets.
It mirrors the observable v0.1 RTL contracts; it does not replace the FPGA
architecture or establish animal-guidance or road-safety performance.

For assembly and dashboard operation, see
[`../docs/ESP32_ASSEMBLY_DEMO.md`](../docs/ESP32_ASSEMBLY_DEMO.md). Signal
mapping now matches the main PCB. The PCB power path is still marked HOLD;
follow the bench-power restrictions in the guide and
[`../docs/PCB_LAYOUT_REVIEW_2026-11-08.md`](../docs/PCB_LAYOUT_REVIEW_2026-11-08.md).

## Safety boundary

- GPIO 3 and GPIO 4 drive only the PCB's existing protected buzzer and motor
  transistor stages. They are never direct motor/speaker outputs.
- Reset, an invalid/stale/uncertain/corrupt fix, map failure, an out-of-range
  coordinate, a trajectory fault, or manual disable force cue output off.
- The PCB report button on GPIO 6 is used as a **hold-to-enable** input: the
  operator must hold it to permit a bounded cue, and release immediately
  disables outputs. Dashboard commands and mock GPS never arm a cue.
- GPIO 5 controls GPS power through the PCB PNP switch (active low). GPIO 20 is
  GPS UART RX. The console uses native USB Serial/JTAG to avoid sharing GPIO20
  with the PCB GPS TX net. Defaults avoid ESP32-C3 strapping GPIO 2, 8, and 9.

| Signal | Default GPIO | Direction |
|---|---:|---|
| PCB buzzer driver / motor driver | 3 / 4 | output only, bounded cue |
| GPS enable | 5 | output, active low |
| PCB button / cue enable | 6 | input, hold low to arm |
| Red status LED (standalone bench) | 7 | output, active high |
| Green status LED / PCB D3 | 10 | output, active high |
| Yellow status LED (standalone bench) | 21 | output, active high |
| GPS TX → ESP32 UART RX | 20 | UART1 input |
| USB console | native USB Serial/JTAG | commands and logs |

Defaults are Kconfig-configurable in `main/Kconfig.projbuild`. During a bounded
cue the firmware activates both protected PCB stages. The standalone
breadboard's LEDs indicate green=SAFE, yellow=CAUTION/COOLDOWN, red=DANGER, and
blinking red=INVALID. GPIO7 and GPIO21 are not connected on PCB v1; its fitted
GPIO10 LED shows green only for SAFE. Use the breadboard for full three-color
status.

## Runtime contract

- NMEA: checked `GPRMC`, `GNRMC`, `GPGGA`, and `GNGGA`; only accepted RMC fixes
  enter geometry. With the default configuration, an RMC fix is rejected unless
  a fresh GGA quality/HDOP record is available.
- Coordinates: the same origin and fixed-point conversion as RTL
  (`lat=-338250000`, `lon=186500000`, `cos_lat_q14=13611`).
- Map: generated from `data/road_segments.csv` and `data/road_manifest.json`.
  The C fixture validates FNV-1a checksum, version, segment count, coordinate
  range, Q14 direction, and duplicate IDs before use.
- Risk: `INVALID`, `SAFE`, `CAUTION`, `DANGER`, `COOLDOWN`; thresholds are
  500/600 cm and 200/300 cm with two qualifying samples.
- Cue: maximum 500 ms on and a mandatory 30,000 ms quiet interval. This is a
  deliberate bench safety limit; it is longer than the RTL demo's 3-second
  cooldown.
- Logging: every state/cue event is emitted as reconstructable CSV on USB
  serial. The log includes sequence numbers, map result, approach, faults, and
  cue timing.

## Build and bench commands

Install the ESP32-C3 target tools using Espressif's [Linux/macOS setup
guide](https://docs.espressif.com/projects/esp-idf/en/v5.5.6/esp32c3/get-started/linux-macos-setup.html).
Then source the environment and build:

```bash
cd esp32
. /path/to/esp-idf/export.sh
idf.py set-target esp32c3
idf.py build
```

Connect the board and identify its serial device before flashing:

```bash
idf.py -p /dev/ttyUSB0 flash monitor
```

Replace `/dev/ttyUSB0` with the actual port (`/dev/ttyACM0` is also common).
No ESP32-C3 board was connected during this build, so flash and live serial
demonstration still need a board.

Run the portable host regression without ESP-IDF:

```bash
python3 esp32/tools/gen_fixtures.py
make -C esp32/test clean all
(cd esp32/test && ./test_balat_core)
```

Regenerate fixtures whenever either source CSV/JSON changes. The generator
uses the same little-endian FNV-1a field order as `balat_map_checksum`.

USB serial commands include `MOCK START|PAUSE|RESET|STOP`. Dashboard trace
replay sends checksummed mock NMEA through this USB console; a manually chosen
map point sends interpolated synthetic `FIX <x_cm> <y_cm>` coordinates toward
the selected location at up to 5 m/s. The speed cap smooths this demo input;
firmware fix, stale, and risk checks remain enabled. Both run with the GPS
module off and use the firmware map/risk pipeline.
`NMEA <sentence>` is accepted only after `MOCK START`. `STATUS`, `MAP`,
`REPLAY`, `FIX`, `FAULT`, `CLEAR`, and `RESET` remain bench tools and cannot
arm outputs.

Start with no actuator connected, then a protected dummy load only. Follow
`docs/MICROCONTROLLER_PROTOTYPE.md` before any outdoor or animal-related work.
