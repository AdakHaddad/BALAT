# BALAT FPGA Prototype Runbook

This runbook describes the next safe lab prototype for BALAT on the Basys 3.
It is an engineering and verification procedure, not an animal-trial
procedure. The current Basys 3 image is a synthetic-trace bench demo; this
runbook describes how to improve it toward a real-GNSS, map-aware demonstrator.

## 1. Prototype objective

Demonstrate the complete digital path with a real GNSS receiver and recorded
replay:

```text
GNSS UART
  -> UART RX
  -> NMEA validation
  -> fix age/quality gate
  -> local coordinate conversion
  -> road-segment scan
  -> closest-point and distance result
  -> trajectory/approach estimate
  -> risk FSM
  -> bounded cue request
  -> protected dummy load / logic analyser
```

The exit claim is:

> The FPGA can deterministically reject invalid or stale input and produce a
> bounded risk/cue decision for documented synthetic and recorded GNSS traces.

The exit claim is **not** that BALAT keeps livestock away from roads.

## 2. Current baseline

The existing demo already provides:

- a synthetic local-coordinate trace;
- a pipelined point-to-segment distance engine;
- risk states and cue timing limits;
- reset/stale/map-fault demonstrations;
- Icarus simulation and local Vivado build evidence.

The current top does not yet connect the GNSS parser, coordinate converter,
nearest-segment scanner, and generated road map. Do not describe the current
bitstream as a real GNSS/map prototype.

## 3. Lab equipment

Required:

- Digilent Basys 3, documented board revision and FPGA part;
- Vivado version recorded in the test log;
- USB cable and host computer;
- 3.3 V UART GNSS receiver with antenna;
- serial adapter or level-compatible wiring;
- oscilloscope or logic analyser;
- LED or logic-level dummy load.

Recommended:

- GNSS breakout with a known antenna connector;
- current-limited external cue-driver test board;
- bench power supply with current measurement;
- second serial adapter for independent host capture;
- controlled outdoor or open-sky test area away from livestock and traffic.

Do not connect a speaker, motor, or other actuator directly to a Basys 3 pin.

## 4. Before powering the board

1. Confirm the board part, clock, XDC revision, and Vivado version.
2. Confirm GNSS UART voltage, baud rate, sentence configuration, and ground.
3. Confirm that FPGA pins are 3.3 V only.
4. Confirm the cue output is connected only to a logic analyser, LED, or
   protected driver input.
5. Keep `SW2` cue enable disabled until the input, map, and timing checks pass.
6. Keep testing away from live roads and animals.
7. Record the map manifest version, source, extraction time, bounding box,
   coordinate origin, CRS, scale, and checksum.

## 5. Implementation order

Do not integrate all modules in one step. Use these gates:

### Gate A — parser and UART

- Connect `uart_rx` to `nmea_parser`.
- Test valid GPRMC/GNRMC sentences at the selected baud.
- Reject bad checksum, bad hex, malformed fields, void status, invalid
  coordinates, impossible speed, and truncated sentences.
- Publish an accepted-fix sequence, UTC time, fix-valid bit, quality metadata,
  and fix-age/watchdog state.

### Gate B — coordinate conversion

- Confirm the origin and local projected coordinate convention.
- Compare FPGA coordinates with `scripts/golden_nmea.py` and the map conversion
  script.
- Test both hemispheres, negative coordinates, origin, maximum documented
  range, and arithmetic overflow.
- Do not pass a coordinate to geometry unless the fix gate is valid.

### Gate C — map and geometry

- Add a versioned road record format with endpoints, direction, road class,
  road-edge/buffer, validity, and source/confidence flags.
- Instantiate `road_seg_rom` and `nearest_segment`.
- Return segment ID, squared distance, closest point, valid, and result latency.
- Reject an empty, corrupt, out-of-range, or version-mismatched map.
- Compare every vector with the Python reference model.

### Gate D — trajectory and risk

