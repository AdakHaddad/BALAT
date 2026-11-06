# BALAT ESP32-C3 bench prototype

This is an ESP-IDF v5.x bench firmware target with a portable C decision core.
It has been built with ESP-IDF v5.5.6 for `esp32c3`.
It mirrors the observable v0.1 RTL contracts; it does not replace the FPGA
architecture or establish animal-guidance or road-safety performance.

## Safety boundary

- GPIO 6 and GPIO 7 are output-only inputs to protected external buzzer/motor
  drivers. Never connect a motor or speaker directly to these pins.
- Reset, an invalid/stale/uncertain/corrupt fix, map failure, an out-of-range
  coordinate, a trajectory fault, or manual disable force cue output off.
- A physical active-high `CUE_ENABLE` switch on GPIO 1 is the sole cue-enable
  authority. USB commands, replay, NMEA, and any future HerdSync/telemetry path
  cannot enable or extend a cue.
- GPIO 0 is an active-low manual disable with pull-up. Defaults avoid ESP32-C3
  strapping GPIO 2, 8, and 9.

| Signal | Default GPIO | Direction |
|---|---:|---|
| GNSS RX / TX | 4 / 5 | UART1 input / output |
| Protected buzzer / motor driver enable | 6 / 7 | output only |
| Invalid / caution / safe LED | 10 / 3 / disabled | output |
| Manual disable | 0 | input, active low |
| Physical cue enable | 1 | input, active high |

All defaults are Kconfig-configurable in `main/Kconfig.projbuild`. GPIO20/21
are reserved for the default UART0 USB serial console. The safe LED is disabled
by default; the invalid and caution LEDs remain available. Select one cue module
in Kconfig so only its protected driver-enable output is activated.

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

USB serial commands are `HELP`, `STATUS`, `MAP`, `REPLAY START|STOP|RESET`,
`FIX <x_cm> <y_cm>`, `NMEA <sentence>`, `FAULT NONE|STALE|MAP|CORRUPT`,
`CLEAR`, and `RESET`. `FIX` and `REPLAY` are bench/replay facilities, not map
or cue authorization paths.

Start with no actuator connected, then a protected dummy load only. Follow
`docs/MICROCONTROLLER_PROTOTYPE.md` before any outdoor or animal-related work.
