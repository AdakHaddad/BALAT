# BALAT Pitch Deck Review and One-Week MCU Prototype Plan

**Status:** Planning document  
**Scope:** Microcontroller-first behavior and safety validation  
**Constraint:** No animal-facing actuator or real livestock trial during this week

## 1. Pitch deck review

The deck presents BALAT as an offline smart collar using GNSS/geofencing and
vibration or audio cues. Its strongest points are:

- A clear rural livestock and road-safety problem.
- Offline operation as a meaningful differentiator for cellular dead zones.
- A low-cost, modular hardware direction.
- An existing FPGA proof point with visible SAFE, CAUTION, DANGER, and cue
  indicators.
- An explicit non-electric approach to cues.

Several claims should be softened until they have evidence:

| Deck statement or implication | Recommended treatment |
|---|---|
| “Zero-accident” vision | Present as an aspiration, not a demonstrated outcome. |
| Cues will cause cattle to turn away | State that cue response and learning are unproven and require supervised behavioral research. |
| “GPS” provides reliable position | Use “GNSS position with quality and uncertainty gating.” |
| ESP32 stores zones and runs the collar | Treat as a prototype direction, not a validated product architecture. |
| 100% standalone offline geofencing | State that local computation is offline, while GNSS reception and map completeness remain limitations. |
| Roadside LoRa alert station | Keep as a future communications surface, outside the local cue safety path. |
| FPGA LED as an actuator | Call it a dummy cue output or protected-driver control signal. |

The pitch should separate:

1. **Existing evidence:** simulation, synthetic trace replay, FPGA bench logic,
   and UART bridge tests.
2. **One-week target:** MCU GNSS, map, logging, replay, and dummy cue behavior.
3. **Open questions:** animal response, road-safety effectiveness, field
   reliability, battery life, and spoofing resistance.

Suggested evidence-safe product statement:

> BALAT first validates conservative, offline road-approach detection and safe
> cue scheduling under supervised bench and replay conditions. Animal-guidance
> effectiveness remains an open behavioral research question.

## 2. Existing requirements and interfaces to preserve

The MCU must reproduce the existing observable contracts rather than introduce
a second, incompatible policy.

### Requirements

From [`PRD.md`](../PRD.md):

- Parse GNSS serial input.
- Reject invalid, incomplete, or stale fixes.
- Use locally stored, bounded road geometry.
- Calculate point-to-road distance in a documented metric coordinate system.
- Estimate motion toward the road.
- Use SAFE, CAUTION, and DANGER risk states.
- Apply hysteresis, confirmation, maximum cue duration, and cooldown.
- Keep the cue interface output-only and replaceable.
- Never drive a speaker, motor, or other load directly from MCU or FPGA GPIO.
- Test invalid fixes, stale data, map errors, direction changes, and arithmetic
  boundaries.

### Coordinate and map contract

Preserve the contract in [`docs/INTERFACES.md`](../docs/INTERFACES.md) and
[`data/road_manifest.json`](../data/road_manifest.json):

- Local projected East/North coordinates.
- Signed 32-bit coordinates.
- Centimetres as the current coordinate unit.
- Segment endpoints `ax, ay, bx, by`.
- Optional precomputed Q14 direction vectors.
- Road class and source metadata.
- Bounded segment count.
- Manifest containing source, ODbL attribution, extraction date, bounding box,
  CRS/origin, simplification tolerance, coordinate width, and version.

The current fixture contains seven segments and permits up to 256 records.

### RTL behavior to match

| RTL module | MCU behavior |
|---|---|
| [`rtl/nmea_parser.v`](../rtl/nmea_parser.v) | Supported sentence format, checksum validation, fix validity, coordinate conversion, and UTC extraction. |
| [`rtl/road_geom.v`](../rtl/road_geom.v) | Point-to-segment squared distance, endpoint clamping, inside-span result, and zero-length handling. |
| [`rtl/nearest_segment.v`](../rtl/nearest_segment.v) | Scan configured segments and retain minimum squared distance and segment ID. |
| [`rtl/velocity_estimator.v`](../rtl/velocity_estimator.v) | Successive valid fixes, low-speed suppression, implausible jump rejection, and approach dot product. |
| [`rtl/risk_fsm.v`](../rtl/risk_fsm.v) | `INVALID`, `SAFE`, `CAUTION`, `DANGER`, `COOLDOWN`; stale/map fault forces invalid. |
| [`rtl/cue_scheduler.v`](../rtl/cue_scheduler.v) | Reset-safe output, bounded pulse, cooldown, and enable gating. |
| HerdSync bridge | Status and logging only; no cue authorization or extension. |

