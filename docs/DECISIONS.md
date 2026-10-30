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
