# Scripts

Planned scripts:
- `extract_osm_roads.py`: fetch/extract road geometries for a defined bounding box.
- `prepare_road_map.py`: project, simplify, segment, quantize, and emit BRAM init files.
- `golden_geometry.py`: Python reference model for RTL comparison.
- `make_test_vectors.py`: generate deterministic simulation vectors.

Scripts must record source attribution, map timestamp, CRS, bounds, and conversion parameters.
Do not embed API keys or private credentials.