The demonstration thresholds in [`rtl/risk_fsm.v`](../rtl/risk_fsm.v) are:

- CAUTION enter: 500 cm
- CAUTION exit: 600 cm
- DANGER enter: 200 cm
- DANGER exit: 300 cm

These are demonstration policy values, not livestock safety limits.

The current 10 Hz scheduler profile uses a 0.5 second maximum cue and a
3 second cooldown. The MCU should support this as an explicit compatibility
profile, while using a stricter profile for supervised bench demonstrations.

### Test assets to reuse

- [`data/demo_trace.csv`](../data/demo_trace.csv)
- [`data/demo_trace_expected.csv`](../data/demo_trace_expected.csv)
- [`tb/nmea_test_vectors.txt`](../tb/nmea_test_vectors.txt)
- [`tb/nmea_bad_vectors.txt`](../tb/nmea_bad_vectors.txt)
- [`tb/road_geom_vectors.txt`](../tb/road_geom_vectors.txt)
- [`scripts/golden_geometry.py`](../scripts/golden_geometry.py)
- [`scripts/golden_nmea.py`](../scripts/golden_nmea.py)

The existing RTL and Python regression commands remain the comparison baseline.

## 3. Recommended MCU platform

Use an STM32L476RG Nucleo board for the one-week prototype.

Reasons:

- Low-power MCU suitable for eventual collar-style duty cycles.
- Hardware UART for GNSS.
- USB serial through the ST-LINK interface.
- Hardware timers for deterministic sample ticks and cue timing.
- Watchdog and brownout/reset support.
- Enough flash and RAM for the current map, logs, and replay harness.
- Good integer and fixed-point performance.
- No need to enable Wi-Fi, BLE, or an RTOS during the first week.

An ESP32-class board is an acceptable fallback only if the team already has a
working ESP-IDF environment. Wi-Fi and BLE should remain disabled for the
safety-path experiment.

## 4. MCU prototype architecture

```text
GNSS UART
   |
   v
UART driver + raw byte logger
   |
   v
NMEA parser
   |
   v
Fix-quality and uncertainty gate
   |
   v
Coordinate transform to local centimetres
   |
   v
Map store + checksum/version validation
   |
   v
Nearest segment and squared-distance calculation
   |
   v
Trajectory estimator
   |
   v
Risk state machine
   |
   v
Cue scheduler
   |
   +--> LED / protected driver input / dummy load
   |
   +--> structured UART/USB event log

USB/UART telemetry and HerdSync-DTN status
   |
   +--> logging/status only
       never cue authorization
```

## 5. Required firmware modules

```text
board_support
clock_and_tick
gnss_uart
raw_nmea_capture
nmea_parser
fix_quality_gate
timestamp_and_stale_watchdog
coordinate_transform
map_store
map_manifest_validator
nearest_segment
point_to_segment_distance
trajectory_estimator
risk_fsm
cue_scheduler
fault_manager
manual_disable
event_log
trace_replay
usb_uart_console
herdsync_status_adapter
```

### Core behavior

The MCU processes one fix at a time through a deterministic pipeline. Logging,
USB, and HerdSync processing must not block or alter the risk decision.

Every accepted fix contains:

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

Every geometry result contains:

```text
map_version
segment_id
closest_x/closest_y
distance_squared
road_buffer
geometry_valid
```

Every risk/cue event contains:

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

## 6. GNSS input and uncertainty handling

Use a 3.3 V GNSS receiver with configurable UART, NMEA output, one-second or
faster updates, and visible fix-quality fields where available.

Log both:

1. Raw NMEA bytes.
2. Parsed and accepted fix records.

Use receiver-provided accuracy when available. Otherwise use HDOP/fix quality
as a coarse quality indicator and apply a conservative configured uncertainty
floor. Reject or hold `INVALID` when quality is below the configured minimum.

