# Testbenches

Every RTL module has a dedicated testbench. Run the v0.1 demo suite with:

```bash
bash scripts/run_demo_sims.sh
```

Run the Basys 3 UART bridge suite with:

```bash
bash scripts/run_herdsync_sims.sh
```

Current testbenches:

- `tb_road_geom.v` — generated geometry vectors from `scripts/golden_geometry.py`.
- `tb_risk_fsm.v` — state transitions, confirmation, stale/map faults, cooldown.
- `tb_cue_scheduler.v` — pulse limit, cooldown, enable gating, reset.
- `tb_trace_player.v` — sample timing, wrap, pause.
- `tb_balat_basys3_top.v` — end-to-end integration and fail-safe checks.
- `tb_uart_tx.v` — UART TX timing, data, and reset.
- `tb_uart_rx.v` — UART RX data recovery and framing-error rejection.
- `tb_herdsync_uart_bridge.v` — frame construction, CRC, peer parsing, drop counter, reset.
- `tb_balat_herdsync_top.v` — bridge plus risk/cue integration and stale fail-safe.
- `road_geom_vectors.txt` — generated vector file used by `tb_road_geom.v`.
