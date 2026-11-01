# Scripts

Current scripts:

- `golden_geometry.py` — integer geometry reference model and synthetic trace
  generator. Emits `data/demo_trace.csv`, `data/demo_trace_expected.csv`,
  `rtl/demo_trace_rom.v`, and `tb/road_geom_vectors.txt`.
- `build_basys3_demo.tcl` — Vivado non-project build for the Basys 3 demo.
- `run_demo_sims.sh` — Icarus Verilog simulation suite.
- `web_demo.py` — dashboard that decodes the Basys 3 USB-UART bridge with
  `--serial PORT` and supports explicit start/stop CSV POC recording. Without
  `--serial`, it uses a local synthetic trace. It is display/recording only and
  has no cue-control path.
- `build_basys3_herdsync.tcl` — Vivado non-project build for the Basys 3 UART bridge.
- `run_herdsync_sims.sh` — Icarus simulation suite for the UART bridge.

Planned scripts:

- `extract_osm_roads.py`: fetch/extract road geometries for a defined bounding box.
- `prepare_road_map.py`: project, simplify, segment, quantize, and emit BRAM init files.
- `make_test_vectors.py`: generate deterministic simulation vectors for the full pipeline.

Scripts must record source attribution, map timestamp, CRS, bounds, and conversion parameters.
Do not embed API keys or private credentials.
