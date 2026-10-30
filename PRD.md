# Product Requirements Document — BALAT RTL v0.1

## 1. Product summary

BALAT is an autonomous, map-aware livestock wearable concept. It uses GNSS position and locally stored road geometry to estimate whether an animal is approaching a mapped road, then issues a configurable cue through an interchangeable external cue module.

The v0.1 objective is to prove the digital hardware decision pipeline on a Basys 3 FPGA. It is not a production collar and must not be relied upon as the sole road-safety barrier.

## 2. Problem statement

Livestock may approach or enter roads bordering or crossing grazing areas. A conventional tracker reports position but does not necessarily make a local, timely decision or provide a trained response cue.

BALAT explores whether a low-complexity autonomous wearable can:
- know its position;
- compare that position with locally stored road geometry;
- estimate approach risk before road entry;
- command a selected cue module;
- continue core operation without internet or a fixed base station.

## 3. Goals

### v0.1 goals
- Parse GNSS NMEA position and validity information from UART.
- Consume a preprocessed, bounded list of road segments stored locally.
- Calculate animal-to-road distance in a local metric coordinate frame.
- Estimate whether the animal is moving toward the relevant road.
- Apply configurable risk thresholds with hysteresis and stale-fix handling.
- Generate a simple, bounded cue command using a modular output interface.
- Demonstrate the complete pipeline on Basys 3.
- Verify behavior in simulation before hardware testing.

### Non-goals
- No SoC, CPU, MicroBlaze, or RISC-V core in v0.1.
- No live internet, cellular, LoRa, BLE, or gateway dependency.
- No onboard camera or road-vision model.
- No animal movement classification.
- No claim that a sound or vibration inherently tells cattle which direction to move.
- No electric shock or painful stimulus.
- No autonomous operation beside live traffic during early trials.
- No claim of production-grade GNSS accuracy or battery life from Basys 3 results.

## 4. Users and operating context

Primary operator: farmer or livestock manager who configures a grazing area and verifies map data.

Wearable: one device attached to an animal, with GNSS receiver and external cue transducer/driver.

Environment: mixed rural/agricultural land, potentially with multiple road segments and entrances. Map completeness and GNSS reception may vary.

## 5. Functional requirements

| ID | Requirement | Priority |
|---|---|---|
| FR-01 | Accept GNSS serial data through a defined UART interface. | Must |
| FR-02 | Reject invalid, incomplete, or stale position fixes. | Must |
| FR-03 | Expose position, fix-valid, and fix-age signals/registers. | Must |
| FR-04 | Read a finite set of road segments from local memory. | Must |
| FR-05 | Calculate distance to candidate road segments in meters or a documented fixed-point scale. | Must |
| FR-06 | Estimate velocity component toward the road from successive valid fixes. | Must |
| FR-07 | Avoid risk escalation when the animal is moving away or parallel, subject to uncertainty. | Must |
| FR-08 | Produce SAFE, CAUTION, and DANGER states using configurable thresholds. | Must |
| FR-09 | Apply hysteresis, debounce, and minimum cue interval to prevent chatter/repeated cues. | Must |
| FR-10 | Drive an output-only cue interface with enable and optional PWM/control signal. | Must |
| FR-11 | Provide debug/status outputs for LEDs or UART during prototype testing. | Should |
| FR-12 | Support changing the cue module without changing road-risk RTL. | Should |
| FR-13 | Detect configuration/map checksum or version mismatch in a later revision. | Could |

## 6. Non-functional requirements

- Synthesizable RTL compatible with the selected Vivado version and Basys 3 FPGA.
- Explicit clock-domain handling for asynchronous UART input.
- Reset behavior places cue outputs in the inactive state.
- Arithmetic widths, signedness, coordinate scaling, and overflow behavior are documented.
- No cue is generated from invalid or stale GNSS data.
- Cue output has a hard maximum duration and enforced quiet interval.
- Testbench coverage includes invalid fixes, map edge cases, direction changes, and arithmetic boundaries.
- Hardware resource use and timing are recorded from Vivado reports.

## 7. Initial measurable acceptance criteria

These are engineering targets for the demonstrator, not field-proven safety thresholds.

1. GNSS parser correctly parses the selected supported sentence format for all supplied valid test vectors.
2. Invalid checksum, no-fix status, malformed sentence, and stale input do not update the accepted position.
3. Geometry engine matches a software reference within the chosen fixed-point tolerance for the full test vector set.
4. Trajectory estimator distinguishes toward, away, and near-parallel synthetic trajectories within documented tolerances.
5. Risk FSM transitions correctly for all state/threshold/hysteresis test cases.
6. Cue output remains inactive on reset, invalid fix, stale fix, or disabled configuration.
7. Cue duration and repetition limits are enforced in simulation and on FPGA.
8. Vivado implementation completes with timing constraints met at the chosen clock.
9. FPGA demo can replay a documented sequence of GNSS positions and visibly indicate risk state and cue output.

## 8. Open questions

- Which GNSS receiver and NMEA sentences will be used?
- What is the intended farm boundary and road-data source for the pilot?
- What road classes should be considered hazardous?
- How will missing/private roads be added and map data checked?
- What GNSS accuracy and update rate are available under collar mounting?
- Which cue transducers will be evaluated?
- What training protocol and animal-welfare review are required?
- What response latency and warning distance are appropriate for the actual cattle, terrain, and speed?
- What local radio/frequency regulations apply if communications are added later?

## 9. Product success definition

v0.1 succeeds when the FPGA reliably demonstrates map-based road proximity and approach-risk logic and safely commands a replaceable cue output under controlled bench conditions. It does not succeed merely because a buzzer sounds, and it does not establish that cattle will respond effectively until supervised behavioral trials are completed.
