# Testbenches

Every RTL module has a dedicated testbench. Run the demo suite with:

```bash
bash scripts/run_demo_sims.sh
```

Current testbenches:

- `tb_road_geom.v` — generated geometry vectors from `scripts/golden_geometry.py`.
- `tb_risk_fsm.v` — state transitions, confirmation, stale/map faults, cooldown.
- `tb_cue_scheduler.v` — pulse limit, cooldown, enable gating, reset.
- `tb_trace_player.v` — sample timing, wrap, pause.
- `tb_balat_basys3_top.v` — end-to-end integration and fail-safe checks.
- `road_geom_vectors.txt` — generated vector file used by `tb_road_geom.v`.
