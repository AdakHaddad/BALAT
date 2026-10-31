#!/usr/bin/env bash
# Run all Basys 3 demo simulations with Icarus Verilog.
# Usage: bash scripts/run_demo_sims.sh
set -euo pipefail

cd "$(dirname "$0")/.."
mkdir -p build/sim

TOP_RTL="rtl/balat_basys3_top.v rtl/trace_player.v rtl/demo_trace_rom.v rtl/road_geom.v rtl/risk_fsm.v rtl/cue_scheduler.v"

iverilog -g2012 -o build/sim/tb_nmea_parser tb/tb_nmea_parser.v rtl/nmea_parser.v
vvp build/sim/tb_nmea_parser

iverilog -g2012 -o build/sim/tb_coord_convert tb/tb_coord_convert.v rtl/coord_convert.v
vvp build/sim/tb_coord_convert

iverilog -g2012 -o build/sim/tb_road_seg_rom tb/tb_road_seg_rom.v rtl/road_seg_rom.v
vvp build/sim/tb_road_seg_rom

iverilog -g2012 -o build/sim/tb_road_geom tb/tb_road_geom.v rtl/road_geom.v
vvp build/sim/tb_road_geom

iverilog -g2012 -o build/sim/tb_nearest_segment tb/tb_nearest_segment.v rtl/nearest_segment.v rtl/road_geom.v rtl/road_seg_rom.v
vvp build/sim/tb_nearest_segment

iverilog -g2012 -o build/sim/tb_velocity_estimator tb/tb_velocity_estimator.v rtl/velocity_estimator.v
vvp build/sim/tb_velocity_estimator

iverilog -g2012 -o build/sim/tb_risk_fsm tb/tb_risk_fsm.v rtl/risk_fsm.v
vvp build/sim/tb_risk_fsm

iverilog -g2012 -o build/sim/tb_cue_scheduler tb/tb_cue_scheduler.v rtl/cue_scheduler.v
vvp build/sim/tb_cue_scheduler

iverilog -g2012 -o build/sim/tb_cue_modules tb/tb_cue_modules.v
vvp build/sim/tb_cue_modules

iverilog -g2012 -o build/sim/tb_trace_player tb/tb_trace_player.v rtl/trace_player.v
vvp build/sim/tb_trace_player

iverilog -g2012 -o build/sim/tb_balat_basys3_top tb/tb_balat_basys3_top.v $TOP_RTL
vvp build/sim/tb_balat_basys3_top

iverilog -g2012 -o build/sim/tb_gnss_replay tb/tb_gnss_replay.v rtl/nmea_parser.v rtl/coord_convert.v rtl/road_geom.v rtl/velocity_estimator.v rtl/risk_fsm.v rtl/cue_scheduler.v
vvp build/sim/tb_gnss_replay

echo "All Basys 3 demo simulations passed."
