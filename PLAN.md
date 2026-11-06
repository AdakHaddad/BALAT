# BALAT RTL Project Plan

## Milestone 0 — Scope freeze and toolchain
- [x] Confirm Basys 3 board and FPGA part.
- [x] Record Vivado version and project settings.
- [x] Select Verilog/SystemVerilog standard.
- [x] Choose GNSS receiver and supported NMEA sentence(s).
- [x] Define local coordinate system, fixed-point scales, and map record format.
- [x] Define initial MCI connector and external driver assumptions.
- Exit: interface contracts reviewed; no ambiguous widths or units.

## Milestone 1 — Simulation-first foundations
- [x] Create clock/reset testbench.
- [x] Implement UART RX.
- [x] Implement NMEA parser for selected sentence(s).
- [x] Create Python golden-model test vectors.
- [x] Validate checksum, fix validity, coordinates, and stale-fix handling.
- Exit: parser passes valid and invalid vector suite.

## Milestone 2 — Road-map representation
- [x] Create OSM extraction workflow for a chosen pilot bounding box.
- [x] Convert road geometries into local metric coordinates.
- [x] Simplify and segment road polylines.
- [x] Add manual correction mechanism for missing/private roads.
- [x] Generate BRAM initialization file and manifest.
- [x] Test map loader/ROM addressing.
- Exit: generated map records match source geometry and are traceable to map version/date.

## Milestone 3 — Spatial engine
- [x] Implement point-to-segment projection.
- [x] Implement clamping and degenerate-segment handling.
- [x] Implement squared-distance threshold comparison.
- [x] Implement nearest-segment selection.
- [x] Compare against Python reference over randomized and edge-case vectors.
- Exit: bounded error and no overflow for documented coordinate range.

## Milestone 4 — Approach prediction and risk
- [x] Estimate velocity from successive valid fixes.
- [x] Project velocity toward closest road point.
- [x] Add GNSS uncertainty margin.
- [x] Implement INVALID/SAFE/CAUTION/DANGER/COOLDOWN FSM.
- [x] Add hysteresis, debounce, and stale-data watchdog.
- Exit: all risk transitions covered by testbench.

## Milestone 5 — Modular cue output
- [x] Define MCI connector and pin assignment.
- [x] Implement CUE_EN and optional PWM.
- [x] Implement maximum-on-time and cooldown.
- [ ] Build safe external driver for selected transducer.
- [ ] Test with LED/dummy load before actuator.
- [x] Test interchangeable output modules without changing risk engine.
- Exit: cue output is bounded, reset-safe, and electrically compatible.

## Milestone 6 — Basys 3 integration
- [x] Integrate modules at top level (synthetic-trace demo).
- [x] Add XDC pin constraints.
- [x] Add LED debug display and a UART debug bridge; GNSS UART input still pending.
- [x] Run synthesis, implementation, timing, and utilization reports.
- [x] Demonstrate recorded GNSS trace replay (synthetic local-coordinate replay done; NMEA/GNSS pending).
- Exit: repeatable FPGA demo with saved reports and test logs.

Demo status: see `docs/BASYS3_DEMO.md`. The Vivado 2024.2 build met timing
(WNS +1.701 ns) at 885 LUTs, 628 flip-flops, and 18 DSPs. This is a bench demo
with a synthetic trace; it is not GNSS, map, or animal validation.

The separate Basys 3 USB-UART bridge build met timing (WNS +2.451 ns) at
1248 LUTs, 1328 flip-flops, and 18 DSPs. On hardware it streamed 320 records
and a 1200-frame/120 s soak with no CRC errors, sequence gaps, or resets. See
`docs/BASYS3_HERDSYNC_BRIDGE.md`. These are bench results, not field measurements.

## Parallel ESP32-C3 bench prototype
- [x] Implement portable C contracts for NMEA, fixed-point coordinates, map checksum, geometry, trajectory, risk FSM, bounded cue, logging, and replay in `esp32/`.
- [x] Add host regression for RTL geometry vectors, parser failures, map corruption, thresholds, cue bounds, and synthetic replay.
- [x] Install ESP-IDF v5.5.6 ESP32-C3 tools and build the firmware binary.
- [ ] Flash and run the serial/replay demo on an ESP32-C3 board; no board is currently attached.
- [ ] Measure GPIO cue timing with a protected dummy load before any actuator connection.

## Milestone 7 — Controlled validation
- [ ] Verify map completeness against site survey.
- [ ] Measure GNSS error in actual collar mounting positions.
- [ ] Test road-distance/risk logic using recorded tracks.
- [ ] Conduct supervised cue evaluation only after animal-welfare review and training protocol approval.
- [ ] Compare cue response across individuals; record non-response and adverse signs.
- Exit: report limitations and evidence; do not claim safety effectiveness without data.

## Milestone 8 — ASIC feasibility (future)
- [ ] Freeze synthesizable RTL and test suite.
- [ ] Evaluate ASIC synthesis flow and target process.
- [ ] Estimate area, timing, and power with realistic constraints.
- [ ] Compare FPGA and ASIC architecture trade-offs.
- [ ] Decide whether a processor/MCU is still unnecessary.
- Exit: evidence-based ASIC feasibility report.

## Post-v0.1 — HerdSync-DTN POC (separate track)
This track does not change the v0.1 safety path or cue interface. See ADR-007
and `docs/HERDSYNC_POC.md`.

- [x] Phase 0: software store-carry-forward, version-vector, phone-mule, and
  security-rejection simulation.
- [x] Phase 0: unit and scenario tests pass.
- [ ] Phase 1: two COTS BLE boards exchange signed records and a phone reads
  both.
- [ ] Phase 2: three-board multi-hop, partition, and rejoin demonstration.
- [x] Phase 3a: Basys 3 USB-UART record bridge and PC host collector; status
  display only, with no path to the cue output. Simulations, build, record
  streaming, and peer-summary indication pass on physical hardware.
- [ ] Phase 3b: Basys 3 UART link to a COTS BLE module; neighbor status display
  only, with no path to the cue output.
- [ ] Phase 4: supervised, welfare-reviewed bench/field prototype.
- Exit: measured radio, range, power, and latency results; a security review;
  and an explicit decision on whether HerdSync-DTN proceeds to a collar
  product.
