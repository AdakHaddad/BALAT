# Data

Store only small, permitted test fixtures and generated map memory images here.
Do not commit private farm coordinates or sensitive location data without explicit authorization.
Include a manifest for every map-derived dataset.

Current demo fixtures (synthetic, not map-derived):

- `demo_trace.csv` — 201-sample local-coordinate track.
- `demo_trace_expected.csv` — squared distance, inside-span flag, and zone per sample.

Regenerate both with `python3 scripts/golden_geometry.py`.
