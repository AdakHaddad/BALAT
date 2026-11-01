# HerdSync-DTN Proof of Concept

> **Status:** Phase 0 software POC complete. Phase 3a uses a Basys 3 plus a PC
> USB-UART host as a bench stand-in for the phone/BLE peer. BLE radio phases are
> blocked on hardware availability. This is a communication study for a
> post-v0.1 capability. It is not firmware, a safety component, or a validated
> animal-behaviour system. It does not change the BALAT v0.1 cue path.

HerdSync-DTN is a gatewayless, delay-tolerant location-sharing layer for BALAT
collars. Collars exchange signed location records over BLE when they come into
range; a farmer's phone collects the latest known location of every collar it
can reach. The pattern is store-carry-forward, not continuous networking.

## 1. What this POC demonstrates

- A signed, immutable location record with an origin ID, epoch, sequence
  number, timestamp, local coordinates, quality, battery, risk, and priority.
- Version-vector anti-entropy: two nodes exchange only records the peer has not
  seen.
- Controlled forwarding: a mutable TTL envelope bounds propagation and prevents
  stale records from circulating indefinitely.
- Duplicate suppression, stale-fix rejection, future-clock rejection, and
  authentication failure rejection.
- Phone collection and optional phone push-back to a collar.
- Partition and rejoin convergence.
- Multi-hop propagation over a line of six collars.
- Priority handling for an emergency record.

## 2. What it does not demonstrate

- BLE advertising, scanning, GATT, MTU negotiation, connection timing, or radio
  range.
- Body attenuation, antenna orientation, interference, or field reliability.
- Battery current, sleep scheduling, or energy harvesting.
- Production authentication and key management. The POC uses an 8-byte
  truncated HMAC-SHA256 tag with a shared keyring as a stand-in for per-device
  signatures such as Ed25519 or ECDSA.
- Map distribution, signed configuration updates, or firmware update.
- A phone app, persistent storage, time synchronization, or a real GNSS input.
- Any effect on the cue decision. Neighbor and phone data are telemetry only.

## 3. Architecture

```text
  Collar 1             Collar 2             Collar 3
  +--------+  BLE     +--------+  BLE     +--------+
  | record |<-------->| record |<-------->| record |
  | VV     |  GATT    | VV     |  GATT    | VV     |
  +--------+          +--------+          +--------+
       ^                   ^                   ^
       |                   |                   |
       +--------- phone visits each collar ----+
                  (pull latest, optional push)
```

Each collar keeps a latest-record table keyed by `origin_id` and a version
vector of `(origin_id, epoch, seq)` entries. A contact is a short BLE GATT
session. The phone is a mobile sink: it visits collars, pulls their tables, and
can push records back to a collar.

The full record is not broadcast in the advertisement. Advertising carries a
small digest or summary; the GATT session transfers the records the peer is
missing. This keeps radio time bounded and avoids exposing the full table to
every nearby scanner.

## 4. Record model

The POC record payload is 28 bytes. The authentication tag is 8 bytes, so the
wire size is 36 bytes.

| Field | Encoding | Notes |
| --- | --- | --- |
| `schema_version` | `u8` | Currently 1 |
| `priority` | `u8` | 0 routine, 1 alert |
| `epoch` | `u16` | Boot or key epoch; larger value wins |
| `origin_id` | `u32` | Collar identity |
| `seq` | `u32` | Per-origin serial number, wrap-aware |
| `fix_time_s` | `u32` | Fix time, seconds |
| `x_cm` | `i32` | Local x, centimetres |
| `y_cm` | `i32` | Local y, centimetres |
| `quality` | `u8` | 0-100 |
| `battery_mv` | `u16` | Millivolts |
| `risk` | `u8` | 0-4, mirrors the risk-state encoding (including COOLDOWN) |
| `auth_tag` | 8 bytes | Truncated HMAC-SHA256 in the POC |

The TTL is deliberately outside the signed payload. A relay can decrement it
without invalidating the origin's signature. Relays never rewrite the record
body.

Production choices still open: WGS84 coordinates or a local map frame,
Ed25519/ECDSA signatures, per-device keys, key rotation, replay windows, and
whether risk/battery belong in every record or a separate status record.

## 5. Synchronization rules

1. Reject a record with an unknown origin, invalid schema field, or bad tag.
2. Reject a fix that is older than `stale_after_s` (default 300 s), except the
   phone may retain stale records for display.
3. Reject a fix more than `max_future_skew_s` (default 60 s) in the future.
4. If the origin is already known, accept only a newer `(epoch, seq)`.
5. Treat an identical `(origin_id, epoch, seq)` as a duplicate; do not count it
   as new data.
6. Forward only records with `ttl > 0`; a relay decrements TTL before sending.
7. Send alert records before routine records, then newest first.
8. Default TTL is 6. It covers a six-collar line with five relays and leaves
   one hop of margin.

Sequence comparison is serial-number arithmetic over 32 bits, so a wrap does
not make an old record look new. An epoch change overrides sequence comparison.

## 6. Simulation model

