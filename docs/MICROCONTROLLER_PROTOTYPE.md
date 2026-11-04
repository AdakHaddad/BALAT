# BALAT Microcontroller Prototype Runbook

This runbook defines a parallel prototype for validating GNSS, map, logging,
power, and cue behavior on a microcontroller when the FPGA is only available in
the laboratory. It does not replace the FPGA architecture decision and does not
make animal-guidance claims.

## 1. Why build an MCU prototype

An MCU prototype can answer questions that the Basys 3 cannot answer well:

- GNSS reception with a collar-mounted antenna;
- battery and sleep behavior;
- local map loading and updates;
- field logging and replay;
- enclosure and wiring;
- optional BLE or USB telemetry;
- longer-duration operation.

The FPGA remains the deterministic RTL reference for the v0.1 research path.
The MCU should implement the same observable contracts so that traces and
expected results can be compared across platforms.

## 2. Recommended architecture

```text
GNSS UART
  -> MCU UART/DMA
  -> parser and fix-quality gate
  -> local coordinate conversion
  -> local road map
  -> nearest segment and approach estimator
  -> risk state machine
  -> cue scheduler
  -> protected driver / dummy load
  -> local log and optional telemetry
```

Keep telemetry and HerdSync separate from the cue decision. A lost radio,
malformed peer packet, or phone command must not create or extend a cue.

## 3. Hardware selection

Choose a board with:

- a documented 3.3 V UART;
- hardware timers;
- non-volatile storage or an external flash/SD option;
- watchdog and brownout reset;
- enough RAM for the selected map and log buffer;
- measured low-power modes;
- accessible debug interface.

Practical evaluation options:

- an STM32L4 or STM32U5 development board for low-power testing;
- an nRF52840 board if BLE is an explicit near-term experiment;
- an ESP32-class board only when its power and radio trade-offs are acceptable.

Do not choose a board solely because it has Wi-Fi or BLE. First measure GNSS,
compute, storage, and sleep current for the intended duty cycle.

## 4. MCU safety contract

The MCU implementation must preserve these rules:

1. Reset, watchdog, brownout, boot failure, and configuration failure leave the
   cue driver inactive.
2. Invalid, stale, uncertain, or checksum-failed fixes cannot create a cue.
3. A cue has a hard maximum duration and mandatory quiet interval.
4. A missing map, invalid map checksum, or out-of-range coordinate disables
   road-based cueing.
5. The radio, USB, BLE, phone, cloud, and HerdSync paths cannot authorize a cue.
6. Configuration updates are versioned, validated, and rejected atomically.
7. Manual disable remains available.
8. The device logs why a cue was requested and which fix/map version supported
   the decision.

The cue output must drive only a protected external driver. Never drive a motor
or speaker directly from a GPIO pin.

## 5. Software modules

Implement small modules with host tests:

```text
gnss_uart
nmea_parser
fix_quality_gate
coordinate_transform
map_store
nearest_segment
trajectory_estimator
risk_fsm
cue_scheduler
event_log
watchdog/fault_manager
telemetry_adapter
```

Use integer or fixed-point arithmetic where comparison with the FPGA is
important. If floating point is used for exploration, retain a fixed-point
reference path and document every conversion and rounding rule.

## 6. Data contracts

Every accepted fix should contain:

```text
fix_seq
utc_time
latitude/longitude
local_x/local_y
fix_valid
quality
uncertainty estimate
received_at
```

Every geometry result should contain:

```text
map_version
segment_id
closest_x/closest_y
distance_squared
road_buffer
geometry_valid
```

Every risk/cue event should contain:

```text
fix_seq
risk_state
fault_reason
approaching
cue_requested
cue_started
cue_stopped
cue_duration
```

This makes MCU logs comparable with FPGA simulation and prevents a dashboard
from hiding invalid or stale states.

## 7. Development sequence

### Stage 1 — host-only reference

- Parse recorded NMEA files on the host.
- Compare against `scripts/golden_nmea.py` and the geometry reference.
- Add malformed, stale, jump, and uncertainty cases.
- Produce a CSV/JSON event log.

### Stage 2 — MCU GNSS bench

- Connect the GNSS receiver to the MCU UART.
- Log raw NMEA and accepted fixes simultaneously.
- Compare MCU coordinates with the host reference.
- Measure fix latency, parser errors, and current draw.
- Keep cue output disabled.

