# Architecture Decision Records

## ADR-001 — Standalone RTL before SoC
- Status: Accepted for v0.1
- Decision: Implement a standalone synthesizable RTL pipeline on Basys 3. No CPU/SoC initially.
- Rationale: First workload is bounded spatial geometry, trajectory estimation, risk FSM, and cue output. A processor is not required to validate the core hypothesis.
- Consequence: Map loading/configuration is static or host-preprocessed for v0.1. Revisit if dynamic configuration becomes necessary.

## ADR-002 — Map data is preprocessed offline
- Status: Accepted for v0.1
- Decision: Obtain road geometry from a digital map source such as OSM, convert it to a local metric coordinate system, and store a bounded set of road segments locally.
- Rationale: No runtime internet dependency and simpler hardware.
- Consequence: Map completeness, freshness, attribution, and manual correction must be handled by the preparation workflow.

## ADR-003 — Output-only cue interface
- Status: Accepted for v0.1
- Decision: The cue module receives commands; it does not need to send feedback to the FPGA.
- Rationale: The core requirement is to issue a response after risk assessment. Hardware feedback can be added if a selected actuator needs it.
- Consequence: Animal response is observed separately using later GNSS/IMU data, not through cue connector input pins.

## ADR-004 — No movement classifier initially
- Status: Accepted for v0.1
- Decision: Do not implement grazing/walking/running classification.
- Rationale: The initial use case is road-approach prediction, requiring position and trajectory rather than semantic behavior classes.
- Consequence: IMU is optional for v0.1 and may be used later to supplement response observation.

## ADR-005 — Non-aversive cue research
- Status: Accepted as safety constraint
- Decision: No electrical shock or painful cue. Start with controlled evaluation of conditioned acoustic cues; vibration remains an experimental alternative.
- Rationale: Cue effectiveness and welfare must be demonstrated, not assumed.
- Consequence: No live-road animal trials; supervised controlled trials only after appropriate review.

## ADR-006 — Basys 3 synthetic-trace demo
- Status: Accepted for the bench demo
- Decision: The first Basys 3 demo replays a compiled synthetic local-coordinate track through the road-distance engine, risk FSM, and cue scheduler. It does not include a GNSS receiver or NMEA parser. The demo road record supplies endpoints plus a precomputed Q14 unit direction, and the geometry engine is pipelined to seven stages and outputs squared distance. The cue output is a 3.3 V logic-level signal on Pmod JA1 for observation only.
- Rationale: Exercise the integrated risk path on hardware before adding the parser and map-memory path, avoid a runtime divider, and meet 100 MHz timing.
- Consequence: Demo state transitions are not GNSS validation. The production map contract still requires endpoints and a manifest; the unit direction is a preprocessed derivative. Demo thresholds are not calibrated safety limits.

## ADR-007 — HerdSync-DTN is a post-v0.1 communications study
- Status: Accepted for the POC; hardware phases need new ADRs
- Decision: Keep the v0.1 standalone RTL safety path unchanged. Build HerdSync-DTN as a separate communication subsystem, starting with the software proof of concept in `poc/`. Phase 0 validates store-carry-forward, version-vector anti-entropy, phone-mule collection, and rejection of duplicate, stale, and forged records. Future hardware uses a COTS BLE SoC over UART/SPI; the Basys 3 remains the risk/cue engine. Do not implement a BLE stack, custom SoC, or network stack in v0.1 RTL.
- Rationale: BLE and DTN require a protocol stack, radio, and security lifecycle that are outside the v0.1 workload. A software POC establishes behaviour and metrics before radio selection, firmware work, or RTL changes. A COTS BLE SoC is lower risk and lower cost than a custom SoC at this stage.
- Consequence: HerdSync-DTN does not affect cue decisions. Neighbor data, phone commands, and emergency messages are telemetry only. Any hardware phase needs a new ADR for the radio, security model, and map/firmware update path. `docs/HERDSYNC_POC.md` defines the POC scope, scenarios, and phased hardware plan.

## ADR-008 — Basys 3 USB-UART bench bridge
- Status: Accepted for the bench demo; record and peer paths verified on hardware
- Decision: Add a separate `balat_herdsync_basys3_top` that exposes the synthetic-trace risk engine over the Basys 3 USB-UART bridge at 115200 8N1. Frames are `AA 55 | version 0x01 | type | length | payload | CRC16/CCITT-FALSE`; type `0x01` carries a 36-byte record with a 3-bit risk state (0-4) and type `0x02` carries a 13-byte peer summary. A PC host (`poc/herdsync_dtn/host.py`) acts as the phone/DTN peer. The existing `balat_basys3_top`, `basys3_demo.xdc`, and cue interface are unchanged.
- Rationale: The user has a Basys 3 but no BLE boards or BLE phone. A USB-UART bridge validates framing, host parsing, and status display using available hardware, and defines the byte pipe a future COTS BLE module will use.
- Consequence: The bridge is unsigned, unauthenticated, and not a production collar link. UART state is telemetry only and must never drive `cue_out`, the risk FSM, or the cue scheduler. Pins `RsRx=B18` and `RsTx=A18` come from Digilent's `Basys-3-Master.xdc`. Phase 3b (BLE module) still requires a new ADR covering the radio, security, and update path.

