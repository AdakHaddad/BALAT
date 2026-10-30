# Agent Instructions — BALAT RTL

## Mission
Help build a safe, testable, synthesizable FPGA prototype of BALAT's map-aware road-approach risk engine and modular cue output.

## Non-negotiable architecture constraints
- v0.1 is standalone RTL: do not add a CPU, SoC, MicroBlaze, RISC-V, operating system, or network stack without an approved architecture decision.
- Do not add movement classification unless a concrete requirement and dataset justify it.
- Road geometry is preprocessed offline and stored locally for runtime use.
- The cue interface is output-only in v0.1. Do not require module feedback pins.
- Never drive motors/speakers directly from FPGA pins; use an appropriate protected driver.
- No electric shock or painful stimulus.
- Never claim that a cue will reliably steer cattle without controlled behavioral evidence.

## Engineering rules
1. Read `PRD.md`, `ARCHITECTURE.md`, and relevant `docs/` before changing RTL.
2. Every RTL module must have a concise interface specification and a testbench.
3. Prefer synthesizable, portable Verilog/SystemVerilog supported by the project toolchain.
4. Avoid inferred latches, unsized arithmetic surprises, implicit signedness, and undocumented truncation.
5. Define widths and units for every coordinate, speed, timestamp, and threshold.
6. Use clock enables, not fabric-gated clocks.
7. Synchronize asynchronous inputs; document clock-domain crossings.
8. Reset all actuator outputs to inactive.
9. Invalid/stale GNSS data must never trigger a cue.
10. Add assertions or directed tests for overflow, zero-length segments, malformed packets, stale fixes, and state transitions.
11. Keep a Python reference model for geometric arithmetic and compare test vectors.
12. Do not silently change pin assignments, coordinate scales, map record format, or module interfaces.

## Workflow
- Before implementation, summarize the requirement and identify affected modules.
- Implement the smallest change that satisfies it.
- Add/update tests before declaring completion.
- Run available lint/simulation/build commands; report commands and actual results.
- If tools are unavailable, state that tests were not run. Never fabricate passing results.
- Update `docs/DECISIONS.md` when changing architecture or interfaces.
- Update `PLAN.md` when a milestone changes.

## Map-data rules
- Preserve OSM attribution and applicable ODbL obligations when using OpenStreetMap data.
- Store source, extraction timestamp, bounding box, coordinate reference system, simplification tolerance, and map version in a manifest.
- Treat map data as potentially incomplete or stale.
- Provide a manual correction path for private/missing roads.
- Do not assume map road class equals traffic danger.

## Safety and animal welfare
- Initial tests must use simulation, replayed tracks, dummy loads, or controlled non-road environments.
- Any animal trial requires appropriate veterinary/animal-welfare oversight, trained supervision, and a safe enclosed test area.
- Use non-aversive cues and positive conditioning; enforce cue duration and cooldown.
- Stop trials if distress, habituation, or unsafe behavior is observed.
- BALAT is not a substitute for physical fencing, supervision, or road-safety infrastructure.

## Commit / documentation expectations
- Keep modules small and independently verifiable.
- Document fixed-point formats and latency.
- Include Vivado utilization and timing reports for FPGA milestones.
- Distinguish measured values from estimates and design targets.
