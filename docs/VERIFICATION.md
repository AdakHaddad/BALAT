# Verification and Test Strategy

## 1. Verification layers

### Unit simulation
Each module gets a dedicated testbench:
- UART receiver;
- NMEA parser;
- fix validator/watchdog;
- road memory;
- point-to-segment distance;
- nearest-segment selector;
- trajectory estimator;
- risk FSM;
- cue scheduler/PWM.

### Reference-model comparison
Use Python to generate expected:
- projected coordinates;
- point-to-segment distances;
- closest segment;
- approach velocity;
- risk state.

Feed the same vectors into RTL simulation and compare outputs.

### Integration simulation
Replay timestamped position traces across:
- approach to road;
- movement parallel to road;
- movement away from road;
- stop and restart;
- turn away before boundary;
- GNSS dropout;
- stale fix;
- position jump/multipath outlier;
- multiple nearby road segments;
- map empty/corrupt/out-of-range.

### FPGA bench test
- Start with UART loopback or host-generated GNSS stream.
- Show state on LEDs/seven-segment.
- Use LED or logic analyzer as cue dummy load.
- Only then connect an external driver and transducer.

Current demo status: a synthetic local-coordinate trace replay with LED state
display and a logic-level cue output on JA1 is implemented and verified in
simulation (`docs/BASYS3_DEMO.md`). The UART/NMEA input path, seven-segment
display, and recorded GNSS replay are still pending.

## 2. Required safety tests

- Reset forces cue output inactive.
- Invalid fix forces risk state to INVALID and cue inactive.
- Stale fix cannot sustain or initiate a cue.
- Maximum cue-on time is enforced.
- Cooldown prevents repeated rapid activation.
- Map checksum/version failure disables road-based cueing and indicates fault.
- Arithmetic overflow or invalid segment cannot create a false low-distance result.
- No output pin sources actuator current directly.

## 3. Metrics to report

- Parser success/failure counts.
- Geometry absolute error versus reference.
- Risk-state confusion matrix on synthetic/replayed tracks.
- End-to-end decision latency.
- FPGA LUT/FF/BRAM/DSP utilization.
- Timing slack / maximum clock.
- Board-level power measurement, clearly separated from ASIC estimates.
- Cue command duration and repetition statistics.

## 4. Behavioral validation

Hardware tests do not establish animal learning or cue efficacy.

Any cattle study needs:
- veterinary/animal-welfare review;
- controlled enclosed area away from traffic;
- individual baseline and training protocol;
- positive conditioning;
- randomized/counterbalanced cue trials where feasible;
- response definition specified in advance;
- non-response and adverse-event logging;
- stop criteria;
- independent human supervision.

Never infer that an animal understood a cue merely because it moved after the cue.
