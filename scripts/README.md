# Scripts

Current scripts:

- `golden_geometry.py` — integer geometry reference model and synthetic trace
  generator. Emits `data/demo_trace.csv`, `data/demo_trace_expected.csv`,
  `rtl/demo_trace_rom.v`, and `tb/road_geom_vectors.txt`.
- `build_basys3_demo.tcl` — Vivado non-project build for the Basys 3 demo.
- `run_demo_sims.sh` — Icarus Verilog simulation suite.

Planned scripts:

- `extract_osm_roads.py`: fetch/extract road geometries for a defined bounding box.
- `prepare_road_map.py`: project, simplify, segment, quantize, and emit BRAM init files.
- `make_test_vectors.py`: generate deterministic simulation vectors for the full pipeline.

Scripts must record source attribution, map timestamp, CRS, bounds, and conversion parameters.
Do not embed API keys or private credentials.