## ADR-009 — GNSS receiver selection: u-blox NEO-M8N
- Status: Accepted for v0.1
- Decision: Target the u-blox NEO-M8N (or pin-compatible NEO-M9N) GNSS module. Parse the $GNRMC (and $GPRMC) sentence at 9600 baud 8N1, which is the module's default configuration.
- Rationale: NEO-M8N is widely available, inexpensive ($5-15), supports GPS+GLONASS+Galileo, has 3.3 V UART output compatible with Basys 3 Pmod pins, and defaults to outputting RMC sentences at 1 Hz. The NMEA parser (`rtl/nmea_parser.v`) is already built and tested for $G[PN]RMC. Any module outputting standard NMEA RMC at 3.3 V UART can substitute.
- Consequence: Default baud rate for the GNSS UART path is 9600. The module-specific configuration (update rate, constellation selection, SBAS) is set via the receiver's own configuration tool, not by the FPGA. The FPGA does not send UBX commands in v0.1.

## ADR-010 — Read-only Basys3 dashboard telemetry
- Status: Accepted for the bench POC
- Decision: The dashboard consumes only validated type-`0x01` USB-UART records from `balat_herdsync_basys3_top` at 115200 baud. It may calculate presentation-only speed, approach, and distance for the fixed synthetic demo segment, and it may write explicitly started local CSV sessions. It exposes no HTTP endpoint or serial command path to FPGA controls, risk state, or cue output.
- Rationale: A single, visible host display and recording artifact should reflect the same FPGA records as the board LEDs, while preserving the output-only cue boundary.
- Consequence: The current dashboard is a bench observability tool, not a production application. UART v1 does not carry cue-active, so cue state is verified on LED5 or JA1. The OSM-derived `road_segments.csv` layer is clearly labelled reference-only because it is not loaded into the current fixed-segment bitstream; its source and ODbL attribution stay in `road_manifest.json`.

## ADR-011 — ESP32-C3 portable-core bench prototype
- Status: Accepted for the MCU bench prototype only
- Decision: Implement the ESP32-C3 prototype with ESP-IDF v5.x and a portable, fixed-point C `balat_core`. It consumes the existing map and replay data, preserves RTL coordinate/risk contracts, and keeps GPIO actuation behind a physical cue-enable input and protected external driver.
- Rationale: This permits GNSS/UART, power, logging, and replay bench work without changing the standalone RTL v0.1 architecture. A host-compiled core gives regression coverage where ESP-IDF hardware tooling is unavailable.
- Consequence: USB/replay/NMEA paths cannot enable a cue, map checksum/version validation is mandatory, and every decision is CSV logged. The MCU defaults to a 500 ms maximum cue and 30 s cooldown as a conservative bench setting. It remains a field-data/bench prototype, not a production collar or evidence of animal guidance.

## ADR-012 — ESP32 PCB signal profile and dashboard mock GPS
- Status: Accepted for bench integration only
- Decision: Add an ESP32-C3 PCB profile matching the BALAT main-board netlist: GPIO3 buzzer driver, GPIO4 motor driver, GPIO5 active-low GPS power, GPIO6 hold-to-enable button, GPIO10 status LED, and GPIO20 GNSS UART RX. Use the ESP32-C3 native USB Serial/JTAG console so the command/log channel does not occupy GPIO20. For the separate breadboard demo, add red/yellow/green risk indicators on GPIO7/GPIO21/GPIO10; GPIO7 and GPIO21 are not routed on PCB v1. Both PCB cue drivers follow the existing bounded cue scheduler. The dashboard may start, pause, reset, and set the speed of a synthetic NMEA input trace; it cannot arm outputs.
- Rationale: Reuse the assembled PCB's transistor drivers and indicator while preserving one physical cue authorization. Replaying checked NMEA through the firmware parser makes the dashboard a controllable input demonstrator without replacing device-side fix, map, risk, and cue logic.
- Consequence: The existing PCB button's original report function is repurposed as a hold-to-enable in this bench image. Releasing it disables both outputs. This profile resolves the firmware/netlist signal mismatch, but does not clear the PCB v1 power-path, DRC, or fabrication hold. Confirm the exact ESP32-C3 module USB wiring before programming; use no battery, TP4056, solar, or motor until the power-path review is closed.

## ADR-013 — Dashboard-controlled Basys 3 NMEA demo
- Status: Accepted for bench demonstration only
- Decision: Add a separate `balat_basys3_dashboard_top` image that receives raw checksummed NMEA over the Basys 3 USB-UART, runs the RTL NMEA/coordinate/geometry/risk/cue pipeline, and returns the existing HerdSync telemetry record format. The dashboard reuses the ESP32 mock-trace controls and labels this source `BASYS3_NMEA_UART`. The original synthetic replay image and HerdSync telemetry-only image remain separate.
- Rationale: One dashboard replay can exercise both the ESP32 firmware parser and the FPGA RTL parser, with each device producing its own decisions and telemetry.
- Consequence: The FPGA demo uses a fixed horizontal road segment and a dashboard-generated synthetic NMEA trace. SW2 remains the physical FPGA cue-enable, SW1 forces invalid, and SW3 forces map invalid. JA1 is 3.3 V logic observation only; it is not electrically tied to the ESP32 PCB cue driver nets. Do not connect board outputs together or directly connect JA1 to an actuator.