The effective road threshold is:

```text
effective_distance_limit =
    configured_road_buffer + uncertainty_margin
```

The uncertainty margin must be logged with every risk decision. It must not be
presented as a certified statistical accuracy bound.

For a one-second receiver update, initially mark a fix stale after three
seconds without a fresh accepted fix. A stale fix forces `INVALID` and cue off.

## 7. Road-segment and map representation

Use the current segment model:

```text
segment_id
ax_cm
ay_cm
bx_cm
by_cm
ux_q14
uy_q14
road_class
osm_id or source_id
buffer_cm
valid
```

The manifest remains authoritative for source, license, extraction timestamp,
bounding box, origin, CRS/projection, coordinate unit, simplification
tolerance, segment count, coordinate width, direction format, and checksum or
version.

Use the existing seven-segment fixture for this week. Do not introduce private
farm coordinates into the repository.

## 8. Distance and approach calculations

### Distance

For each valid segment:

1. Compute `R = P - A`.
2. Compute `D = B - A`.
3. Project `R` onto `D`.
4. Clamp the projection to the segment.
5. Calculate squared distance to the closest point.
6. Select the minimum result.

Avoid square root in the decision path. Use squared-centimetre comparisons to
remain aligned with the RTL.

Guard:

- zero-length segments;
- negative coordinates;
- outside-span projections;
- multiplication overflow;
- invalid records;
- maximum coordinate range.

### Approach

Use successive accepted fixes:

```text
velocity = (P_current - P_previous) / elapsed_time
road_vector = closest_point - P_current
approach_score = dot(velocity, road_vector)
```

Approaching is true only when both fixes are accepted, elapsed time is valid,
speed is plausible, the dot product is positive, and uncertainty does not
dominate the movement. Do not rely only on GNSS heading at low speed.

## 9. Risk state machine

Implement:

```text
INVALID
SAFE
CAUTION
DANGER
COOLDOWN
```

Rules:

- Any stale or invalid fix forces `INVALID`.
- Map validation failure forces `INVALID`.
- Enter CAUTION or DANGER only after consecutive qualifying samples.
- Apply distance hysteresis.
- Require `approaching = true` for escalation.
- Keep cue scheduling separate from risk state.
- Manual disable suppresses the cue even in DANGER.
- Log every transition and reason.

## 10. Cue scheduler

Use two profiles:

### `rtl_compatibility`

- 10 Hz sample tick.
- 0.5 second maximum cue.
- 3 second minimum cooldown.
- Same request semantics as the RTL.

### `supervised_safe`

- 250 to 500 ms maximum cue.
- At least 30 seconds between cue starts.
- Manual enable required.
- LED or protected driver input only.
- No cue extension while the request remains continuously high.

The first-week output must be an LED, logic-analyzer signal, or protected driver
input. Do not connect a motor, speaker, vibration module, shock circuit, or
animal-facing actuator.

## 11. UART/USB logging and reproducible traces

Use a dedicated hardware UART for GNSS and the ST-LINK virtual COM port for
logs and commands. Capture raw input and structured decisions separately.

Suggested console commands:

```text
status
map_info
faults
set_profile rtl_compatibility
set_profile supervised_safe
manual_disable 1
manual_disable 0
replay start demo_trace.csv
replay stop
clear_log
reset
```

Every replay run records:

- firmware version;
- map checksum and version;
- profile;
- scenario name;
- configuration;
- reset count;
- start and end timestamps;
- event log.

The same trace should be usable by the Python reference model, MCU replay
harness, and RTL trace player.

## 12. HerdSync-DTN integration boundaries

HerdSync-DTN remains outside the road-risk safety path.

The MCU may export:

- device status;
- risk and fault summaries;
- event logs;
- map version;
- last known fix metadata;
- sequence counters.

HerdSync, BLE, USB, phone, or cloud commands must not:

- authorize or extend a cue;
- bypass stale-fix handling;
- replace the local map without atomic validation;
- clear a safety fault automatically.

For this week, a USB event-log export is sufficient. No radio hardware is
required.

## 13. Failure behavior