- Use at least two accepted fixes and a real time interval.
- Reject implausible jumps and stale intervals.
- Use the closest point from the selected segment, not only centerline distance.
- Apply GNSS uncertainty and road buffer before threshold comparison.
- Require consecutive qualifying samples before escalation.
- Verify away, parallel, stopped, turning, dropout, and segment-switch cases.

### Gate E — cue output

- Keep the cue enable switch off during functional integration.
- Verify reset, invalid, stale, map-fault, overflow, and disabled states force
  the output inactive.
- Verify maximum-on time and cooldown using a logic analyser.
- Test the output first with an LED or resistor load, then with a protected
  driver and dummy transducer.
- Do not run animal or live-road trials from this milestone.

## 6. Suggested FPGA integration signals

Use explicit transaction boundaries instead of relying on pipeline timing:

```text
fix_seq, fix_time, fix_valid, fix_age, fix_quality, fix_uncertainty
map_valid, map_version, map_fault
geom_start, geom_busy, geom_done
nearest_seg_id, closest_qx, closest_qy, dist2, geom_valid
velocity_valid, approaching, approach_confidence
risk_state, risk_fault, cue_request, cue_active, cue_fault
```

Every result must correspond to a known `fix_seq`. A late geometry result must
not be applied to a newer fix.

## 7. Required verification

Run the existing suites before and after each integration stage:

```bash
bash scripts/run_demo_sims.sh
bash scripts/run_herdsync_sims.sh
python3 -m unittest discover -s poc/tests -t . -v
```

Add an assertion-driven GNSS integration test. It must fail if any expected
result differs. Required scenarios:

- valid approach;
- movement away from a road;
- parallel movement;
- no movement and GNSS jitter;
- invalid checksum;
- void fix;
- stale fix;
- missing UART bytes;
- malformed coordinates;
- implausible position jump;
- zero-length segment;
- empty or invalid map;
- exact threshold and hysteresis boundaries;
- reset during parsing and during cue output;
- map/result from an older `fix_seq`;
- overflow and signed-coordinate limits.

Do not use a test that only prints “PASS” without checking expected state,
distance, validity, and cue timing.

## 8. Hardware evidence log

For each run, save:

- Git commit or source snapshot identifier;
- board and FPGA part;
- Vivado version;
- bitstream path and SHA-256;
- map manifest and checksum;
- GNSS receiver model, firmware/configuration, antenna placement, and baud;
- input trace or raw NMEA capture;
- simulation command and output;
- synthesis utilization and timing reports;
- measured clock/baud and end-to-end decision latency;
- cue pulse width, cooldown, and fault behavior;
- ambient conditions and power measurements;
- known failures and deviations.

Separate measured results from design targets and estimates.

## 9. Stop conditions

Stop the run and disable the cue output if:

- the map version or coordinate origin is uncertain;
- GNSS validity, age, or checksum behavior is unclear;
- a stale or malformed input can produce a cue;
- arithmetic overflow is detected without an invalid gate;
- cue duration or cooldown is not measured;
- the output pin is being used to power a load;
- the board resets unexpectedly;
- an actuator or transducer behaves unexpectedly.

## 10. FPGA improvement priorities

1. Integrate the real GNSS/map path.
2. Add explicit fix quality, uncertainty, age, and sequence handling.
3. Add closest-point output and transaction correlation.
4. Add road-edge buffers and map validity/version checks.
5. Convert integration tests to assertions and reference-model comparisons.
6. Measure timing, power, latency, and long-duration stability.
7. Keep animal guidance and field-safety claims out of the FPGA milestone.

## 11. Prototype exit criteria

The FPGA prototype may be called a **real-GNSS lab demonstrator** only when:

- all five integration gates pass;
- all required failure-injection tests pass;
- the current bitstream uses real GNSS input and the generated map;
- no cue is possible from invalid, stale, uncertain, or corrupt input;
- output timing is measured on a protected dummy load;
- timing and utilization reports are saved;
- the limitations are shown beside the demonstration.

It remains a research demonstrator, not a production collar or road-safety
barrier.
