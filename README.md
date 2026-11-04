# BALAT RTL — Road-Aware Livestock Guidance

An FPGA-first research and prototyping project for an autonomous livestock wearable.
The initial prototype uses standalone synthesizable RTL on a Digilent Basys 3 (Artix-7),
with external GNSS input and an interchangeable, output-oriented cue module.

> Status: architecture baseline plus a synthetic-trace Basys 3 bench demo and a
> Basys 3 USB-UART record and peer-summary bridge verified on hardware. GNSS
> input, map memory, and animal guidance effectiveness are not yet validated. A
> separate post-v0.1 software POC studies gatewayless collar communication; it
> does not change the v0.1 safety path.

## Initial design decision

**BALAT v0.1 does not include a SoC or soft CPU.** The FPGA implements a deterministic
data path:

```text
GNSS UART
   |
   v
GNSS parser --> position/quality registers
   |
   v
Road-segment memory (BRAM / initialized ROM)
   |
   v
Road geometry + distance engine
   |
   v
Trajectory / approach estimator
   |
   v
Risk state machine
   |
   v
Cue scheduler / output driver
   |
   v
MCI output connector --> external cue driver/module
```

An MCU, processor, radio, cloud connection, camera, movement classifier, and bidirectional
cue-module protocol are explicitly out of scope for v0.1 unless later justified by evidence.

## Repository map

- `PRD.md` — product requirements and acceptance criteria.
- `ARCHITECTURE.md` — functional and RTL architecture.
- `PLAN.md` — milestones, tasks, and exit criteria.
- `AGENTS.md` — instructions for human and AI coding agents.
- `docs/INTERFACES.md` — GNSS, road-map, and cue interface contracts.
- `docs/VERIFICATION.md` — simulation, FPGA, and field-test strategy.
- `docs/SAFETY_AND_LIMITATIONS.md` — safety constraints and known limitations.
- `docs/RESEARCH_NOTES.md` — research questions and evidence to collect.
- `docs/DECISIONS.md` — architecture decision records.
- `docs/BASYS3_DEMO.md` — build, program, and run the synthetic-trace demo.
- `docs/PROTOTYPE_RUNBOOK.md` — improve the FPGA prototype toward a real-GNSS lab demonstrator.
- `docs/MICROCONTROLLER_PROTOTYPE.md` — parallel MCU prototype for GNSS, power, logging, and field-data validation.
- `docs/HERDSYNC_POC.md` — post-v0.1 gatewayless DTN software POC and hardware plan.
- `docs/BASYS3_HERDSYNC_BRIDGE.md` — Basys 3 USB-UART record bridge and host collector.
- `rtl/` — synthesizable Verilog/SystemVerilog.
- `tb/` — testbenches.
- `constraints/` — Basys 3 XDC constraints.
- `scripts/` — build and data-conversion scripts.
- `poc/herdsync_dtn/` — HerdSync-DTN reference model, scenarios, UART frame codec, and host collector.
- `poc/tests/` — POC unit and scenario tests.
- `data/` — sample map data and generated road-segment memory images.

## Quick start

1. Read `PRD.md`, `ARCHITECTURE.md`, and `docs/SAFETY_AND_LIMITATIONS.md`.
2. Confirm the Basys 3 board revision and Vivado version.
3. Implement and simulate the GNSS parser before connecting physical hardware.
4. Start with synthetic road segments and a host-driven UART test.
5. Add the geometry and risk pipeline only after parser tests pass.
6. Use a dummy LED/buzzer load before connecting any actuator driver.
7. Build and run the current synthetic-trace demo with `docs/BASYS3_DEMO.md`.
8. Follow `docs/PROTOTYPE_RUNBOOK.md` before describing a real-GNSS or map-aware FPGA demo.
9. Use `docs/MICROCONTROLLER_PROTOTYPE.md` for a parallel wearable and field-data prototype.
10. Optionally run the post-v0.1 HerdSync-DTN simulation:
   `python3 -m poc.herdsync_dtn --scenario all`; see `docs/HERDSYNC_POC.md`.
11. Stream frames from the Basys 3 to a PC and back with
   `docs/BASYS3_HERDSYNC_BRIDGE.md`.

## Design principles

1. Autonomous core: no base station or internet required during runtime.
2. Map-first: roads are preloaded/configured from an external map workflow; no live map API in the wearable.
3. Conservative risk: account for GNSS uncertainty and stale fixes.
4. Output-only cue module in v0.1: BALAT commands an external driver; it does not assume actuator feedback.
5. Humane-by-design: cues are experimental, conditioned, limited, and subject to supervised animal-behaviour validation.
6. Reproducible engineering: every module has a specification, testbench, and measurable acceptance criteria.