The simulator is discrete-time. It advances in 1 s steps by default; collars
generate a fix every 10 s; contacts occur at a configurable period when two
nodes are within `ble_range_m`. Each contact has a bounded record budget. The
phone visit is an explicit event, not an always-on connection.

Metrics:

| Metric | Meaning |
| --- | --- |
| `latest_coverage` | Collars whose latest record is held by the phone, divided by total collars |
| `phone_records` | Number of distinct origins in the phone table |
| `freshness_p50/p95/max` | Age of the latest phone record at collection time |
| `multi_hop_count` | Origins received by the phone after at least one relay |
| `node_contact_count` | Collar-to-collar contacts |
| `phone_contact_count` | Phone-to-collar visits |
| `duplicates_rejected` | Duplicate records seen during contacts |
| `records_rejected` | Stale, future, old, unknown-origin, or bad-auth records |

## 7. Scenarios and current results

Run:

```bash
python3 -m poc.herdsync_dtn --scenario all
```

Measured output on the current POC (`seed=7`):

| Scenario | Latest coverage | Phone records | Multi-hop origins | Freshness p95 | Contacts |
| --- | --- | --- | --- | --- | --- |
| `two_collar` | 2/2 | 2 | 1 | 10 s | 70 node, 1 phone |
| `multi_hop` | 6/6 | 6 | 5 | 60 s | 900 node, 1 phone |
| `partition_rejoin` | 6/6 | 6 | 5 | 60 s | 1500 node, 1 phone |
| `phone_mule` | 5/5 | 5 | 0 | 0 s | 0 node, 6 phone |
| `emergency` | 6/6 | 6 | 5 | 90 s | 300 node, 1 phone |

`emergency`: origin 6 alert delivered to the phone, latency 90 s, still present
in the phone table at collection.

These are simulation results, not field measurements. The scenarios are
deterministic for a fixed seed, but they are not a statistical validation of BLE
behaviour.

### Scenario details

- `two_collar`: two collars 20 m apart, 30 m range, routine fixes every 10 s,
  phone visits node 1 after a settle period.
- `multi_hop`: six collars on a 20 m-spaced line, 30 m range, five relays, phone
  visits node 6 after a settle period.
- `partition_rejoin`: two groups of three collars separated by 1 km, then the
  second group moves next to the first; phone visits after convergence.
- `phone_mule`: five collars 100 m apart, no collar-to-collar contacts; the
  phone visits each collar and pushes the collected table back to node 1.
- `emergency`: six-collar line; node 6 emits an alert at 30 s; phone visits node
  1 after the alert has propagated.

## 8. Running the POC

```bash
python3 -m poc.herdsync_dtn --scenario all
python3 -m poc.herdsync_dtn --scenario multi_hop --verbose
python3 -m poc.herdsync_dtn --scenario emergency --json build/herdsync_poc_report.json
python3 -m unittest discover -s poc/tests -t . -v
```

The JSON report includes the scenario name, bounded radio parameters, metrics,
the phone table, and per-node counters. It is suitable for regression checks
and for plotting later.

Current test result: 26 tests pass. The suite covers signature verification,
tampering, wrong keys, duplicate and old records, stale and future fixes,
sequence wrap, epoch changes, TTL forwarding, priority order, version vectors,
phone pull/push, all five scenarios, determinism, JSON serialization, UART frame
encoding, CRC, split-frame parsing, oversize length, and unknown frame types.

## 9. Phased plan

| Phase | Deliverable | Exit criterion | Status |
| --- | --- | --- | --- |
| 0 | Software POC | All scenarios and unit tests pass | Complete |
| 1 | Two-board BLE POC | Two COTS boards exchange records over GATT and a phone reads both | Not started |
| 2 | Multi-hop BLE POC | Three boards forward a record across two hops; partition/rejoin works | Not started |
| 3a | Basys 3 USB-UART bench bridge | Basys 3 exports framed records to a PC host and displays peer status | Complete on hardware |
| 3b | Basys 3 BLE bridge | UART link to a COTS BLE module; phone reads the record | Blocked: no BLE module |
| 4 | Field prototype | Enclosed, supervised, non-aversive bench/field test with welfare review | Not started |

Phase 3b does not put BLE or a DTN stack in the v0.1 RTL. The Basys 3 remains
the risk/cue engine; a COTS BLE module handles the radio.

## 10. Phase 1: real BLE boards

Suggested hardware:

| Item | Suggested part | Purpose |
| --- | --- | --- |
| BLE development boards | 2-3x nRF52840 DK, or ESP32-C3 boards | Firmware and radio experiments |
| Phone | Android or iOS with nRF Connect | GATT client and data-mule prototype |
| Power measurement | Nordic PPK2 or equivalent | Current profile |
| BLE sniffer | Nordic sniffer or equivalent | Advertising and connection debugging |
| Test enclosure | Non-metallic box and spacer | Repeatable range tests |
| Optional | Dummy torso/water phantom | Body attenuation screening |

Firmware responsibilities:

- Generate a signed record from a synthetic or replayed GNSS fix.
- Advertise a short digest or service UUID.
- Scan for peers and connect when a peer digest indicates missing records.
- Expose a GATT service: `summary` for the version vector, `records` for the
  table, `status` for battery and time, and later `config`/`map` for signed
  updates.
