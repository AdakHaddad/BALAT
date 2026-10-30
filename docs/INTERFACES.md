# Interface Contracts — BALAT RTL v0.1

## 1. GNSS UART input

Initial proposal:
- UART RX, 3.3 V logic.
- Baud rate configurable at build time; choose based on receiver configuration.
- Parser supports only explicitly selected NMEA sentence(s) initially.
- Validate NMEA checksum and fix validity.
- Publish accepted latitude, longitude, timestamp, fix-valid, and quality/accuracy metadata where available.

Do not assume every receiver emits identical sentence sets or that NMEA quality fields provide a reliable statistical error bound. Confirm the selected receiver datasheet.

## 2. Coordinate and map record contract

All runtime geometry should use a local projected metric coordinate system.

Each road segment record should include:
- segment_id;
- x1, y1;
- x2, y2;
- road_class;
- configured safety buffer;
- optional confidence/source flags.

The generated map manifest must include:
- source (e.g. OpenStreetMap);
- extraction date;
- bounding box;
- coordinate reference system and origin;
- simplification tolerance;
- segment count;
- coordinate scale and signed width;
- checksum/version.

## 3. MCI — Modular Cue Interface v0.1

Recommended minimum logical signals:
- `CUE_EN`: output, active-high enable/trigger.
- `CUE_PWM`: optional output for supported modules.
- `GND`: common reference.
- `VCC_MODULE`: protected module power rail supplied by external power circuitry.

Optional future signals:
- serial command interface;
- module identification;
- busy/fault feedback.

The first revision does not require cue-module input signals. The cue module can simply receive a command and produce an output.

### Electrical rules
- FPGA I/O is 3.3 V logic; do not connect 5 V signals directly.
- FPGA I/O pins are not actuator power supplies.
- Use a dedicated transistor/MOSFET or driver IC appropriate to the load.
- Provide current limiting, protection, decoupling, and connector keying.
- Keep actuator current return paths from disturbing GNSS/RF/logic ground.
- Verify Basys 3 Pmod pin capabilities and constraints before wiring.

## 4. Cue command abstraction

The core should output an abstract cue request:
- cue_enable;
- cue_pattern or cue_mode;
- optional intensity;
- requested duration.

The MCI adapter translates the abstract request into physical pins. The risk engine must not know whether the attached module is a buzzer or vibration driver.

## 5. Debug interface

Recommended prototype observability:
- LEDs: current risk state, fix-valid, cue-active, fault.
- UART TX: position, nearest road segment, distance, approach speed, risk state, cue events.
- Buttons/switches: reset, test mode, optional scenario selection.

## 6. Demo-specific notes

The current synthetic-trace Basys 3 demo (`docs/BASYS3_DEMO.md`) adds two
implementation details that do not change the production contracts above:

- The demo road record also stores a precomputed Q14 unit direction for each
  segment. This is derived offline from the endpoints and avoids a runtime
  divider. The production map contract still requires endpoints and a manifest.
- `cue_out` is a 3.3 V logic-level observation signal on Pmod JA1. It is not an
  actuator drive and must be connected only to a suitable driver stage or test
  instrument.
