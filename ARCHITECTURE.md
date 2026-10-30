# BALAT RTL Architecture — v0.1

## 1. Architecture choice

Use a **standalone RTL datapath**, not a SoC, for v0.1.

Rationale:
- Workload is bounded and event-driven.
- The core path is parsing, fixed-point geometry, risk-state logic, and cue scheduling.
- A processor is not required to demonstrate the first hypothesis.
- A processor or MCU can be added later for dynamic map management, richer configuration, logging, and communications.

## 2. Block diagram

```text
                   Basys 3 / Artix-7
  GNSS UART
      |
      v
+------------------+
| uart_rx + parser |
+------------------+
      |
      v
+---------------------+       +-----------------------+
| position registers  |<------| fix validation/watchdog|
+---------------------+       +-----------------------+
      |
      +---------------------------+
                                  |
  road segment BRAM/ROM           |
      |                           |
      v                           v
+---------------------------------------+
| candidate segment selection (v0.1 may |
| scan all configured segments)         |
+---------------------------------------+
      |
      v
+---------------------+
| road distance engine|
+---------------------+
      |
      v
+----------------------+
| trajectory estimator |
+----------------------+
      |
      v
+---------------------+
| risk assessment FSM |
+---------------------+
      |
      v
+----------------------+
| cue scheduler/driver |
+----------------------+
      |
      v
  MCI output connector
  (external driver + transducer)

Debug: LEDs / seven-segment / UART TX
```

## 3. Coordinate representation

Do not calculate Euclidean distance directly on latitude/longitude degrees.

The map preprocessing tool should:
1. Select a local origin near the pilot area.
2. Convert road geometry to a local metric coordinate system (East, North), using an appropriate local projection.
3. Simplify road polylines while preserving road shape and junctions.
4. Split polylines into bounded line segments.
5. Store each segment with endpoints, road class, configured buffer, and validity metadata.
6. Quantize coordinates into documented signed fixed-point integers.

For a small local pilot, a suitable projected CRS can be selected for the region. Document the CRS and origin in the generated map manifest. Do not assume a single flat projection is appropriate for every deployment.

## 4. Distance calculation

For v0.1, use point-to-segment distance. Given animal point P and road segment AB:
- Compute projection parameter t = dot(P-A, B-A) / dot(B-A, B-A).
- Clamp t to [0,1].
- Compute closest point Q = A + t(B-A).
- Compute distance d = norm(P-Q).

Implementation options:
- Initial FPGA implementation: fixed-point projection and squared-distance comparison, avoiding square root where only threshold comparisons are needed.
- If exact distance is needed for display, add an integer square-root IP.
- Guard zero-length segments and arithmetic overflow.
- Validate against a Python reference model.

An alternative first prototype may use distance-to-polyline approximations or rectangular road buffers, but the approximation and limitations must be explicit.

## 5. Trajectory / time-to-road

Use successive valid fixes and timestamps to estimate local velocity. Project velocity onto the vector from current position toward the closest road point.

Only treat positive velocity toward the road as an approach. Handle:
- low-speed/noisy heading;
- stale fixes;
- implausible jumps;
- GNSS uncertainty;
- animal turning during the observation interval.

Do not use a single GNSS heading field as the only direction source at low speed. Require multiple valid fixes and confidence checks.

## 6. Risk state machine

Initial states:
- INVALID: no trustworthy current position.
- SAFE: no imminent approach detected.
- CAUTION: approaching configured road buffer.
- DANGER: predicted road entry within configured horizon / inner threshold.
- COOLDOWN: cue has been issued and repeat is inhibited.

Use configurable thresholds, hysteresis, consecutive-fix confirmation, and maximum cue rate. Thresholds must be calibrated and validated in a controlled environment; do not treat example numbers as safety limits.

## 7. Cue interface

MCI v0.1 is output-oriented:
- Power rails supplied through protected external circuitry.
- CUE_EN digital output.
- Optional CUE_PWM output.
- Optional serial output only if a selected module needs it.
- Common ground and connector keying.

The FPGA must not directly drive a speaker, motor, or other high-current actuator. Use a separate driver stage matched to the transducer.

Cue module feedback pins are optional future expansion, not required for basic actuation. Animal response is inferred separately from later GNSS/IMU observations and requires behavioral validation.

## 8. Clocking and reset

- Use Basys 3 oscillator as the primary clock.
- Synchronize asynchronous UART RX before state-machine use.
- Generate clock enables rather than fabric-gated clocks.
- Use a documented reset strategy and ensure all outputs default inactive.
- Constrain all I/O and clock timing in XDC.

## 9. Memory and scalability

For v0.1, scan a small bounded list of road segments stored in BRAM/ROM. Define:
- maximum segment count;
- record width;
- coordinate scale;
- road class encoding;
- buffer width;
- map version.

If map size or update needs outgrow BRAM, add external memory or a configuration MCU in a later revision. Do not add a SoC preemptively.

## 10. Future extension points

- MCU for map loading and device configuration.
- LoRa/BLE/cellular for farmer notification.
- IMU for response observation and dead-reckoning assistance.
- Audio feature extraction or other environmental sensing.
- More sophisticated risk model.
- ASIC implementation after FPGA validation and power/area analysis.