- Persist the latest table across reset.
- Enforce TTL, duplicate, stale, future, and authentication checks.
- Log contacts, bytes, and failures for comparison with the POC.

Acceptance targets for Phase 1 (design targets, not measured claims):

- Two boards discover each other within 30 s at 1 m in open air.
- A full 36-byte record sync completes within 10 s of discovery.
- The phone reads the latest record from both boards in one visit.
- A forged or tampered record is rejected.
- A reset does not resurrect an old record as new.

## 11. Phase 3: Basys 3 integration

### Implemented bench variant (Phase 3a)

The current bench uses only the Basys 3 and its USB-UART bridge. The FPGA streams
a 43-byte frame at 10 Hz:

```text
AA 55 | version 0x01 | type | length | payload | CRC16/CCITT-FALSE
```

- Type `0x01`: 36-byte record (28-byte POC record body plus eight zero tag bytes);
  the risk byte carries the full 0-4 state, including COOLDOWN.
- Type `0x02`: 13-byte peer summary (`peer_id`, `seq`, `fix_time_s`, `risk`).

`poc/herdsync_dtn/host.py` validates frames, prints records, optionally writes
JSON Lines, and can send a peer summary back to the board. The RTL bridge retains
TX/RX frame counts, CRC errors, TX drops, and peer status for host-side
inspection; the simplified POC LEDs show only risk, cue, and heartbeats. It never
feeds the risk FSM or cue scheduler.

Bench results: Icarus simulations pass; the Vivado 2024.2 build met timing
(WNS +0.614 ns, WHS +0.127 ns) at 1053 LUTs, 1190 flip-flops, and 18 DSPs. On
hardware, `/dev/ttyUSB1` delivered 320 records over two runs with no CRC errors
and no sequence gaps within each run; risk states 0-4 (including COOLDOWN) were
observed, and JSON Lines output was validated. A host peer summary was accepted,
confirmed by the RX counter (the simplified display does not expose peer LEDs). A 120 s soak
delivered 1200 frames with no CRC errors, sequence gaps, or resets. See
`docs/BASYS3_HERDSYNC_BRIDGE.md` for build, pin, LED, and host commands.

### Next: BLE module (Phase 3b)

The Basys 3 has no BLE radio and cannot run a BLE stack. Use a COTS BLE module
with a UART interface, such as a Pmod BLE module or an nRF52/ESP32 board, on an
unused Pmod header. Keep the existing `cue_out` on Pmod JA1. This step is blocked
until a radio module is available.

Recommended boundary:

```text
Basys 3 (risk/cue engine) <-- UART --> BLE module <-- BLE --> phone/collars
```

The FPGA-side interface is deliberately small:

- `uart_rx`: framed records or status from the BLE module.
- `uart_tx`: a framed local position/risk record to the BLE module.
- `neighbor_count` and `neighbor_age` registers for LEDs or the seven-segment
  display.
- No path from UART/BLE state to `cue_out`, `risk_fsm`, or `cue_scheduler`.

The implemented bridge uses `0xAA 0x55 | version | type | length | payload |
CRC16` with a byte-level CRC. When the BLE module is added, connect it to the
same framing on an unused Pmod header, add its pins to a new XDC copied from
Digilent's `Basys-3-Master.xdc`, and do not invent pin locations. Keep the cue
output independent of BLE link state.

Phase 3 bench sequence:

1. ~~UART loopback between the FPGA and the USB-UART bridge.~~ Done in simulation.
2. ~~FPGA sends a record; host verifies framing and CRC.~~ Host codec, RTL
   testbenches, and the physical record path are done.
3. BLE module connected to the phone; phone reads the record. Blocked.
4. Two Basys 3 boards show neighbor count and latest age. Blocked.
5. Fault injection: unplug the BLE module, corrupt a frame, and force a stale
   fix; verify the cue path is unaffected and the display shows a link fault.
   The stale/fault path is covered in simulation; the unplug test needs hardware.

## 12. Open questions before hardware

- Is the production record signed with Ed25519, ECDSA, or a symmetric scheme?
- What is the key provisioning and rotation process for a herd?
- Does the collar need a local map frame, WGS84, or both?
- How many records must persist across reset, and for how long?
- What is the phone's role: read-only sink, data mule, or configuration tool?
- What is the acceptable latency for an emergency record in a real herd?
- Which BLE SoC meets current, range, antenna, and certification constraints?
- How is a stale or missing neighbor record displayed without implying safety?

## 13. Safety and scope limits

- This POC does not authorize animal trials or road tests.
- Do not connect an actuator directly to a Basys 3 pin or a BLE module pin.
- Do not use neighbor data, phone commands, or emergency messages to drive the
  cue. The cue path remains local, validated, and fail-safe.
- Do not claim that HerdSync-DTN prevents collisions, finds lost cattle
  reliably, or steers a herd. Those claims require controlled evidence.
- Any animal work requires veterinary/animal-welfare review, trained
  supervision, a safe enclosed area, non-aversive cues, and a stop rule.