| Failure | Required behavior |
|---|---|
| Invalid NMEA checksum | Reject sentence, retain no new position, log parser fault. |
| GNSS reports no fix | Force `INVALID`, cue off. |
| Missing NMEA data | Enter stale state after timeout, cue off. |
| Timestamp stops or moves backward | Reject fix, log time fault, and prevent cueing. |
| Corrupted map record | Reject map load, force `INVALID`, cue off. |
| Map checksum/version mismatch | Reject atomically and force `INVALID` unless an explicitly validated previous map is retained. |
| Empty map | `INVALID`, cue off. |
| Zero-length segment | Handle as a point or reject by documented policy; never produce a false low distance. |
| Coordinate outside range | Reject fix and log range fault. |
| Implausible position jump | Reject fix and clear velocity continuity. |
| Suspected spoof or replay | Quarantine or reject fix, force `INVALID`, log evidence. |
| USB disconnect | Continue local operation; USB cannot authorize a cue. |
| HerdSync packet corruption | Reject packet with no effect on cueing. |
| Watchdog reset | Keep cue GPIO inactive during reset and boot; log reset reason after startup. |
| Brownout | Cue inactive; restart in `INVALID` until a fresh valid fix is accepted. |
| Manual disable | Cue inactive regardless of risk state. |

One week is not enough to provide authenticated GNSS or comprehensive spoofing
defense. The prototype should detect obvious anomalies and fail safe without
claiming GNSS security.

## 14. Day-by-day implementation plan

### Day 1: Freeze contracts and establish the bench

- Select and document the STM32 board, pins, voltage levels, GNSS UART, and
  event-log schema.
- Build boot, reset-reason, firmware-version, and USB-console support.
- Connect only an LED, logic analyzer, or protected driver input.
- Import the current map manifest and trace fixtures.
- Run existing RTL and Python baselines.

**Exit:** USB works, GNSS UART receives bytes, and cue output is inactive after
reset.

### Day 2: GNSS parser and quality gate

- Implement UART buffering, raw capture, RMC parsing, checksum validation,
  status handling, UTC parsing, stale timer, and rejection counters.
- Run valid vectors from [`tb/nmea_test_vectors.txt`](../tb/nmea_test_vectors.txt)
  and invalid vectors from [`tb/nmea_bad_vectors.txt`](../tb/nmea_bad_vectors.txt).
- Add truncated, repeated-timestamp, and missing-stream cases.

**Exit:** Invalid input never produces an accepted fix, and MCU parser output
matches the host reference.

### Day 3: Map loading and geometry

- Implement manifest validation, segment loading, local coordinate conversion,
  point-to-segment squared distance, nearest-segment scan, and arithmetic guards.
- Run the existing geometry vectors and seven-segment map.
- Test endpoints, outside-span points, negative coordinates, degenerate
  segments, and overflow boundaries.

**Exit:** MCU geometry matches the golden vectors within documented tolerance.

### Day 4: Approach estimator and risk FSM

- Implement successive-fix velocity, time validation, low-speed suppression,
  jump rejection, approach dot product, risk states, hysteresis, and
  confirmation.
- Test toward, away, parallel, stationary, turn-away, dropout, jump, and map
  invalidation traces.

**Exit:** State transitions match the RTL policy with no escalation from invalid,
  stale, stationary, parallel, or implausible data.

### Day 5: Cue scheduling, faults, and logging

- Implement both scheduler profiles, manual disable, maximum-on timer,
  cooldown, structured logging, reset/watchdog logging, and LED state display.
- Inject reset, stale, map, USB, and manual-disable faults.

**Exit:** Cue output is bounded and every cue decision has a logged reason.

### Day 6: Replay, comparison, and bench soak

- Implement deterministic synthetic replay and host-side comparison.
- Compare MCU output with Python and RTL expected output.
- Run a supervised multi-hour bench test using only a dummy output.
- Measure MCU, GNSS, USB logging, and idle current separately.

**Exit:** Replay is deterministic and any mismatch identifies the sample and
affected field.

### Day 7: Demo, evidence package, and go/no-go review

- Prepare the demo command sequence, captured logs, test summary, fault matrix,
  MCU-versus-RTL comparison, timing data, and current measurements.
