# BALAT RTL Project Plan

## Milestone 0 — Scope freeze and toolchain
- [ ] Confirm Basys 3 board and FPGA part.
- [ ] Record Vivado version and project settings.
- [ ] Select Verilog/SystemVerilog standard.
- [ ] Choose GNSS receiver and supported NMEA sentence(s).
- [ ] Define local coordinate system, fixed-point scales, and map record format.
- [ ] Define initial MCI connector and external driver assumptions.
- Exit: interface contracts reviewed; no ambiguous widths or units.

## Milestone 1 — Simulation-first foundations
- [ ] Create clock/reset testbench.
- [ ] Implement UART RX.
- [ ] Implement NMEA parser for selected sentence(s).
- [ ] Validate checksum, fix validity, coordinates, and stale-fix handling.
- [ ] Create Python golden-model test vectors.
- Exit: parser passes valid and invalid vector suite.

## Milestone 2 — Road-map representation
- [ ] Create OSM extraction workflow for a chosen pilot bounding box.
- [ ] Convert road geometries into local metric coordinates.
- [ ] Simplify and segment road polylines.
- [ ] Add manual correction mechanism for missing/private roads.
- [ ] Generate BRAM initialization file and manifest.
- [ ] Test map loader/ROM addressing.
- Exit: generated map records match source geometry and are traceable to map version/date.

## Milestone 3 — Spatial engine
- [ ] Implement point-to-segment projection.
- [ ] Implement clamping and degenerate-segment handling.
- [ ] Implement squared-distance threshold comparison.
- [ ] Implement nearest-segment selection.
- [ ] Compare against Python reference over randomized and edge-case vectors.
- Exit: bounded error and no overflow for documented coordinate range.

## Milestone 4 — Approach prediction and risk
- [ ] Estimate velocity from successive valid fixes.
- [ ] Project velocity toward closest road point.
- [ ] Add GNSS uncertainty margin.
- [ ] Implement INVALID/SAFE/CAUTION/DANGER/COOLDOWN FSM.
- [ ] Add hysteresis, debounce, and stale-data watchdog.
- Exit: all risk transitions covered by testbench.

## Milestone 5 — Modular cue output
- [ ] Define MCI connector and pin assignment.
- [ ] Implement CUE_EN and optional PWM.
- [ ] Implement maximum-on-time and cooldown.
- [ ] Build safe external driver for selected transducer.
- [ ] Test with LED/dummy load before actuator.
- [ ] Test interchangeable output modules without changing risk engine.
- Exit: cue output is bounded, reset-safe, and electrically compatible.

## Milestone 6 — Basys 3 integration
- [x] Integrate modules at top level (synthetic-trace demo).
- [x] Add XDC pin constraints.
- [x] Add LED debug display; UART input/debug path still pending.
- [x] Run synthesis, implementation, timing, and utilization reports.
- [ ] Demonstrate recorded GNSS trace replay (synthetic local-coordinate replay done; NMEA/GNSS pending).
- Exit: repeatable FPGA demo with saved reports and test logs.

Demo status: see `docs/BASYS3_DEMO.md`. The Vivado 2024.2 build met timing
(WNS +1.701 ns) at 885 LUTs, 628 flip-flops, and 18 DSPs. This is a bench demo
with a synthetic trace; it is not GNSS, map, or animal validation.

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
