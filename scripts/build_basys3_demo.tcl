# Non-project Vivado build for the BALAT Basys 3 demo.
# Usage: vivado -mode batch -source scripts/build_basys3_demo.tcl
# Outputs: build/basys3_demo/balat_basys3_demo.bit plus utilization/timing reports.

set script_dir [file normalize [file dirname [info script]]]
set repo_dir   [file normalize [file join $script_dir ..]]
set build_dir  [file join $repo_dir build basys3_demo]

file mkdir $build_dir

set rtl_files [list \
    [file join $repo_dir rtl balat_basys3_top.v] \
    [file join $repo_dir rtl trace_player.v] \
    [file join $repo_dir rtl demo_trace_rom.v] \
    [file join $repo_dir rtl road_geom.v] \
    [file join $repo_dir rtl risk_fsm.v] \
    [file join $repo_dir rtl cue_scheduler.v] \
]

read_verilog $rtl_files
read_xdc [file join $repo_dir constraints basys3_demo.xdc]

synth_design -top balat_basys3_top -part xc7a35tcpg236-1
opt_design
place_design
route_design

write_checkpoint -force [file join $build_dir balat_basys3_demo_routed.dcp]
write_bitstream -force [file join $build_dir balat_basys3_demo.bit]
report_utilization -file [file join $build_dir utilization.rpt]
report_timing_summary -file [file join $build_dir timing_summary.rpt]

puts "BALAT Basys 3 demo build complete: $build_dir"