### Stage 3 — MCU synthetic replay

- Feed the existing synthetic trace through the MCU.
- Compare risk state, distance, approach, and cue timing against expected data.
- Repeat after reset, watchdog recovery, and map reload.

### Stage 4 — MCU real-map bench

- Load one documented local map.
- Verify map checksum, version, record count, and coordinate origin.
- Test manual road correction and rollback.
- Use a logic analyser or GPIO timestamp to measure decision latency.

### Stage 5 — protected dummy-load test

- Connect an LED, resistor load, or protected driver input.
- Verify reset, invalid, stale, map-fault, disable, maximum-on, and cooldown
  behavior.
- Run a multi-hour bench test with logged brownouts, resets, and watchdogs.

### Stage 6 — controlled non-animal outdoor test

- Walk or carry the device in a controlled area away from traffic and animals.
- Collect GNSS traces near trees, buildings, and open sky.
- Compare false approach and missed approach behavior.
- Do not infer animal behavior from human-carried traces.

## 8. Power and wearable measurements

Measure separately:

- GNSS acquisition current;
- GNSS tracking current;
- MCU active current;
- MCU sleep current;
- map read current;
- cue-driver current;
- telemetry/radio current;
- battery voltage under load;
- reset/brownout behavior;
- estimated runtime for the actual duty cycle.

Record antenna placement, collar orientation, enclosure, temperature, and
whether logging or radio was enabled. Do not claim battery life from a
development board measurement without accounting for regulators, LEDs, USB,
and debug interfaces.

## 9. Verification plan

Run the repository RTL and POC tests as regression references:

```bash
bash scripts/run_demo_sims.sh
bash scripts/run_herdsync_sims.sh
python3 -m unittest discover -s poc/tests -t . -v
```

Add MCU tests for:

- parser checksum and malformed input;
- hemisphere and coordinate boundaries;
- time gaps and stale fixes;
- uncertainty and quality thresholds;
- implausible jumps;
- zero-length and out-of-range map segments;
- map version/checksum failure;
- signed arithmetic and overflow;
- exact risk thresholds and hysteresis;
- cue maximum duration and cooldown;
- watchdog, brownout, reset, and manual disable;
- telemetry loss and malformed HerdSync frames.

The MCU and FPGA must consume the same trace files and produce comparable
event logs. Differences require an explicit documented rounding or timing
explanation.

## 10. HerdSync placement

HerdSync can be added to the MCU prototype as telemetry after the local safety
path is stable:

```text
local risk/cue path  ---> event log
                         |
                         +--> optional signed telemetry ---> BLE/phone
```

It must not be used for:

- remote cue authorization;
- map updates without local validation;
- clearing a stale/fault state;
- changing risk thresholds in the field without authenticated configuration;
- replacing local GNSS validity or map checks.

The current HerdSync POC and Basys 3 bridge are not production-secure. Treat
them as protocol experiments until device identity, key provisioning, replay
protection, rotation, and radio behavior are validated.

## 11. MCU prototype exit criteria

The MCU prototype may be called a **field-data prototype** only when:

- real GNSS traces are logged from the intended mounting configuration;
- map conversion and manual corrections are reproducible;
- invalid/stale/uncertain fixes inhibit cueing;
- reset/watchdog/brownout states inhibit cueing;
- cue timing is measured with a protected dummy load;
- battery and thermal behavior are measured;
- logs are sufficient to reconstruct every risk and cue decision;
- no animal or road-safety claim is made from the device alone.

An approved welfare protocol, trained supervision, and a controlled enclosed
test area are required before any cue is evaluated with animals.

## 12. FPGA and MCU division of labor

| Question | FPGA prototype | MCU prototype |
|---|---|---|
| RTL determinism and fixed-point timing | Primary | Reference comparison |
| GNSS parser and map integration | Next lab milestone | Primary field-data path |
| Power and wearable packaging | Not representative | Primary |
| Road geometry correctness | Reference implementation | Cross-check and deployment |
| Cue safety limits | Must be proven | Must independently be proven |
| BLE/HerdSync | Separate bridge/POC | Optional telemetry layer |
| Animal guidance efficacy | Neither proves it | Neither proves it |

Use the MCU to collect evidence and expose deployment problems. Use the FPGA
to keep the bounded digital decision path inspectable and reproducible.
