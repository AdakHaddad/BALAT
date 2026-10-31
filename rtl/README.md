# RTL source

Place synthesizable RTL here. Keep one primary module per file where practical.
Every module must have a documented interface and a corresponding testbench under `tb/`.
Do not add processor/SoC modules in v0.1 without an approved ADR.

Current demo modules:

- `balat_basys3_top.v` — synthetic-trace top-level integration, LEDs, switches, watchdog.
- `balat_herdsync_basys3_top.v` — separate UART-bridge top; same risk/cue path plus 10 Hz frame output.
- `trace_player.v` — fixed-rate trace address generator.
- `demo_trace_rom.v` — generated synthetic trace ROM (do not edit by hand).
- `road_geom.v` — seven-stage pipelined point-to-segment squared distance.
- `risk_fsm.v` — INVALID/SAFE/CAUTION/DANGER/COOLDOWN state machine.
- `cue_scheduler.v` — maximum-on-time and cooldown scheduler.
- `uart_tx.v` — 115200 8N1 transmitter.
- `uart_rx.v` — 8N1 receiver with a two-flop synchronizer.
- `herdsync_uart_bridge.v` — record framing, CRC, peer-summary parser, status counters.