- Label all results as measured, target, or open question.
- Have a second operator reproduce the demo.

**Exit:** The evidence package supports a decision about the next RTL step.

## 15. Minimal bill of materials

| Item | Purpose |
|---|---|
| STM32L476RG Nucleo board | MCU, USB console, timers, watchdog |
| 3.3 V GNSS receiver | GNSS UART input |
| Suitable GNSS antenna | Repeatable bench reception |
| USB cable | Power and logging |
| Breadboard or prototyping board | Safe wiring |
| LED and resistor | Dummy cue output |
| Logic analyzer or oscilloscope | Cue duration and UART timing |
| Optional protected driver input board | Interface validation without a load |
| External regulated supply or USB power meter | Current measurement |
| Jumper wires and safe connectors | Wiring |
| Optional microSD module | Extended logging only if USB is insufficient |

Do not include a motor, speaker, shock circuit, or animal-mounted transducer.

## 16. Required test scenarios

### Parser and GNSS

1. Valid RMC north/east.
2. Valid RMC south/west.
3. Void fix.
4. Bad checksum.
5. Truncated sentence.
6. Unsupported sentence.
7. Repeated timestamp.
8. Stale stream.
9. Malformed or out-of-range coordinates.
10. Implausible position jump.
11. Suspected replayed timestamp.

### Geometry

1. Point inside the projection span.
2. Point before an endpoint.
3. Point after an endpoint.
4. Point exactly on a road.
5. Negative coordinates.
6. Diagonal segment.
7. Zero-length segment.
8. Multiple nearby segments.
9. Empty map.
10. Corrupt record.
11. Map checksum mismatch.
12. Overflow boundary.

### Motion and risk

1. Consistent approach.
2. Consistent movement away.
3. Parallel movement.
4. Stationary noisy fixes.
5. Noisy low-speed movement.
6. Approach followed by turn-away.
7. CAUTION hysteresis.
8. DANGER hysteresis.
9. Two-fix confirmation.
10. Stale fix during DANGER.
11. Map invalidation during DANGER.
12. Manual disable during DANGER.

### Cue safety

1. Reset.
2. Valid DANGER request.
3. Invalid fix.
4. Stale fix.
5. Map fault.
6. Maximum cue duration.
7. Cooldown enforcement.
8. Repeated DANGER samples.
9. USB disconnect.
10. Watchdog reset.
11. Brownout/restart.
12. HerdSync packet error.

## 17. Demo script

### Setup

1. Connect the MCU board to USB.
2. Connect the GNSS receiver to the dedicated UART.
3. Connect only an LED, logic analyzer, or protected driver input to the cue
   output.
4. Leave motors, speakers, vibration modules, and animal hardware disconnected.
5. Open the USB serial console.

### Sequence

```text
reset
status
map_info
set_profile supervised_safe
replay start approach_trace
```

Expected behavior:

1. The device boots with cue inactive.
2. Map version, checksum, segment count, and units are printed.
3. Initial samples produce `SAFE`.
4. Decreasing distance plus confirmed approach produces `CAUTION`.
5. Continued qualifying samples produce `DANGER`.
6. The dummy output activates for the configured maximum duration.
7. The output turns off and remains inhibited during cooldown.
8. A turn-away trace returns through `CAUTION` to `SAFE`.
9. A stale or corrupted trace enters `INVALID` with cue inactive.
10. The event log is exported and compared with Python and RTL output.

Spoken demo claim:

> This demonstrates deterministic offline road-proximity and approach-risk
> processing with bounded dummy cue output. It does not demonstrate that
> livestock will follow the cue or that the system prevents road accidents.

## 18. Risks and mitigations

