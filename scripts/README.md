# Scripts

Current scripts:

- `golden_geometry.py` — integer geometry reference model and synthetic trace
  generator. Emits `data/demo_trace.csv`, `data/demo_trace_expected.csv`,
  `rtl/demo_trace_rom.v`, and `tb/road_geom_vectors.txt`.
- `build_basys3_demo.tcl` — Vivado non-project build for the Basys 3 demo.
- `run_demo_sims.sh` — Icarus Verilog simulation suite.
- `web_demo.py` — dashboard that decodes the Basys 3 USB-UART bridge with
  `--serial PORT`; `--esp32-serial PORT` reads ESP32 key/value logs and
  exposes dashboard-controlled mock GPS input using checksummed NMEA through
  the ESP32 parser; `--basys3-nmea-serial PORT` streams the same dashboard
  replay as raw NMEA into the dedicated FPGA image and reads its telemetry back.
  Both hardware modes expose the same start/pause/reset/rate controls. Without a
  serial argument, `--simulate` uses the local trace. See
  `docs/BASYS3_DASHBOARD_NMEA.md` for the FPGA build and wiring steps.
- `build_basys3_herdsync.tcl` — Vivado non-project build for the Basys 3 UART bridge.
- `build_basys3_dashboard.tcl` — Vivado build for the NMEA-input/dashboard FPGA image.
- `run_herdsync_sims.sh` — Icarus simulation suite for the UART bridge.

Planned scripts:

- `extract_osm_roads.py`: fetch/extract road geometries for a defined bounding box.
- `prepare_road_map.py`: project, simplify, segment, quantize, and emit BRAM init files.
- `make_test_vectors.py`: generate deterministic simulation vectors for the full pipeline.

Scripts must record source attribution, map timestamp, CRS, bounds, and conversion parameters.
Do not embed API keys or private credentials.
## Supabase telemetry storage

The optional Supabase schema is in
[`../supabase/migrations/20261102234000_create_telemetry_events.sql`](../supabase/migrations/20261102234000_create_telemetry_events.sql).
It stores validated bridge samples for 90 days and keeps row-level security
enabled without exposing telemetry to anonymous clients.

Apply the migration through the Supabase SQL editor or the Supabase CLI. The
bridge can optionally ingest samples with these environment variables:

```bash
export BALAT_SUPABASE_URL="https://YOUR_PROJECT.supabase.co"
export BALAT_SUPABASE_SERVICE_ROLE_KEY="your-service-role-key"
export BALAT_SUPABASE_SITE_ID="kupang-demo"
python3 scripts/web_demo.py --simulate
```

Ingestion is disabled when the variables are absent. The service-role key is
used only by the bridge process; never put it in `web/` or a `NEXT_PUBLIC_*`
variable.
