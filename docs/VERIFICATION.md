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
simulation (`docs/BASYS3_DEMO.md`). A separate USB-UART bridge exports framed
records to a host (`docs/BASYS3_HERDSYNC_BRIDGE.md`); it is verified in
simulation, builds, and has streamed records on physical hardware. The GNSS/NMEA
input path, seven-segment display, and recorded GNSS replay are still pending.

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

## 5. HerdSync-DTN POC verification

The post-v0.1 communication POC in `poc/` has its own test suite. It does not
verify RTL, firmware, radio behaviour, or the cue path.

Run:

```bash
python3 -m unittest discover -s poc/tests -t . -v
python3 -m poc.herdsync_dtn --scenario all
```

Covered cases:

- valid signature, tampered payload, wrong key, unknown origin;
- duplicate, older, stale, and future records;
- sequence wrap and epoch override;
- TTL decrement and forwarding cutoff;
- alert-before-routine ordering;
- version-vector exchange and pending selection;
- phone pull, phone push, and stale retention;
- two-collar, multi-hop, partition/rejoin, phone-mule, and emergency scenarios;
- deterministic scenario output and JSON serialization.

These are simulation tests. They do not establish BLE range, body attenuation,
power, or field reliability. See `docs/HERDSYNC_POC.md` for the hardware phases
and their acceptance targets.

## 6. Basys 3 UART bridge verification

Run:

```bash
bash scripts/run_herdsync_sims.sh
python3 -m unittest discover -s poc/tests -t . -v
```

The Icarus suite covers UART TX timing and data, UART RX data and framing-error
rejection, frame sync/version/length/CRC checks, record field encoding, TX drop
counting under backpressure, peer-summary parsing, CRC-error rejection, reset,
the integrated risk path, stale fail-safe, and cue independence from UART state.

The Vivado 2024.2 build for `xc7a35tcpg236-1` met timing with WNS +2.451 ns and
WHS +0.122 ns, using 1248 LUTs, 1328 registers, 18 DSPs, and no BRAM. These are
local bench measurements, not field guarantees.

Physical record-path check: the Basys 3 streamed 320 records over `/dev/ttyUSB1`
at 115200 baud across two runs. There were no CRC errors and no sequence gaps
within either run; a reset mid-capture restarted the sequence at 1. Risk states
0-4 were observed, including COOLDOWN=4. A 30-record run wrote valid JSON Lines.
The host sent a peer summary; the board's RX counter toggled and the peer-seen
and peer-risk LEDs lit, confirming the reverse path. A 120 s soak captured 1200
frames with zero sequence gaps, zero CRC errors, zero resets, and zero buffered
bytes at exit.

Not yet verified: USB-UART loopback with an independent adapter, multi-hour or
thermal soak behaviour, and any BLE link. Do not treat the bridge as a validated
communication path beyond these bench runs.
