# RTL source

Place synthesizable RTL here. Keep one primary module per file where practical.
Every module must have a documented interface and a corresponding testbench under `tb/`.
Do not add processor/SoC modules in v0.1 without an approved ADR.

Current demo modules:

- `balat_basys3_top.v` — top-level integration, LEDs, switches, watchdog.
- `trace_player.v` — fixed-rate trace address generator.
- `demo_trace_rom.v` — generated synthetic trace ROM (do not edit by hand).
- `road_geom.v` — seven-stage pipelined point-to-segment squared distance.
- `risk_fsm.v` — INVALID/SAFE/CAUTION/DANGER/COOLDOWN state machine.
- `cue_scheduler.v` — maximum-on-time and cooldown scheduler.