| Risk | Mitigation |
|---|---|
| GNSS error exceeds the road buffer | Add uncertainty margin, reject low-quality fixes, and test under canopy and partial obstruction. |
| Multipath causes false approach | Require consecutive fixes, speed plausibility, dot-product approach, and hysteresis. |
| Spoofing cannot be reliably detected | Detect obvious jumps, timestamp anomalies, impossible motion, and quality loss; fail to `INVALID`. |
| Parser differs from RTL | Reuse existing vectors and compare accepted fields. |
| MCU geometry differs from RTL | Use fixed-point/integer arithmetic and golden-vector comparison. |
| Map is incomplete or stale | Require manifest/version/checksum and preserve manual correction. |
| Cue chatter or habituation | Use bounded cues, long cooldown, no extension, and manual disable. |
| Logging blocks the safety path | Use non-blocking logging and explicit drop counters. |
| HerdSync causes side effects | Keep it status-only and separate from cue authorization. |
| Board current misleads battery claims | Measure board, GNSS, USB, and regulator currents separately. |
| Scope expands into a product build | Defer enclosure, radio, app, cloud, production PCB, and animal trials. |
| Human traces are mistaken for cattle behavior | Label them as geometry and system tests only. |

## 19. Out of scope for this prototype week

- Animal testing or animal-guidance claims.
- Real motors, speakers, vibration modules, or painful stimuli.
- Roadside operation or testing near live traffic.
- Production collar enclosure or battery-life claims.
- Cellular, BLE, LoRa, Wi-Fi, cloud, or HerdSync radio integration.
- Mobile app and remote map provisioning.
- Automatic map updates.
- Full GNSS spoofing defense.
- Movement classification or machine learning.
- Multi-animal coordination.
- Behavioral conditioning.
- Production-grade geospatial accuracy.
- Replacing or silently changing the existing RTL contracts.

## 20. Comparing MCU behavior against future RTL

Use one shared trace schema and expected-output schema. Compare:

```text
sample_index
timestamp
accepted_fix
fault_reason
local_x_cm
local_y_cm
nearest_segment_id
distance2_cm2
inside_span
velocity
approaching
risk_state
cue_request
cue_active
cue_start_count
```

Use exact comparisons for parser validity, segment IDs, state transitions,
cue gating, stale handling, and map validity. Use documented tolerances for
projected coordinates, distances, velocity, and uncertainty-expanded thresholds.

Compare functional sample-boundary behavior rather than raw clock cycles. FPGA
pipeline latency and MCU software latency will differ.

## 21. Definition of done

The one-week prototype is complete when:

- The MCU boots and reports firmware, version, and reset status.
- GNSS input is captured and logged.
- Valid and invalid NMEA vectors behave as expected.
- Stale fixes force `INVALID` and cue inactive.
- Map manifest and records are validated.
- Geometry matches the repository golden vectors within documented tolerance.
- Approach, away, parallel, stationary, and jump cases are covered.
- The risk FSM matches the required state behavior.
- Cue output is reset-safe, bounded, and cooldown-protected.
- Logs include firmware, map, fix, risk, fault, and cue metadata.
- Synthetic traces replay deterministically.
- MCU results are compared with Python and RTL outputs.
- HerdSync status is isolated from cue authorization.
- A supervised dummy-load soak completes without unexpected cue activation or reset.
- No animal-guidance or accident-prevention claim is made.

## 22. Exit criteria for FPGA continuation

Continue toward FPGA GNSS/RTL implementation only if:

1. MCU parser and geometry agree with reference vectors.
2. No unexplained escalation occurs for invalid, stale, stationary, parallel,
   or implausible traces.
3. Cue output is inactive for every tested fault condition.
4. Map format and uncertainty policy are stable enough to freeze.
5. Event logs identify every decision and support replay.
6. The prototype demonstrates useful deterministic behavior independent of
   HerdSync.
7. The team accepts that behavioral efficacy remains unproven.
8. A supervised, non-animal next test is defined.
9. There is a concrete FPGA reason, such as deterministic latency, parallel
   segment scanning, or hardware architecture research.

Pause or revise the plan if GNSS uncertainty exceeds the intended buffer, map
completeness cannot be verified, MCU and RTL disagree on basic transitions, or
the only evidence of success is that an LED turns on.

## Recommended next step

Run this as a one-week behavior and safety validation sprint. At the end,
produce an evidence report containing parser results, geometry comparisons,
risk-state results, cue timing, fault-injection results, current measurements,
replay logs, and unresolved GNSS/map limitations.

Only then decide whether to:

1. Integrate live GNSS into the existing FPGA path.
2. Refine the risk policy.
3. Improve map and uncertainty handling.
4. Continue MCU-only field instrumentation before expanding RTL.
